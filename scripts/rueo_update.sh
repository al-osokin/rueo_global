#!/usr/bin/env bash
set -euo pipefail

# Rueo dictionary update helper.
# Usage examples:
#   ./scripts/rueo_update.sh run --last-ru-letter "прегрешить"
#   ./scripts/rueo_update.sh sync-in
#   ./scripts/rueo_update.sh dump-local-db
#   ./scripts/rueo_update.sh restore-server-db ./tmp/rueo_db.dump

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
BACKEND_DIR="${REPO_DIR}/backend"
DATA_SRC_DIR="${BACKEND_DIR}/data/src"
TEKSTOJ_DIR="${BACKEND_DIR}/data/tekstoj"

DROPBOX_ROOT_DEFAULT="/mnt/f/Backup/Dropbox"
DROPBOX_VORTARO_RE_DEFAULT="${DROPBOX_ROOT_DEFAULT}/VortaroRE-daily"
DROPBOX_VORTARO_ER_DEFAULT="${DROPBOX_ROOT_DEFAULT}/VortaroER-daily"

SERVER_SSH_DEFAULT="root@rueo.ru"
SERVER_TEKSTOJ_DIR_DEFAULT="/var/www/slovari/data/www/rueo.ru/backend/data/tekstoj"

LOCAL_PG_CONTAINER_DEFAULT="rueo_postgres"
SERVER_PG_CONTAINER_DEFAULT="rueo-db-1"
SERVER_BACKEND_CONTAINER_DEFAULT="rueo-backend-1"

log() { printf "%s\n" "$*"; }
die() { printf "ERROR: %s\n" "$*" >&2; exit 1; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"
}

parse_pg_url_json() {
  # Prints JSON: {"user":...,"password":...,"dbname":...}
  # Tolerates unescaped characters like '?' in passwords (some envs set DATABASE_URL like that).
  # Supports postgresql:// and postgres://
  local url="$1"
  python3 - <<'PY' "$url"
import json
import sys
from urllib.parse import unquote

url = sys.argv[1].strip()
if not (url.startswith("postgresql://") or url.startswith("postgres://")):
    scheme = url.split("://", 1)[0] if "://" in url else ""
    raise SystemExit(f"Unsupported DATABASE_URL scheme: {scheme}")

rest = url.split("://", 1)[1]
# netloc is up to first '/'
if "/" not in rest:
    raise SystemExit("DATABASE_URL must include database name")
netloc, path_and_more = rest.split("/", 1)
# dbname ends before '?' or '#'
dbname = path_and_more.split("?", 1)[0].split("#", 1)[0].strip()

# userinfo is before last '@'
if "@" not in netloc:
    raise SystemExit("DATABASE_URL must include userinfo")
userinfo, _hostport = netloc.rsplit("@", 1)
if ":" in userinfo:
    user, password = userinfo.split(":", 1)
else:
    user, password = userinfo, ""

user = unquote(user)
password = unquote(password)

if not user or not dbname:
    raise SystemExit("DATABASE_URL must include username and database name")

print(json.dumps({"user": user, "password": password, "dbname": dbname}))
PY
}

json_get() {
  local key="$1"
  python3 -c 'import json,sys
key=sys.argv[1]
raw=sys.stdin.read().strip()
if not raw:
  print("")
  raise SystemExit(0)
data=json.loads(raw)
print(data.get(key,""))' "$key"
}

rsync_two_dirs_into_src() {
  need_cmd rsync
  local dropbox_re="${DROPBOX_VORTARO_RE:-$DROPBOX_VORTARO_RE_DEFAULT}"
  local dropbox_er="${DROPBOX_VORTARO_ER:-$DROPBOX_VORTARO_ER_DEFAULT}"

  [[ -d "$dropbox_re" ]] || die "Dropbox folder not found: $dropbox_re"
  [[ -d "$dropbox_er" ]] || die "Dropbox folder not found: $dropbox_er"

  mkdir -p "${DATA_SRC_DIR}/VortaroRE-daily" "${DATA_SRC_DIR}/VortaroER-daily"

  log "Sync Dropbox → ${DATA_SRC_DIR}"
  rsync -a --delete \
    --exclude='*:com.dropbox.attrs' \
    --exclude='*.attrs' \
    "$dropbox_re/" "${DATA_SRC_DIR}/VortaroRE-daily/"

  rsync -a --delete \
    --exclude='*:com.dropbox.attrs' \
    --exclude='*.attrs' \
    "$dropbox_er/" "${DATA_SRC_DIR}/VortaroER-daily/"

  # Extra cleanup: Windows/Dropbox artifact filenames with colon suffix.
  find "${DATA_SRC_DIR}" -type f -name '*:com.dropbox.attrs' -delete || true

  normalize_src_perms
}

