# Deployment Spec

This spec documents what is present in the repo for running the backend locally (Docker Compose) and the key notes for server deployment (reverse proxying and static hosting headers).

Primary references
- Local containers: `docker-compose.yml`.
- Backend image build: `backend/Dockerfile`.
- Server proxy notes: `memory-bank/docs/DEPLOYMENT_NOTES.md`.
- Update/deploy script: `scripts/rueo_update.sh`.
- Frontend hosting headers (Apache-style): `frontend-app/public/.htaccess`.

## Local deployment (docker-compose)

`docker-compose.yml` defines two services:
- `db`: Postgres 13
- `backend`: FastAPI (uvicorn)

Ports (default)
- Postgres: `5432:5432`
- Backend: `8000:8000`

Backend container behavior
- Runs `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`.
- Mounts:
  - `./backend:/app`
  - `./frontend:/frontend`

Note on credentials
- Compose and code contain development defaults for DB connection strings. Do not treat them as production secrets.
- For documentation and ops, refer to variable names (for example `DATABASE_URL`) rather than copying literal values.

## Backend container image (backend/Dockerfile)

The backend Dockerfile:
- uses `python:3.9-slim`
- installs pip requirements from `backend/requirements.txt`
- copies backend code to `/app/app`
- copies static frontend files to `/frontend`
- runs uvicorn on port 8000

## Server deployment notes (nginx)

The repo does not ship a live nginx config. `memory-bank/docs/DEPLOYMENT_NOTES.md` contains a reference snippet and operational reminders.

Reference config snippet (from memory-bank)
Note: this is a reminder only, not a source of truth for deployment.
```nginx
server {
    listen 5.129.201.65:443 ssl;
    server_name rueo.ru www.rueo.ru;

    ssl_certificate     /var/www/httpd-cert/slovari/rueo.ru_le7.crtca;
    ssl_certificate_key /var/www/httpd-cert/slovari/rueo.ru_le7.key;
    ssl_dhparam         /etc/ssl/certs/dhparam4096.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    add_header Strict-Transport-Security "max-age=31536000" always;

    root /var/www/slovari/data/www/rueo.ru;
    index index.html;

    location ^~ /.well-known/acme-challenge/ {
        alias /var/www/slovari/data/www/rueo.ru/.well-known/acme-challenge/;
        default_type "text/plain";
        try_files $uri =404;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /search {
        proxy_pass http://127.0.0.1:8000/search;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    location /suggest {
        proxy_pass http://127.0.0.1:8000/suggest;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    location /status/info {
        proxy_pass http://127.0.0.1:8000/status/info;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    location /admin/import/status {
        proxy_pass http://127.0.0.1:8000/admin/import/status;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    location /admin/import {
        proxy_pass http://127.0.0.1:8000/admin/import;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    location /admin/ui {
        proxy_pass http://127.0.0.1:8000/admin/ui;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    location /orph {
        proxy_pass http://127.0.0.1:8000/orph;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

What to check if "backend is down"
- nginx upstream is alive: `curl -i http://127.0.0.1:8000/status/info` on the server
- proxy locations `/search`, `/suggest`, `/status/info`, `/admin/*`, `/orph` still point to port 8000
- SPA routing still uses `try_files ... /index.html`

Where to store the live config
- Recommended: keep nginx site config on the server and back it up in a separate private repo or storage. This repo keeps only a reference snippet.

## Frontend hosting requirements (PWA update correctness)

The Quasar PWA update mechanism relies on:
- `frontend-app/src/utils/cache-manager.js` fetching `/package.json` with no-cache headers to detect new versions.
- `frontend-app/src-pwa/custom-service-worker.js` using a `CACHE_VERSION` constant and deleting old caches on activation.

Repo-provided hosting config
- `frontend-app/public/.htaccess`:
  - disables caching for `service-worker.js` and `package.json`
  - enables long cache for static assets (`css|js|png|...`)
  - includes SPA routing rewrite rules

Important note (repo consistency)
- `.htaccess` references `api-proxy.php`, but `frontend-app/public/api-proxy.php` is not present in this repo. If production depends on those rewrites, the missing file must come from outside this repo or the rules must be adjusted in the deployment environment.

## DB transfer approach (current ops)

Current operational preference (per `memory-bank/07_Update_Automation_Jan2026.md`)
- Run the importer locally.
- Transfer the resulting database to the server via dump/restore.
- Deploy `backend/data/tekstoj/klarigo.md` and `backend/data/tekstoj/renovigxo.md` to the server web root.

Implementation reference
- `scripts/rueo_update.sh` implements dump/restore and tekstoj deployment.
