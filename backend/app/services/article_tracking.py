from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ArticleChangeLog, ArticleFileState, ArticleState


HEADER_REGEX = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2}) (?P<time>\d{2}:\d{2}) (?P<initials>[a-zA-Z0-9_]+)(?P<suffix>#?)$")
CANONICAL_REGEX = re.compile(r"\[(.+?)\]")

FIXED_INITIALS = "bk"
FIXED_TIME = "22:22"


def extract_canonical_key(text: str) -> str:
    if not text:
        return ""
    match = CANONICAL_REGEX.search(text)
    if match:
        return f"[{match.group(1)}]"
    return ""


def calculate_checksum_from_text(text: str) -> str:
    hasher = hashlib.sha256()
    for line in text.splitlines():
        normalized = line.replace("\t", " ")
        normalized = re.sub(r"\s+", " ", normalized.strip())
        if normalized:
            hasher.update(normalized.encode("utf-8"))
    return hasher.hexdigest()


def parse_header_line(header: str) -> Optional[Tuple[datetime, str]]:
    if not header:
        return None
    match = HEADER_REGEX.match(header.strip())
    if not match:
        return None
    try:
        dt = datetime.strptime(
            f"{match.group('date')} {match.group('time')}",
            "%Y-%m-%d %H:%M",
        )
    except ValueError:
        return None
    suffix = match.group("suffix") or ""
    return dt, suffix


class ArticleTracker:
    def __init__(self, session: Session, lang: str, run_time: Optional[datetime] = None) -> None:
        self.session = session
        self.lang = lang
        self.run_time = run_time or datetime.now()
        fake_date = (self.run_time - timedelta(days=1)).date()
        self.fake_timestamp = datetime.combine(fake_date, datetime.strptime(FIXED_TIME, "%H:%M").time())
        self.fake_header_prefix = self.fake_timestamp.strftime("%Y-%m-%d %H:%M")
        self.current_script_date = datetime.combine(fake_date, datetime.min.time())
        self.file_cache: Dict[str, ArticleFileState] = {}
        self.summary: Dict[str, int] = {
            "articles_total": 0,
            "articles_changed": 0,
            "articles_auto_dated": 0,
            "articles_new": 0,
        }

    def ensure_file_state(self, file_path: str, file_modified: Optional[datetime]) -> ArticleFileState:
        if file_path in self.file_cache:
            state = self.file_cache[file_path]
            if file_modified:
                state.last_modified_at = file_modified
            return state

        stmt = (
            select(ArticleFileState)
            .where(ArticleFileState.lang == self.lang)
            .where(ArticleFileState.file_path == file_path)
            .limit(1)
        )
        state = self.session.execute(stmt).scalar_one_or_none()
        if state is None:
            state = ArticleFileState(
                lang=self.lang,
                file_path=file_path,
            )
            self.session.add(state)
            self.session.flush()
        if file_modified:
            state.last_modified_at = file_modified
        self.file_cache[file_path] = state
        return state

    def finalize_file(self, state: ArticleFileState) -> None:
        state.last_run_at = self.run_time

    def process_article(
        self,
        file_state: ArticleFileState,
        article_index: int,
        canonical_key: str,
        occurrence: int,
        checksum: str,
        header_lines: List[str],
    ) -> List[str]:
        self.summary["articles_total"] += 1

        stmt = (
            select(ArticleState)
            .where(ArticleState.file_state_id == file_state.id)
            .where(ArticleState.canonical_key == canonical_key)
            .where(ArticleState.canonical_occurrence == occurrence)
            .limit(1)
        )
        state = self.session.execute(stmt).scalar_one_or_none()

        if state is None:
            stmt_by_index = (
                select(ArticleState)
                .where(ArticleState.file_state_id == file_state.id)
                .where(ArticleState.article_index == article_index)
                .limit(1)
            )
            state = self.session.execute(stmt_by_index).scalar_one_or_none()
            if state is not None:
                state.canonical_key = canonical_key
                state.canonical_occurrence = occurrence

        last_header_line = header_lines[-1] if header_lines else None
        header_info = parse_header_line(last_header_line) if last_header_line else None

        if state is None:
            # Первое обнаружение статьи
            state = ArticleState(
                file_state=file_state,
                article_index=article_index,
                canonical_key=canonical_key,
                canonical_occurrence=occurrence,
                checksum=checksum,
                last_header_line=last_header_line,
                last_seen_at=self.run_time,
            )
            self.session.add(state)
            self.summary["articles_new"] += 1
            return header_lines

        header_changed = False
        content_changed = state.checksum != checksum

        if content_changed:
            self.summary["articles_changed"] += 1
            new_header_line = last_header_line

            if header_info is not None:
                header_dt, suffix = header_info
                last_run = state.last_seen_at or file_state.last_run_at
                preserve = False
                if last_run and header_dt > last_run and header_dt < self.current_script_date:
                    preserve = True

                if not preserve:
                    new_header_line = f"{self.fake_header_prefix} {FIXED_INITIALS}{suffix}"
                    header_changed = True
                    self.summary["articles_auto_dated"] += 1
                    if header_lines:
                        header_lines[-1] = new_header_line
                else:
                    if header_lines:
                        header_lines[-1] = new_header_line
            else:
                # отсутствует корректный заголовок — создаём фиксированный
                new_header_line = f"{self.fake_header_prefix} {FIXED_INITIALS}"
                if header_lines:
                    header_lines[-1] = new_header_line
                else:
                    header_lines.append(new_header_line)
                header_changed = True
                self.summary["articles_auto_dated"] += 1

            change = ArticleChangeLog(
                file_state_id=file_state.id,
                canonical_key=canonical_key,
                canonical_occurrence=occurrence,
                old_checksum=state.checksum,
                new_checksum=checksum,
                old_header_line=state.last_header_line,
                new_header_line=header_lines[-1] if header_lines else None,
                action="auto_date" if header_changed else "content_changed",
            )
            self.session.add(change)

        state.checksum = checksum
        state.last_header_line = header_lines[-1] if header_lines else None
        state.article_index = article_index
        state.last_seen_at = self.run_time

        return header_lines

    def get_summary(self) -> Dict[str, int]:
        return dict(self.summary)
