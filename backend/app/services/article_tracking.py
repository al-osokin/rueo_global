from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, Iterable, List, Optional, Tuple

from sqlalchemy import func, select
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


def normalize_canonical_key(text: str) -> str:
    if not text:
        return ""
    return text.replace("|", "")


def calculate_checksum_from_text(text: str) -> str:
    hasher = hashlib.sha256()
    lines = text.splitlines()
    if not lines and text:
        lines = [text]
    for line in lines:
        normalized = line.replace("\t", " ")
        normalized = re.sub(r"\s+", " ", normalized.strip())
        if not normalized:
            continue
        try:
            payload = normalized.encode("cp1251")
        except UnicodeEncodeError:
            raise ValueError(
                "Encountered characters outside cp1251 during checksum calculation"
            ) from None
        hasher.update(payload)
    return hasher.hexdigest()


@dataclass
class HeaderInfo:
    timestamp: datetime
    initials: str
    suffix: str


def parse_header_line(header: str) -> Optional[HeaderInfo]:
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
    initials = match.group("initials") or ""
    return HeaderInfo(timestamp=dt, initials=initials, suffix=suffix)


class ArticleTracker:
    def __init__(
        self,
        session: Session,
        lang: str,
        run_time: Optional[datetime] = None,
        previous_update_date: Optional[date] = None,
        override_fake_date: Optional[date] = None,
        auto_header_date: Optional[date] = None,
    ) -> None:
        self.session = session
        self.lang = lang
        self.run_time = run_time or datetime.now()
        self.previous_update_date = previous_update_date
        if override_fake_date is not None:
            fake_date = override_fake_date
        else:
            fake_date = (self.run_time - timedelta(days=1)).date()
        default_dt = datetime.strptime(FIXED_TIME, "%H:%M").time()
        self.fake_timestamp = datetime.combine(fake_date, default_dt)
        self.fake_header_prefix = self.fake_timestamp.strftime("%Y-%m-%d %H:%M")
        if auto_header_date is not None:
            auto_date = auto_header_date
        else:
            auto_date = fake_date
        self.auto_header_timestamp = datetime.combine(auto_date, default_dt)
        self.auto_header_prefix = self.auto_header_timestamp.strftime("%Y-%m-%d %H:%M")
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
            normalized_key = normalize_canonical_key(canonical_key)
            if normalized_key and normalized_key != canonical_key:
                stmt_normalized = (
                    select(ArticleState)
                    .where(ArticleState.file_state_id == file_state.id)
                    .where(func.replace(ArticleState.canonical_key, "|", "") == normalized_key)
                    .limit(1)
                )
                normalized_state = self.session.execute(stmt_normalized).scalar_one_or_none()
                if normalized_state is not None:
                    state = normalized_state
                    state.canonical_key = canonical_key
                    state.canonical_occurrence = occurrence

            if state is None and "|" in canonical_key:
                base_key = canonical_key.split("|", 1)[0]
                if base_key:
                    stmt_base = (
                        select(ArticleState)
                        .where(ArticleState.file_state_id == file_state.id)
                        .where(func.split_part(ArticleState.canonical_key, "|", 1) == base_key)
                        .where(ArticleState.canonical_occurrence == occurrence)
                        .limit(1)
                    )
                    base_state = self.session.execute(stmt_base).scalar_one_or_none()
                    if base_state is not None:
                        state = base_state
                        state.canonical_key = canonical_key
                        state.canonical_occurrence = occurrence

            stmt_by_index = (
                select(ArticleState)
                .where(ArticleState.file_state_id == file_state.id)
                .where(ArticleState.article_index == article_index)
                .limit(1)
            )
            fallback_state = self.session.execute(stmt_by_index).scalar_one_or_none()
            if fallback_state is not None:
                same_identity = (
                    fallback_state.canonical_key == canonical_key
                    and fallback_state.canonical_occurrence == occurrence
                )
                if same_identity or fallback_state.checksum == checksum:
                    state = fallback_state
                    state.canonical_key = canonical_key
                    state.canonical_occurrence = occurrence

        last_header_line = header_lines[-1] if header_lines else None
        stored_header_line: Optional[str] = None
        stored_header_info: Optional[HeaderInfo] = None
        if state is not None:
            stored_header_line = state.last_header_line
            if stored_header_line:
                stored_header_info = parse_header_line(stored_header_line)
                current_info = parse_header_line(last_header_line) if last_header_line else None
                if (
                    current_info
                    and current_info.initials == FIXED_INITIALS
                    and current_info.timestamp.strftime("%H:%M") == FIXED_TIME
                    and stored_header_info
                ):
                    if header_lines:
                        header_lines[-1] = stored_header_line
                    else:
                        header_lines.append(stored_header_line)
                    last_header_line = stored_header_line
                    current_info = stored_header_info
                if stored_header_info and (
                    not current_info or stored_header_info.timestamp > current_info.timestamp
                ):
                    if header_lines:
                        header_lines[-1] = stored_header_line
                    else:
                        header_lines.append(stored_header_line)
                    last_header_line = stored_header_line

        header_info = parse_header_line(last_header_line) if last_header_line else None

        if state is None:
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

        if not content_changed:
            if stored_header_line:
                if header_lines:
                    header_lines[-1] = stored_header_line
                else:
                    header_lines.append(stored_header_line)
            state.checksum = checksum
            state.article_index = article_index
            state.last_seen_at = self.run_time
            return header_lines

        if content_changed:
            self.summary["articles_changed"] += 1
            new_header_line = last_header_line
            stored_header_info = parse_header_line(state.last_header_line) if state.last_header_line else None

            if header_info is not None:
                header_dt = header_info.timestamp
                header_initials = header_info.initials
                suffix = header_info.suffix or ""
                last_run = state.last_seen_at or file_state.last_run_at
                preserve = False
                is_auto_header = (
                    header_initials == FIXED_INITIALS
                    and header_dt.strftime("%H:%M") == FIXED_TIME
                )

                if last_run and header_dt >= last_run and not is_auto_header:
                    preserve = True
                elif (
                    self.previous_update_date
                    and header_dt.date() >= self.previous_update_date
                    and not is_auto_header
                ):
                    preserve = True

                if not preserve:
                    suffix_to_use = suffix
                    new_header_line = f"{self.auto_header_prefix} {FIXED_INITIALS}{suffix_to_use}"
                    header_changed = True
                    self.summary["articles_auto_dated"] += 1
                    if header_lines:
                        header_lines[-1] = new_header_line
                    else:
                        header_lines.append(new_header_line)
                else:
                    if header_lines:
                        header_lines[-1] = new_header_line
            else:
                if header_lines:
                    new_header_line = header_lines[-1]
                else:
                    suffix = stored_header_info.suffix if stored_header_info else ""
                    new_header_line = f"{self.auto_header_prefix} {FIXED_INITIALS}{suffix}"
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
