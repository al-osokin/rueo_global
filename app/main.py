from typing import Annotated

from fastapi import Depends, FastAPI, Query, Request
from sqlalchemy.orm import Session

from app import admin
from app.database import get_session, init_db
from app.services.search import SearchService


app = FastAPI(
    title="Rueo.ru API",
    description="Новый бэкенд для словаря Rueo.ru",
    version="0.1.0",
)

app.include_router(admin.router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/")
def read_root():
    return {"message": "Hello from Rueo.ru API"}


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
