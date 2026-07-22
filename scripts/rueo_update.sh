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

# Production rueo.ru now lives on the FirstVDS Stage host. The local SSH alias
# carries the required key/user configuration.
SERVER_SSH_DEFAULT="firstvds-stage"
SERVER_TEKSTOJ_DIR_DEFAULT="/var/www/slovari/data/www/rueo.ru/backend/data/tekstoj"

OLD_UPDATER_SSH_DEFAULT="$SERVER_SSH_DEFAULT"
OLD_UPDATER_DIR_DEFAULT="/var/www/slovari/data/www/updater.rueo.ru"
OLD_UPDATER_DB_DEFAULT="slovari_vortaro"
OLD_UPDATER_TEST_DB_DEFAULT="slovari_vortaro_test"
OLD_LOCAL_UPDATER_PHP_DEFAULT="/home/avo/updater.rueo.ru/updater_src/vortaro_updater_8.php"
OLD_LOCAL_SITE_DIR_DEFAULT="/home/avo/old.rueo.ru"
OLD_LOCAL_DB_HOST_DEFAULT="127.0.0.1"
OLD_LOCAL_DB_DEFAULT="slovari_vortaro"
OLD_LOCAL_DB_USER_DEFAULT="slovari_vuser"

LOCAL_PG_CONTAINER_DEFAULT="rueo_postgres"
SERVER_PG_CONTAINER_DEFAULT="rueo-db-1"
SERVER_BACKEND_CONTAINER_DEFAULT="rueo-backend-1"

log() { printf "%s\n" "$*"; }
die() { printf "ERROR: %s\n" "$*" >&2; exit 1; }

shell_quote() {
  printf '%q' "$1"
}

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

  printf '%s\n' "Dump local DB (${dbname}) using ${container} → ${out}" >&2
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

write_last_ru_letter_cp1251() {
  local value="$1"
  local out="$2"
  python3 - <<'PY' "$value" "$out"
import sys

value, out = sys.argv[1], sys.argv[2]
with open(out, "wb") as f:
    f.write(value.encode("cp1251"))
PY
}

sync_old_updater_src() {
  need_cmd rsync
  need_cmd ssh
  need_cmd python3

  local last_ru_letter="$1"
  [[ -n "$last_ru_letter" ]] || die "last_ru_letter is required"

  local ssh_target="${OLD_UPDATER_SSH:-$OLD_UPDATER_SSH_DEFAULT}"
  local old_dir="${OLD_UPDATER_DIR:-$OLD_UPDATER_DIR_DEFAULT}"
  local src_dir="${old_dir}/src"

  log "Prepare old.rueo.ru updater source dir → ${ssh_target}:${src_dir}"
  ssh -o BatchMode=yes "$ssh_target" \
    "mkdir -p $(shell_quote "${src_dir}/VortaroRE-daily") $(shell_quote "${src_dir}/VortaroER-daily")"

  log "Sync local dictionary sources → old.rueo.ru updater"
  rsync -a --delete --no-owner --no-group --chmod=D755,F644 \
    --exclude='*:com.dropbox.attrs' \
    --exclude='*.attrs' \
    "${DATA_SRC_DIR}/VortaroRE-daily/" "${ssh_target}:${src_dir}/VortaroRE-daily/"

  rsync -a --delete --no-owner --no-group --chmod=D755,F644 \
    --exclude='*:com.dropbox.attrs' \
    --exclude='*.attrs' \
    "${DATA_SRC_DIR}/VortaroER-daily/" "${ssh_target}:${src_dir}/VortaroER-daily/"

  local tmp_last
  tmp_last="$(mktemp)"
  write_last_ru_letter_cp1251 "$last_ru_letter" "$tmp_last"
  scp -q "$tmp_last" "${ssh_target}:${src_dir}/last-ru-letter.txt"
  rm -f "$tmp_last"

  ssh -o BatchMode=yes "$ssh_target" \
    "chown -R slovari:slovari $(shell_quote "$src_dir") 2>/dev/null || true"
}

