from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, Field

from app.importer import DEFAULT_DATA_DIR, get_last_ru_letter, run_import


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