normalize_src_perms() {
  # Optional permission normalization.
  if [[ "${NORMALIZE_PERMS:-1}" != "1" ]]; then
    return 0
  fi

  # Directories: 755; files: 644.
  find "${DATA_SRC_DIR}/VortaroRE-daily" "${DATA_SRC_DIR}/VortaroER-daily" -type d -exec chmod 755 {} + || true
  find "${DATA_SRC_DIR}/VortaroRE-daily" "${DATA_SRC_DIR}/VortaroER-daily" -type f -exec chmod 644 {} + || true
}

sync_back_to_dropbox() {
  need_cmd rsync
  local dropbox_re="${DROPBOX_VORTARO_RE:-$DROPBOX_VORTARO_RE_DEFAULT}"
  local dropbox_er="${DROPBOX_VORTARO_ER:-$DROPBOX_VORTARO_ER_DEFAULT}"

  [[ -d "$dropbox_re" ]] || die "Dropbox folder not found: $dropbox_re"
  [[ -d "$dropbox_er" ]] || die "Dropbox folder not found: $dropbox_er"

  log "Sync processed files → Dropbox"
  rsync -a --delete \
    --exclude='*:com.dropbox.attrs' \
    --exclude='*.attrs' \
    "${DATA_SRC_DIR}/VortaroRE-daily/" "$dropbox_re/"

  rsync -a --delete \
    --exclude='*:com.dropbox.attrs' \
    --exclude='*.attrs' \
    "${DATA_SRC_DIR}/VortaroER-daily/" "$dropbox_er/"
}

run_local_import() {
  local last_ru_letter="$1"
  [[ -n "$last_ru_letter" ]] || die "last_ru_letter is required"

  local import_cmd="${IMPORT_CMD:-python3 -m app.importer}"
  log "Run local import (data-dir=${DATA_SRC_DIR})"

  (cd "${BACKEND_DIR}" && \
    ${import_cmd} --data-dir "${DATA_SRC_DIR}" --last-ru-letter "$last_ru_letter")
}

is_container_running() {
  local container="$1"
  docker inspect "$container" >/dev/null 2>&1 && \
    docker inspect --format='{{.State.Running}}' "$container" 2>/dev/null | grep -q 'true'
}

get_local_database_url() {
  local database_url="${DATABASE_URL:-}"
  if [[ -n "$database_url" ]]; then
    printf '%s' "$database_url"
    return 0
  fi

  local backend_container="${LOCAL_BACKEND_CONTAINER:-rueo_backend}"
  if is_container_running "$backend_container"; then
    database_url="$(docker exec "$backend_container" printenv DATABASE_URL 2>/dev/null || true)"
    if [[ -n "$database_url" ]]; then
      printf '%s' "$database_url"
      return 0
    fi
  fi

  # Fallback to docker-compose defaults.
  printf '%s' "postgresql://rueo_user:rueo_password@localhost:5432/rueo_db"
}

dump_local_db() {
  need_cmd docker
  need_cmd python3

  local database_url
  database_url="$(get_local_database_url)"

  local meta
  meta="$(parse_pg_url_json "$database_url")"
  local user password dbname
  user="$(printf '%s' "$meta" | json_get user)"
  password="$(printf '%s' "$meta" | json_get password)"
  dbname="$(printf '%s' "$meta" | json_get dbname)"

  [[ -n "$user" ]] || die "Failed to extract database user from DATABASE_URL: $database_url"
  [[ -n "$dbname" ]] || die "Failed to extract database name from DATABASE_URL: $database_url"

  local container="${LOCAL_PG_CONTAINER:-$LOCAL_PG_CONTAINER_DEFAULT}"
  docker inspect "$container" >/dev/null 2>&1 || die "Local Postgres container not found: $container"
  is_container_running "$container" || die "Local Postgres container not running: $container"

  mkdir -p "${REPO_DIR}/tmp"
  local out="${REPO_DIR}/tmp/rueo_db_$(date -u +%Y%m%dT%H%M%SZ).dump"

  log "Dump local DB (${dbname}) using ${container} → ${out}"
  if ! docker exec -e PGPASSWORD="$password" "$container" \
    pg_dump -U "$user" -d "$dbname" -F c -f "/tmp/rueo_db.dump" 2>&1; then
    die "pg_dump failed in container $container"
  fi

  if ! docker cp "$container:/tmp/rueo_db.dump" "$out" 2>&1; then
    die "docker cp failed to copy dump from container"
  fi

  docker exec "$container" rm -f "/tmp/rueo_db.dump" >/dev/null 2>&1 || true

  [[ -f "$out" ]] || die "Dump file not created: $out"

  printf '%s\n' "$out"
}