update_old_server_db() {
  need_cmd ssh

  local last_ru_letter="$1"
  [[ -n "$last_ru_letter" ]] || die "last_ru_letter is required"

  local ssh_target="${OLD_UPDATER_SSH:-$OLD_UPDATER_SSH_DEFAULT}"
  local old_dir="${OLD_UPDATER_DIR:-$OLD_UPDATER_DIR_DEFAULT}"
  local old_db="${OLD_UPDATER_DB:-$OLD_UPDATER_DB_DEFAULT}"
  local old_test_db="${OLD_UPDATER_TEST_DB:-$OLD_UPDATER_TEST_DB_DEFAULT}"
  local backup_path="${OLD_UPDATER_BACKUP_PATH:-}"

  log "Run old.rueo.ru legacy MySQL updater on ${ssh_target}"
  ssh -o BatchMode=yes "$ssh_target" \
    "OLD_DIR=$(shell_quote "$old_dir") LAST_RU_LETTER=$(shell_quote "$last_ru_letter") OLD_DB=$(shell_quote "$old_db") OLD_TEST_DB=$(shell_quote "$old_test_db") OLD_BACKUP_PATH=$(shell_quote "$backup_path") bash -s" <<'EOS'
set -euo pipefail

cd "$OLD_DIR"

php_bin="${OLD_PHP_BIN:-/usr/bin/php}"
php_script="${OLD_PHP_SCRIPT:-updater_src/vortaro_updater_8.php}"
data_dir="${OLD_DATA_DIR:-src}"
log_dir="${OLD_LOG_DIR:-$OLD_DIR/logs}"
mkdir -p "$log_dir"

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
test_log="$log_dir/old-rueo-test-$stamp.log"
prod_log="$log_dir/old-rueo-prod-$stamp.log"
backup_path="${OLD_BACKUP_PATH:-/root/old_rueo_vortaro_$stamp.sql}"

db_password="$(./env311/bin/python - <<'PY'
import yaml
with open("vu.yml", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)
print(cfg.get("db-password", ""))
PY
)"

echo "Test import → $OLD_TEST_DB"
OLD_RUEO_MYSQL_USER=slovari_vuser OLD_RUEO_MYSQL_PASSWORD="$db_password" \
  "$php_bin" "$php_script" --daily --dbname "$OLD_TEST_DB" --last-ru-letter "$LAST_RU_LETTER" "$data_dir" 2>&1 | tee "$test_log"

echo "Backup production MySQL DB → $backup_path"
mysqldump -u slovari_vuser -p"$db_password" "$OLD_DB" > "$backup_path"
chmod 600 "$backup_path"

echo "Production import → $OLD_DB"
"$php_bin" "$php_script" --daily --dbname "$OLD_DB" --last-ru-letter "$LAST_RU_LETTER" --production "$data_dir" 2>&1 | tee "$prod_log"

./env311/bin/python - "$prod_log" "$LAST_RU_LETTER" <<'PY'
import datetime as _dt
import re
import sys
import yaml
from pathlib import Path

log_path = Path(sys.argv[1])
last_word = sys.argv[2]

with open("vu.yml", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

klarigo = Path(cfg["klarigo.textile"])
renovigxo = klarigo.with_name("renovigxo.textile")

raw = log_path.read_bytes()
pattern = re.compile(rb"\[(eo|ru|farito ru)\] \xd0\x9a\xd0\xbe\xd0\xbb\xd0\xb8\xd1\x87\xd0\xb5\xd1\x81\xd1\x82\xd0\xb2\xd0\xbe (\xd1\x81\xd0\xbb\xd0\xbe\xd0\xb2\xd0\xb0\xd1\x80\xd0\xbd\xd1\x8b\xd1\x85 \xd1\x81\xd1\x82\xd0\xb0\xd1\x82\xd0\xb5\xd0\xb9|\xd1\x81\xd0\xbb\xd0\xbe\xd0\xb2): (\d+)")
stats = {(lang.decode(), kind.decode()): int(value) for lang, kind, value in pattern.findall(raw)}

if not stats:
    current_lang = None
    for line in raw.decode("utf-8", errors="replace").splitlines():
        match = re.match(r"Processing language: (eo|ru)$", line)
        if match:
            current_lang = match.group(1)
            continue
        if current_lang is None:
            continue
        match = re.search(r"Dictionary entries processed: (\d+)", line)
        if match:
            stats[(current_lang, "словарных статей")] = int(match.group(1))
            if current_lang == "ru":
                stats[("farito ru", "словарных статей")] = int(match.group(1))
            continue
        match = re.search(r"Words processed: (\d+)", line)
        if match:
            stats[(current_lang, "слов")] = int(match.group(1))
            if current_lang == "ru":
                stats[("farito ru", "слов")] = int(match.group(1))

def rus_num_ending(number, end1, end4, end5):
    number = number % 100
    if 11 <= number <= 19:
        return end5
    last = number % 10
    if last == 1:
        return end1
    if last in (2, 3, 4):
        return end4
    return end5

def rus_in_ending(number, end1, end2, end1000=None):
    if number % 1000 == 0 and end1000:
        return end1000
    if number % 10 == 1 and number % 100 // 10 != 1:
        return end1
    return end2

def format_stat(lang):
    words = stats[(lang, "слов")]
    articles = stats[(lang, "словарных статей")]
    return (
        f"{words} {rus_num_ending(words, 'слово', 'слова', 'слов')} "
        f"в {articles} {rus_in_ending(articles, 'словарной статье', 'словарных статьях', 'словарных статей')}"
    )

re_text = (
    f"рабочие материалы большого русско-эсперантского словаря "
    f"(диапазон А -- {last_word}), {format_stat('farito ru')}"
)

text = (
    "h3. Открыты для поиска:\n\n"
    f"* большой эсперанто-русский словарь в актуальной редакции, {format_stat('eo')};\n"
    f"* {re_text}.\n"
)
klarigo.write_text(text, encoding="utf-8")

months = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]
today = _dt.date.today()
date_line = f"{today.day} {months[today.month - 1]} {today.year} года"
old = renovigxo.read_text(encoding="utf-8")
if not old.startswith(date_line + "\n"):
    renovigxo.write_text(date_line + "\n" + old, encoding="utf-8")
