from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, Field

from app.importer import DEFAULT_DATA_DIR, run_import


class ImportRequest(BaseModel):
    data_dir: Optional[Path] = Field(
        default=None,
        description="Каталог с исходниками. По умолчанию backend/data/src.",
    )
    truncate: bool = Field(
        default=True,
        description="Очищать таблицы перед импортом.",
    )


class ImportStatus(BaseModel):
    running: bool
    last_started: Optional[str]
    last_finished: Optional[str]
    last_error: Optional[str]


router = APIRouter(prefix="/admin", tags=["admin"])

_state_lock = threading.Lock()
_state = {
    "running": False,
    "last_started": None,
    "last_finished": None,
    "last_error": None,
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
        _update_state(running=True, last_error=None, last_started=_now_iso(), last_finished=None)
        try:
            run_import(data_dir, truncate=payload.truncate)
            _update_state(last_finished=_now_iso())
        except Exception as exc:  # noqa: BLE001
            _update_state(last_error=str(exc), last_finished=_now_iso())
        finally:
            _update_state(running=False)

    background_tasks.add_task(task)
    return ImportStatus(**_get_state())


@router.get("/import/status", response_model=ImportStatus)
def import_status() -> ImportStatus:
    return ImportStatus(**_get_state())


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