server_get_database_url() {
  local ssh_target="${SERVER_SSH:-$SERVER_SSH_DEFAULT}"
  local backend_container="${SERVER_BACKEND_CONTAINER:-$SERVER_BACKEND_CONTAINER_DEFAULT}"

  local database_url
  database_url="$(ssh -o BatchMode=yes "$ssh_target" "docker exec $backend_container printenv DATABASE_URL 2>/dev/null" || true)"

  [[ -n "$database_url" ]] || die "Failed to get DATABASE_URL from server container $backend_container"

  printf '%s' "$database_url"
}

restore_server_db() {
  need_cmd ssh
  need_cmd scp

  local dump_path="$1"
  [[ -f "$dump_path" ]] || die "Dump file not found: $dump_path"

  local ssh_target="${SERVER_SSH:-$SERVER_SSH_DEFAULT}"
  local server_tmp="/root/rueo_db.dump"

  log "Upload DB dump → ${ssh_target}:${server_tmp}"
  scp -q "$dump_path" "${ssh_target}:${server_tmp}"

  local database_url
  database_url="$(server_get_database_url)"
  local meta user password dbname
  meta="$(parse_pg_url_json "$database_url")"
  user="$(printf '%s' "$meta" | json_get user)"
  password="$(printf '%s' "$meta" | json_get password)"
  dbname="$(printf '%s' "$meta" | json_get dbname)"

  local db_container="${SERVER_PG_CONTAINER:-$SERVER_PG_CONTAINER_DEFAULT}"

  log "Restore server DB (${dbname}) in container ${db_container}"

  local remote_script
  remote_script="$(cat <<'EOS'
set -euo pipefail

docker inspect "$DB_CONTAINER" >/dev/null
docker inspect --format='{{.State.Running}}' "$DB_CONTAINER" | grep -q 'true' || \
  { echo "ERROR: Container $DB_CONTAINER is not running" >&2; exit 1; }

# Stop active sessions so pg_restore can cleanly drop objects.
docker exec -e PGPASSWORD="$PGPASSWORD" "$DB_CONTAINER" \
  psql -U "$PGUSER" -d postgres -v ON_ERROR_STOP=1 -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$DBNAME' AND pid <> pg_backend_pid();"

# Restore (custom format) with cleanup.
docker exec -e PGPASSWORD="$PGPASSWORD" -i "$DB_CONTAINER" \
  pg_restore -U "$PGUSER" -d "$DBNAME" --clean --if-exists --no-owner --no-privileges < "$SERVER_TMP"

rm -f "$SERVER_TMP"
EOS
)"

  ssh -o BatchMode=yes "$ssh_target" \
    "DB_CONTAINER='$db_container' PGUSER='$user' PGPASSWORD='$password' DBNAME='$dbname' SERVER_TMP='$server_tmp' bash -s" \
    <<<"$remote_script"
}

reset_tracking() {
  need_cmd docker
  need_cmd python3

  local database_url meta user password dbname
  database_url="$(get_local_database_url)"
  meta="$(parse_pg_url_json "$database_url")"
  user="$(printf '%s' "$meta" | json_get user)"
  password="$(printf '%s' "$meta" | json_get password)"
  dbname="$(printf '%s' "$meta" | json_get dbname)"

  local container="${LOCAL_PG_CONTAINER:-$LOCAL_PG_CONTAINER_DEFAULT}"
  docker inspect "$container" >/dev/null 2>&1 || die "Local Postgres container not found: $container"

  log "Reset tracking tables in ${dbname} (container ${container})"
  docker exec -e PGPASSWORD="$password" "$container" \
    psql -U "$user" -d "$dbname" -v ON_ERROR_STOP=1 -c \
    "TRUNCATE article_change_log, article_states, article_file_states RESTART IDENTITY CASCADE;"
}

