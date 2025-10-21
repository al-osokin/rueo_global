from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.importer import DEFAULT_DATA_DIR, get_last_ru_letter, run_import
from app.database import get_session
from app.services.article_review import ArticleReviewService


class ImportRequest(BaseModel):
    data_dir: Optional[Path] = Field(
        default=None,
        description="Каталог с исходниками. По умолчанию backend/data/src.",
    )
    truncate: bool = Field(
        default=True,
        description="Очищать таблицы перед импортом.",
    )
    last_ru_letter: Optional[str] = Field(
        default=None,
        description="Последнее готовое слово русского словаря (например, прегрешить).",
    )


class ImportStatus(BaseModel):
    running: bool
    last_started: Optional[str]
    last_finished: Optional[str]
    last_error: Optional[str]
    progress: Optional[Dict[str, Any]] = None
    stats: Optional[Dict[str, Any]] = None
    last_ru_letter: Optional[str] = None


router = APIRouter(prefix="/admin", tags=["admin"])

SUPPORTED_REVIEW_LANGS = {"eo", "ru"}


class ArticleSearchItem(BaseModel):
    art_id: int
    headword: Optional[str]
    parsing_status: Optional[str]


class ArticleReviewPayload(BaseModel):
    art_id: int
    lang: str
    headword: Optional[str]
    template: Optional[str]
    success: bool
    parsing_status: Optional[str]
    groups: List[Dict[str, Any]]
    auto_candidates: List[str]
    resolved_translations: Dict[str, Any]
    notes: List[Dict[str, Any]]
    review_notes: List[str]


class ArticleStats(BaseModel):
    total: int
    needs_review: int
    reviewed: int


class ReviewUpdateRequest(BaseModel):
    resolved_translations: Optional[Dict[str, Any]] = None
    comment: Optional[str] = None
    author: Optional[str] = None


class ReviewUpdateResponse(BaseModel):
    next_art_id: Optional[int]


class ReparseRequest(BaseModel):
    art_ids: Optional[List[int]] = None
    include_pending: bool = False


class ReparseResponse(BaseModel):
    summary: Dict[str, Any]
    updated: int
    failed_details: List[Dict[str, Any]]

_state_lock = threading.Lock()
_state = {
    "running": False,
    "last_started": None,
    "last_finished": None,
    "last_error": None,
    "progress": None,
    "stats": None,
    "last_ru_letter": get_last_ru_letter(DEFAULT_DATA_DIR),
}


def _update_state(**kwargs) -> None:
    with _state_lock:
        _state.update(kwargs)


def _get_state() -> dict:
    with _state_lock:
        return dict(_state)


@router.post(
    "/import",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ImportStatus,
)
def trigger_import(payload: ImportRequest, background_tasks: BackgroundTasks) -> ImportStatus:
    state = _get_state()
    if state["running"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Импорт уже выполняется.",
        )

    data_dir = payload.data_dir or DEFAULT_DATA_DIR
    if not data_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Каталог {data_dir} не найден.",
        )

    def task() -> None:
        effective_letter = payload.last_ru_letter or get_last_ru_letter(data_dir)
        _update_state(
            running=True,
            last_error=None,
            last_started=_now_iso(),
            last_finished=None,
            progress={"stage": "initializing"},
            last_ru_letter=effective_letter,
        )
        try:
            run_import(
                data_dir,
                truncate=payload.truncate,
                status_callback=_progress_callback,
                last_ru_letter=payload.last_ru_letter,
            )
            _update_state(last_finished=_now_iso())
        except Exception as exc:  # noqa: BLE001
            _update_state(
                last_error=str(exc),
                last_finished=_now_iso(),
                progress={"stage": "error", "message": str(exc)},
            )
        finally:
            _update_state(running=False)

    background_tasks.add_task(task)
    return ImportStatus(**_get_state())


@router.get("/import/status", response_model=ImportStatus)
def import_status() -> ImportStatus:
    state = _get_state()
    if not state.get("last_ru_letter"):
        state["last_ru_letter"] = get_last_ru_letter(DEFAULT_DATA_DIR)
    return ImportStatus(**state)


def _progress_callback(update: Dict[str, Any]) -> None:
    update_copy = dict(update)
    stats = update_copy.pop("stats", None)
    current = _get_state()
    last_letter = current.get("last_ru_letter")
    if stats:
        ru_stats = stats.get("ru") if isinstance(stats, dict) else None
        if isinstance(ru_stats, dict):
            last_letter = ru_stats.get("ready_last_word", last_letter)
    _update_state(
        progress=update_copy,
        stats=stats or current.get("stats"),
        last_ru_letter=last_letter,
    )


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _ensure_lang(lang: str) -> str:
    if lang not in SUPPORTED_REVIEW_LANGS:
        raise HTTPException(status_code=404, detail="Unsupported language")
    return lang


@router.get("/articles/{lang}", response_model=List[ArticleSearchItem])
def search_articles(
    lang: str,
    query: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    session=Depends(get_session),
):
    _ensure_lang(lang)
    service = ArticleReviewService(session)
    return service.search_articles(lang, query, limit, status)


@router.get("/articles/{lang}/queue", response_model=Optional[ArticleSearchItem])
def next_article(
    lang: str,
    after: Optional[int] = Query(None),
    mode: str = Query("next"),
    session=Depends(get_session),
):
    _ensure_lang(lang)
    service = ArticleReviewService(session)
    if mode == "spotcheck":
        return service.get_queue_item(lang, status="reviewed", random=True)
    return service.get_queue_item(lang, status="needs_review", after=after)


@router.get("/articles/{lang}/stats", response_model=ArticleStats)
def get_article_stats(lang: str, session=Depends(get_session)):
    _ensure_lang(lang)
    service = ArticleReviewService(session)
    stats = service.get_statistics(lang)
    return ArticleStats(**stats)


@router.get("/articles/{lang}/{art_id}", response_model=ArticleReviewPayload)
def get_article_review(lang: str, art_id: int, session=Depends(get_session)):
    _ensure_lang(lang)
    service = ArticleReviewService(session)
    return service.load_article(lang, art_id)


@router.post("/articles/{lang}/{art_id}", response_model=ReviewUpdateResponse)
def update_article_review(
    lang: str,
    art_id: int,
    payload: ReviewUpdateRequest,
    session=Depends(get_session),
):
    _ensure_lang(lang)
    service = ArticleReviewService(session)
    result = service.save_review(
        lang,
        art_id,
        resolved_translations=payload.resolved_translations,
        comment=payload.comment,
        author=payload.author,
    )
    return ReviewUpdateResponse(**result)


@router.post("/articles/{lang}/{art_id}/reset", response_model=ArticleReviewPayload)
def reset_article_review(
    lang: str,
    art_id: int,
    session=Depends(get_session),
):
    _ensure_lang(lang)
    service = ArticleReviewService(session)
    return service.reset_article(lang, art_id)


@router.post("/articles/{lang}/reparse", response_model=ReparseResponse)
def reparse_article_batch(
    lang: str,
    payload: ReparseRequest,
    session=Depends(get_session),
):
    _ensure_lang(lang)
    service = ArticleReviewService(session)
    result = service.reparse_articles(
        lang,
        art_ids=payload.art_ids,
        include_pending=payload.include_pending,
    )
    return ReparseResponse(**result)
