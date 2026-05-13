#!/usr/bin/env bash
set -euo pipefail

# Build and deploy the Quasar PWA frontend to rueo.ru.
# Default mode is dry-run. Pass --apply to actually change files on the server.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
FRONTEND_DIR="${REPO_DIR}/frontend-app"
DIST_DIR="${FRONTEND_DIR}/dist/pwa"

SERVER_SSH_DEFAULT="root@rueo.ru"
SERVER_WEB_ROOT_DEFAULT="/var/www/slovari/data/www/rueo.ru"
SERVER_OWNER_DEFAULT="slovari:slovari"

SERVER_SSH="${SERVER_SSH:-$SERVER_SSH_DEFAULT}"
SERVER_WEB_ROOT="${SERVER_WEB_ROOT:-$SERVER_WEB_ROOT_DEFAULT}"
SERVER_OWNER="${SERVER_OWNER:-$SERVER_OWNER_DEFAULT}"
APPLY=0
SKIP_BUILD=0

log() { printf "%s\n" "$*"; }
die() { printf "ERROR: %s\n" "$*" >&2; exit 1; }
need_cmd() { command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"; }

usage() {
  cat <<EOF
Usage: $0 [--apply] [--dry-run] [--skip-build]

Builds frontend-app as Quasar PWA and syncs dist/pwa/ to the production web root.
Default is --dry-run. Use --apply for real deployment.

Environment overrides:
  SERVER_SSH       SSH target (default: $SERVER_SSH_DEFAULT)
  SERVER_WEB_ROOT  Remote web root (default: $SERVER_WEB_ROOT_DEFAULT)
  SERVER_OWNER     Remote owner:group for copied files (default: $SERVER_OWNER_DEFAULT)

Protected server-only paths excluded from rsync delete:
  /backend/
  /webstat/
  /cgi-bin/
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply) APPLY=1; shift ;;
    --dry-run) APPLY=0; shift ;;
    --skip-build) SKIP_BUILD=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown argument: $1" ;;
  esac
done

need_cmd rsync
need_cmd ssh
need_cmd python3

if [[ $SKIP_BUILD -eq 0 ]]; then
  need_cmd npx
  log "Building Quasar PWA..."
  (cd "$FRONTEND_DIR" && npx quasar build -m pwa)
else
  log "Skipping build (--skip-build)."
fi

[[ -d "$DIST_DIR" ]] || die "PWA dist directory not found: $DIST_DIR"
[[ -f "$DIST_DIR/index.html" ]] || die "index.html not found in $DIST_DIR"
[[ -f "$DIST_DIR/package.json" ]] || die "package.json not found in $DIST_DIR"
[[ -f "$DIST_DIR/sw.js" ]] || die "sw.js not found in $DIST_DIR"

version="$(python3 - <<'PY' "$DIST_DIR/package.json"
import json, sys
print(json.load(open(sys.argv[1], encoding='utf-8')).get('version', 'unknown'))
PY
)"

mode_args=()
if [[ $APPLY -eq 0 ]]; then
  mode_args+=(--dry-run)
  log "DRY RUN: no remote files will be changed. Pass --apply to deploy."
else
  log "APPLY MODE: remote files will be updated/deleted under $SERVER_WEB_ROOT."
fi

log "Deploying frontend version: $version"
log "Remote: $SERVER_SSH:$SERVER_WEB_ROOT/"

ssh "$SERVER_SSH" "test -d '$SERVER_WEB_ROOT'" || die "Remote web root not found: $SERVER_WEB_ROOT"

rsync -av --delete --itemize-changes \
  "${mode_args[@]}" \
  --chown="$SERVER_OWNER" \
  --exclude='/backend/' \
  --exclude='/webstat/' \
  --exclude='/cgi-bin/' \
  "$DIST_DIR/" \
  "$SERVER_SSH:$SERVER_WEB_ROOT/"

if [[ $APPLY -eq 1 ]]; then
  log "Verifying deployed package.json..."
  ssh "$SERVER_SSH" "set -e; stat -c '%U:%G %a %n' '$SERVER_WEB_ROOT/package.json'; python3 - <<'PY'
import json
print(json.load(open('$SERVER_WEB_ROOT/package.json', encoding='utf-8')).get('version'))
PY"
fi