PY

echo "OLD_RUEO_BACKUP=$backup_path"
echo "OLD_RUEO_TEST_LOG=$test_log"
echo "OLD_RUEO_PROD_LOG=$prod_log"
EOS
}

update_old_local_texts_from_log() {
  local log_path="$1"
  local last_ru_letter="$2"
  local site_dir="${OLD_LOCAL_SITE_DIR:-$OLD_LOCAL_SITE_DIR_DEFAULT}"

  python3 - <<'PY' "$log_path" "$last_ru_letter" "$site_dir"
import datetime as _dt
import re
import sys
from pathlib import Path

log_path = Path(sys.argv[1])
last_word = sys.argv[2]
site_dir = Path(sys.argv[3])
tekstoj_dir = site_dir / "tekstoj"
klarigo = tekstoj_dir / "klarigo.textile"
renovigxo = tekstoj_dir / "renovigxo.textile"

raw = log_path.read_bytes()
pattern = re.compile(rb"\[(eo|ru|farito ru)\] \xd0\x9a\xd0\xbe\xd0\xbb\xd0\xb8\xd1\x87\xd0\xb5\xd1\x81\xd1\x82\xd0\xb2\xd0\xbe (\xd1\x81\xd0\xbb\xd0\xbe\xd0\xb2\xd0\xb0\xd1\x80\xd0\xbd\xd1\x8b\xd1\x85 \xd1\x81\xd1\x82\xd0\xb0\xd1\x82\xd0\xb5\xd0\xb9|\xd1\x81\xd0\xbb\xd0\xbe\xd0\xb2): (\d+)")
stats = {(lang.decode(), kind.decode()): int(value) for lang, kind, value in pattern.findall(raw)}

if not stats:
    current_lang = None
    for line in raw.decode("utf-8", errors="replace").splitlines():
        match = re.match(r"Processing language: (eo|ru)$", line)
        if match:
            current_lang = match.group(1)
            continue
        if current_lang is None:
            continue
        match = re.search(r"Dictionary entries processed: (\d+)", line)
        if match:
            stats[(current_lang, "словарных статей")] = int(match.group(1))
            if current_lang == "ru":
                stats[("farito ru", "словарных статей")] = int(match.group(1))
            continue
        match = re.search(r"Words processed: (\d+)", line)
        if match:
            stats[(current_lang, "слов")] = int(match.group(1))
            if current_lang == "ru":
                stats[("farito ru", "слов")] = int(match.group(1))

required = [
    ("eo", "слов"),
    ("eo", "словарных статей"),
    ("farito ru", "слов"),
    ("farito ru", "словарных статей"),
]
missing = [key for key in required if key not in stats]
if missing:
    raise SystemExit(f"Missing old.rueo.ru stats in import log: {missing}")

def rus_num_ending(number, end1, end4, end5):
    number = number % 100
    if 11 <= number <= 19:
        return end5
    last = number % 10
    if last == 1:
        return end1
    if last in (2, 3, 4):
        return end4
    return end5

def rus_in_ending(number, end1, end2, end1000=None):
    if number % 1000 == 0 and end1000:
        return end1000
    if number % 10 == 1 and number % 100 // 10 != 1:
        return end1
    return end2

def format_stat(lang):
    words = stats[(lang, "слов")]
    articles = stats[(lang, "словарных статей")]
    return (
        f"{words} {rus_num_ending(words, 'слово', 'слова', 'слов')} "
        f"в {articles} {rus_in_ending(articles, 'словарной статье', 'словарных статьях', 'словарных статей')}"
    )

re_text = (
    f"рабочие материалы большого русско-эсперантского словаря "
    f"(диапазон А -- {last_word}), {format_stat('farito ru')}"
)

text = (
    "h3. Открыты для поиска:\n\n"
    f"* большой эсперанто-русский словарь в актуальной редакции, {format_stat('eo')};\n"
    f"* {re_text}.\n"
)
klarigo.write_text(text, encoding="utf-8")

months = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]
today = _dt.date.today()
date_line = f"{today.day} {months[today.month - 1]} {today.year} года"
old = renovigxo.read_text(encoding="utf-8") if renovigxo.exists() else ""
if not old.startswith(date_line + "\n"):
    renovigxo.write_text(date_line + "\n" + old, encoding="utf-8")
