import os
import re
import smtplib
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path
from typing import Annotated
from urllib.parse import unquote

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    Form,
    HTTPException,
    Query,
    Request,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app import admin
from app.database import get_session, init_db
from app.services.search import SearchService


BACKEND_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = (BACKEND_DIR.parent / "frontend").resolve()
DATA_DIR = (BACKEND_DIR / "data").resolve()
LOGS_DIR = DATA_DIR / "logs"

FEEDBACK_SECRET = os.getenv("RUEO_ORPH_KEY", "2З5")
SMTP_SETTINGS = {
    "host": os.getenv("SMTP_HOST"),
    "port": int(os.getenv("SMTP_PORT", "587")),
    "username": os.getenv("SMTP_USERNAME"),
    "password": os.getenv("SMTP_PASSWORD"),
    "from_addr": os.getenv("SMTP_FROM"),
    "from_name": os.getenv("SMTP_FROM_NAME", "RuEo"),
    "to_addr": os.getenv("SMTP_TO", os.getenv("SMTP_FROM")),
    "use_tls": os.getenv("SMTP_USE_TLS", "true").lower() != "false",
}

app = FastAPI(
    title="Rueo.ru API",
    description="Новый бэкенд для словаря Rueo.ru",
    version="0.1.0",
)

app.include_router(admin.router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/", include_in_schema=False)
def serve_frontend():
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Rueo.ru API"}


@app.get("/admin/ui", include_in_schema=False)
def serve_admin_ui():
    admin_path = FRONTEND_DIR / "admin.html"
    if not admin_path.exists():
        raise HTTPException(status_code=404, detail="Админский интерфейс не найден")
    return FileResponse(admin_path)


@app.get("/status/info")
def status_info():
    klarigo_path = DATA_DIR / "tekstoj" / "klarigo.md"
    if not klarigo_path.exists():
        raise HTTPException(status_code=404, detail="Файл с информацией об обновлении не найден")
    renovigxo_path = DATA_DIR / "tekstoj" / "renovigxo.md"
    date_line = ""
    if renovigxo_path.exists():
        try:
            date_lines = [
                line.strip()
                for line in renovigxo_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            if date_lines:
                date_line = date_lines[0]
        except UnicodeDecodeError:
            date_line = ""

    body = klarigo_path.read_text(encoding="utf-8")
    if date_line:
        combined = f"Словарь обновлён {date_line}\n{body}"
    else:
        combined = body
    return {"text": combined}


def _ensure_logs_dir() -> None:
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        # directory creation failure shouldn't crash the app; logs will simply be skipped
        pass


def _append_log(path: Path, text: str) -> None:
    try:
        _ensure_logs_dir()
        with path.open("a", encoding="utf-8") as fh:
            fh.write(text)
    except OSError:
        # ignore logging failures
        pass


def _log_orph_message(url: str, error_text: str, comment: str) -> None:
    entry = (
        f"{datetime.now():%d.%m.%Y %H:%M:%S}\n"
        f"Адрес: {url}\n"
        f"Ошибка: {error_text}\n"
        f"Комментарий: {comment}\n\n"
    )
    _append_log(LOGS_DIR / "orph.txt", entry)


def _log_mail_error(message: str) -> None:
    timestamped = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {message}\n"
    _append_log(LOGS_DIR / "mail_errors.log", timestamped)


def _send_orph_email(subject: str, body: str) -> None:
    missing = [key for key in ("host", "from_addr", "to_addr") if not SMTP_SETTINGS.get(key)]
    if missing:
        _log_mail_error(f"SMTP configuration missing keys: {', '.join(missing)}")
        return

    msg = EmailMessage()
    from_addr = SMTP_SETTINGS["from_addr"]
    from_name = SMTP_SETTINGS.get("from_name")
    msg["From"] = formataddr((from_name, from_addr)) if from_name else from_addr
    msg["To"] = SMTP_SETTINGS["to_addr"]
    msg["Subject"] = subject
    msg.set_content(body, charset="utf-8")

    try:
        with smtplib.SMTP(SMTP_SETTINGS["host"], SMTP_SETTINGS["port"], timeout=30) as server:
            if SMTP_SETTINGS.get("use_tls", True):
                server.starttls()
            username = SMTP_SETTINGS.get("username")
            password = SMTP_SETTINGS.get("password")
            if username and password:
                server.login(username, password)
            server.send_message(msg)
    except Exception as exc:  # pragma: no cover - defensive
        _log_mail_error(f"SMTP send failed: {exc}")


@app.post("/orph")
async def submit_orph(
    background_tasks: BackgroundTasks,
    url: str = Form(...),
    text: str = Form(...),
    comment: str = Form("") ,
    key: str = Form(...),
):
    if key != FEEDBACK_SECRET:
        raise HTTPException(status_code=403, detail="Недопустимый ключ")

    comment_clean = comment.strip()
    url = url.strip()
    text = text.strip()

    if not url or not text:
        raise HTTPException(status_code=400, detail="Отсутствуют обязательные поля")

    _log_orph_message(url, text, comment_clean)

    match = re.search(r"/sercxo/([^/?#]+)", url)
    subject = "Орфографическая ошибка"
    if match:
        subject = f"{unquote(match.group(1))}: орфографическая ошибка"

    body_lines = [
        f"Адрес: {url}",
        f"Ошибка: {text}",
        f"Комментарий: {comment_clean}" if comment_clean else "Комментарий: (нет)",
    ]
    body = "\n".join(body_lines)

    background_tasks.add_task(_send_orph_email, subject, body)

    return {"status": "ok"}


DbSession = Annotated[Session, Depends(get_session)]


@app.get("/search")
def search(
    query: Annotated[str, Query(min_length=1)],
    request: Request,
    db: DbSession,
):
    service = SearchService(db)
    client_ip = request.client.host if request.client else None
    return service.search(query, client_ip=client_ip)


@app.get("/suggest")
def suggest(term: Annotated[str, Query(min_length=1)], db: DbSession):
    service = SearchService(db)
    return service.suggest(term)