deploy_tekstoj() {
  need_cmd scp
  local ssh_target="${SERVER_SSH:-$SERVER_SSH_DEFAULT}"
  local server_dir="${SERVER_TEKSTOJ_DIR:-$SERVER_TEKSTOJ_DIR_DEFAULT}"

  local klarigo="${TEKSTOJ_DIR}/klarigo.md"
  local renovigxo="${TEKSTOJ_DIR}/renovigxo.md"

  [[ -f "$klarigo" ]] || die "klarigo.md not found (run import first?): $klarigo"
  [[ -f "$renovigxo" ]] || die "renovigxo.md not found (run import first?): $renovigxo"

  log "Deploy klarigo.md → ${ssh_target}:${server_dir}/klarigo.md"
  scp -q "$klarigo" "${ssh_target}:${server_dir}/klarigo.md"

  log "Deploy renovigxo.md → ${ssh_target}:${server_dir}/renovigxo.md"
  scp -q "$renovigxo" "${ssh_target}:${server_dir}/renovigxo.md"
}

prompt_last_ru_letter() {
  local default_file="${DATA_SRC_DIR}/last-ru-letter.txt"
  local current=""
  if [[ -f "$default_file" ]]; then
    current="$(cat "$default_file" 2>/dev/null || true)"
  fi

  if [[ -n "$current" ]]; then
    printf "Enter last ready RU word (default: %s): " "$current" >&2
  else
    printf "Enter last ready RU word: " >&2
  fi

  local value=""
  read -r value
  if [[ -z "$value" && -n "$current" ]]; then
    value="$current"
  fi
  printf '%s' "$value"
}

cmd_run() {
  local last_ru_letter=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --last-ru-letter)
        last_ru_letter="${2:-}"; shift 2;;
      *)
        die "Unknown arg: $1";;
    esac
  done
  if [[ -z "$last_ru_letter" ]]; then
    last_ru_letter="$(prompt_last_ru_letter)"
  fi

  rsync_two_dirs_into_src
  run_local_import "$last_ru_letter"
  sync_back_to_dropbox
  local dump
  dump="$(dump_local_db)"
  restore_server_db "$dump"
  deploy_tekstoj

  log "Done. Dump kept at: $dump"
}

usage() {
  cat <<EOF
Usage: $0 <command> [options]

Commands:
  run --last-ru-letter <word>   Full pipeline: sync-in, import, sync-back, dump, restore, deploy tekstoj
  sync-in                      Copy Dropbox sources into backend/data/src
  sync-back                    Copy processed sources back into Dropbox
  import-local --last-ru-letter <word>
  dump-local-db                Create DB dump file and print its path
  restore-server-db <dumpfile> Upload and restore a dump on the server
  deploy-tekstoj               Copy backend/data/tekstoj/{klarigo,renovigxo}.md to the server
  deploy-klarigo               Alias for deploy-tekstoj
  reset-tracking               Truncate tracking tables (local DB)

Environment variables:
  DROPBOX_VORTARO_RE, DROPBOX_VORTARO_ER  Override Dropbox source dirs
  NORMALIZE_PERMS=0                      Disable chmod normalization
  IMPORT_CMD                             Override importer command (default: python3 -m app.importer)
  DATABASE_URL                           Local DB URL for dumping
  LOCAL_PG_CONTAINER                     Local postgres container name (default: rueo_postgres)
  LOCAL_BACKEND_CONTAINER                Local backend container to read DATABASE_URL from (default: rueo_backend)
  SERVER_SSH                             SSH target (default: root@rueo.ru)
  SERVER_TEKSTOJ_DIR                     Server tekstoj dir (default: $SERVER_TEKSTOJ_DIR_DEFAULT)
  SERVER_PG_CONTAINER                    Server postgres container (default: rueo-db-1)
  SERVER_BACKEND_CONTAINER               Server backend container (default: rueo-backend-1)
EOF
}

main() {
  local cmd="${1:-}"
  shift || true

  case "$cmd" in
    run) cmd_run "$@";;
    sync-in) rsync_two_dirs_into_src;;
    sync-back) sync_back_to_dropbox;;
    import-local)
      [[ "${1:-}" == "--last-ru-letter" ]] || die "import-local requires --last-ru-letter <word>"
      run_local_import "${2:-}";;
    dump-local-db) dump_local_db;;
    restore-server-db) restore_server_db "${1:-}";;
    deploy-tekstoj) deploy_tekstoj;;
    deploy-klarigo) deploy_tekstoj;;
    reset-tracking) reset_tracking;;
    -h|--help|help|"") usage;;
    *) die "Unknown command: $cmd";;
  esac
}

main "$@"
