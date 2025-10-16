from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app import admin
from app.database import get_session, init_db
from app.services.search import SearchService


BACKEND_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = (BACKEND_DIR.parent / "frontend").resolve()
DATA_DIR = (BACKEND_DIR / "data").resolve()

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
    klarigo_path = DATA_DIR / "tekstoj" / "klarigo.textile"
    if not klarigo_path.exists():
        raise HTTPException(status_code=404, detail="Файл с информацией об обновлении не найден")
    return {"text": klarigo_path.read_text(encoding="utf-8")}


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