PY
}

update_old_local_db() {
  need_cmd php
  need_cmd python3

  local last_ru_letter="$1"
  [[ -n "$last_ru_letter" ]] || die "last_ru_letter is required"

  local php_script="${OLD_LOCAL_UPDATER_PHP:-$OLD_LOCAL_UPDATER_PHP_DEFAULT}"
  local db_host="${OLD_LOCAL_DB_HOST:-$OLD_LOCAL_DB_HOST_DEFAULT}"
  local db_name="${OLD_LOCAL_DB:-$OLD_LOCAL_DB_DEFAULT}"
  local db_user="${OLD_LOCAL_DB_USER:-$OLD_LOCAL_DB_USER_DEFAULT}"
  local db_password="${OLD_LOCAL_DB_PASSWORD:-}"

  [[ -f "$php_script" ]] || die "Old local updater PHP not found: $php_script"
  [[ -d "${DATA_SRC_DIR}/VortaroRE-daily" ]] || die "Dictionary source dir not found: ${DATA_SRC_DIR}/VortaroRE-daily"
  [[ -d "${DATA_SRC_DIR}/VortaroER-daily" ]] || die "Dictionary source dir not found: ${DATA_SRC_DIR}/VortaroER-daily"

  mkdir -p "${REPO_DIR}/tmp"
  local stamp log_path
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  log_path="${REPO_DIR}/tmp/old_rueo_local_import_${stamp}.log"

  log "Run old.rueo.ru local MySQL import (${db_name}) → ${log_path}"
  OLD_RUEO_MYSQL_HOST="$db_host" \
  OLD_RUEO_MYSQL_USER="$db_user" \
  OLD_RUEO_MYSQL_PASSWORD="$db_password" \
    php "$php_script" \
      --daily \
      --dbname "$db_name" \
      --last-ru-letter "$last_ru_letter" \
      "${DATA_SRC_DIR}" 2>&1 | tee "$log_path"

  update_old_local_texts_from_log "$log_path" "$last_ru_letter"
  log "Done. Local old.rueo.ru import log: $log_path"
}

cmd_run_old() {
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

  sync_old_updater_src "$last_ru_letter"
  update_old_server_db "$last_ru_letter"
}

