# Deployment notes (rueo)

## Nginx (rueo.ru)

На сервере nginx проксирует некоторые пути на FastAPI (127.0.0.1:8000), а остальное отдаёт как статический SPA.

### Пример конфигурации (справочно)

> Это **не** “источник истины” и не файл для деплоя — просто памятка, чтобы быстро восстановить настройку, если что-то сломается.

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

    # ACME challenge files for ISP Manager / Let's Encrypt
    location ^~ /.well-known/acme-challenge/ {
        alias /var/www/slovari/data/www/rueo.ru/.well-known/acme-challenge/;
        default_type "text/plain";
        try_files $uri =404;
    }

    # статический SPA
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API → FastAPI
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

### Что проверить, если “сломался бэкенд”

- nginx: что upstream жив (`curl -i http://127.0.0.1:8000/status/info` на сервере)
- что location’ы `/search`, `/suggest`, `/status/info`, `/admin/*`, `/orph` всё ещё проксируются на 8000
- что SPA отдаётся через `try_files ... /index.html`

## Где хранить “живую” конфигурацию

Рекомендуемый вариант: держать на сервере как nginx site conf + делать бэкап в отдельном приватном репозитории/хранилище.
В этом репо держим только памятку (как выше).