cmd_run_all() {
  cmd_run "$@"
  cmd_run_old "$@"
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
  run-all --last-ru-letter <word>
                               Full current pipeline, then old.rueo.ru legacy MySQL update
  sync-in                      Copy Dropbox sources into backend/data/src
  sync-back                    Copy processed sources back into Dropbox
  import-local --last-ru-letter <word>
  dump-local-db                Create DB dump file and print its path
  restore-server-db <dumpfile> Upload and restore a dump on the server
  deploy-tekstoj               Copy backend/data/tekstoj/{klarigo,renovigxo}.md to the server
  deploy-klarigo               Alias for deploy-tekstoj
  sync-old-src --last-ru-letter <word>
                               Copy current sources to the old.rueo.ru updater src dir
  update-old-db --last-ru-letter <word>
                               Run legacy old.rueo.ru MySQL updater on the server
  update-old-local-db --last-ru-letter <word>
                               Run legacy old.rueo.ru importer against local MySQL
  run-old --last-ru-letter <word>
                               sync-old-src + update-old-db
  reset-tracking               Truncate tracking tables (local DB)

Environment variables:
  DROPBOX_VORTARO_RE, DROPBOX_VORTARO_ER  Override Dropbox source dirs
  NORMALIZE_PERMS=0                      Disable chmod normalization
  IMPORT_CMD                             Override importer command (default: python3 -m app.importer)
  DATABASE_URL                           Local DB URL for dumping
  LOCAL_PG_CONTAINER                     Local postgres container name (default: rueo_postgres)
  LOCAL_BACKEND_CONTAINER                Local backend container to read DATABASE_URL from (default: rueo_backend)
  SERVER_SSH                             SSH target (default: $SERVER_SSH_DEFAULT)
  SERVER_TEKSTOJ_DIR                     Server tekstoj dir (default: $SERVER_TEKSTOJ_DIR_DEFAULT)
  SERVER_PG_CONTAINER                    Server postgres container (default: rueo-db-1)
  SERVER_BACKEND_CONTAINER               Server backend container (default: rueo-backend-1)
  OLD_UPDATER_SSH                        SSH target for old.rueo.ru updater (default: $OLD_UPDATER_SSH_DEFAULT)
  OLD_UPDATER_DIR                        Server updater dir (default: $OLD_UPDATER_DIR_DEFAULT)
  OLD_UPDATER_DB                         Legacy production MySQL DB (default: $OLD_UPDATER_DB_DEFAULT)
  OLD_UPDATER_TEST_DB                    Legacy test MySQL DB (default: $OLD_UPDATER_TEST_DB_DEFAULT)
  OLD_UPDATER_BACKUP_PATH                Optional remote backup path for update-old-db
  OLD_LOCAL_UPDATER_PHP                  Local legacy PHP importer (default: $OLD_LOCAL_UPDATER_PHP_DEFAULT)
  OLD_LOCAL_SITE_DIR                     Local old.rueo.ru dir for tekstoj (default: $OLD_LOCAL_SITE_DIR_DEFAULT)
  OLD_LOCAL_DB_HOST                      Local MySQL host (default: $OLD_LOCAL_DB_HOST_DEFAULT)
  OLD_LOCAL_DB                           Local MySQL DB (default: $OLD_LOCAL_DB_DEFAULT)
  OLD_LOCAL_DB_USER                      Local MySQL user (default: $OLD_LOCAL_DB_USER_DEFAULT)
  OLD_LOCAL_DB_PASSWORD                  Local MySQL password (no default)
EOF
}

main() {
  local cmd="${1:-}"
  shift || true

  case "$cmd" in
    run) cmd_run "$@";;
    run-all) cmd_run_all "$@";;
    sync-in) rsync_two_dirs_into_src;;
    sync-back) sync_back_to_dropbox;;
    import-local)
      [[ "${1:-}" == "--last-ru-letter" ]] || die "import-local requires --last-ru-letter <word>"
      run_local_import "${2:-}";;
    dump-local-db) dump_local_db;;
    restore-server-db) restore_server_db "${1:-}";;
    deploy-tekstoj) deploy_tekstoj;;
    deploy-klarigo) deploy_tekstoj;;
    sync-old-src)
      [[ "${1:-}" == "--last-ru-letter" ]] || die "sync-old-src requires --last-ru-letter <word>"
      sync_old_updater_src "${2:-}";;
    update-old-db)
      [[ "${1:-}" == "--last-ru-letter" ]] || die "update-old-db requires --last-ru-letter <word>"
      update_old_server_db "${2:-}";;
    update-old-local-db)
      [[ "${1:-}" == "--last-ru-letter" ]] || die "update-old-local-db requires --last-ru-letter <word>"
      update_old_local_db "${2:-}";;
    run-old) cmd_run_old "$@";;
    reset-tracking) reset_tracking;;
    -h|--help|help|"") usage;;
    *) die "Unknown command: $cmd";;
  esac
}

main "$@"
