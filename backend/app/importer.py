from __future__ import annotations

import argparse
import json
import logging
import os
import re
from collections import OrderedDict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from sqlalchemy import func, insert, select, text
from sqlalchemy.orm import Session

from app.database import SessionLocal, init_db
from app.models import (
    Article,
    ArticleRu,
    FuzzyEntry,
    SearchEntry,
    SearchEntryRu,
)
from app.services.article_tracking import (
    ArticleTracker,
    calculate_checksum_from_text,
    extract_canonical_key,
)

BASE_DIR = Path(__file__).resolve().parent.parent

def _resolve_default_data_dir() -> Path:
    env_value = os.getenv("RUEO_DATA_DIR")
    if env_value:
        candidate = Path(env_value).expanduser()
        if not candidate.is_absolute():
            candidate = (BASE_DIR / candidate).resolve()
        else:
            candidate = candidate.resolve()
        return candidate
    return (BASE_DIR / "data/src").resolve()


DEFAULT_DATA_DIR = _resolve_default_data_dir()

ProgressCallback = Callable[[Dict[str, Any]], None]

LOGGER = logging.getLogger(__name__)

LANG_DIRS = {
    "eo": "VortaroER-daily",
    "ru": "VortaroRE-daily",
}

ARTICLE_PATTERN = re.compile(
    r"(?P<redaktoroj>^\d.[^\[]*)(?P<vorto>.*?)(?:\r?\n)\s*(?:\r?\n)",
    re.MULTILINE | re.DOTALL,
)

HEADER_PATTERN = re.compile(r"^\[(.+?)\]", re.MULTILINE | re.DOTALL)
STRUCTURE_HEADER_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2} \d{1,2}:\d{2} [A-Za-z0-9_]+#?$")
STRUCTURE_WORD_PATTERN = re.compile(r"^\[[^\]]+\]")


def _make_notifier(callback: Optional[ProgressCallback]) -> ProgressCallback:
    def _notify(stage: str, **payload: Any) -> None:
        if callback:
            callback({"stage": stage, **payload})

    return _notify


def _detect_structure_issues(lines: Sequence[str]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    idx = 0
    current_headers: List[Dict[str, Any]] = []

    while idx < len(lines):
        stripped = lines[idx].strip()

        if not stripped:
            current_headers = []
            idx += 1
            continue

        if STRUCTURE_HEADER_PATTERN.match(stripped):
            header_block: List[Dict[str, Any]] = []
            while idx < len(lines) and STRUCTURE_HEADER_PATTERN.match(lines[idx].strip()):
                header_block.append({"line": idx + 1, "header": lines[idx].strip()})
                idx += 1

            current_headers = header_block

            if idx >= len(lines):
                issues.append(
                    {
                        "type": "header_without_word",
                        "headers": header_block,
                        "message": "файл заканчивается сразу после блока заголовков",
                    }
                )
                break

            next_stripped = lines[idx].strip()
            if not next_stripped or not STRUCTURE_WORD_PATTERN.match(next_stripped):
                issues.append(
                    {
                        "type": "header_without_word",
                        "headers": header_block,
                        "next_line": next_stripped,
                    }
                )
            continue

        if STRUCTURE_WORD_PATTERN.match(stripped) and not current_headers:
            issues.append(
                {
                    "type": "word_without_header",
                    "line": idx + 1,
                    "word": stripped,
                    "context": lines[max(0, idx - 3) : idx + 2],
                }
            )

        idx += 1

    return issues


def _parse_russian_date(line: str) -> Optional[date]:
    line = line.strip()
    if not line:
        return None
    match = re.match(r"^(\d{1,2})\s+([А-Яа-яЁё]+)\s+(\d{4})", line)
    if not match:
        return None
    day_str, month_str, year_str = match.groups()
    month_map = {
        "января": 1,
        "февраля": 2,
        "марта": 3,
        "апреля": 4,
        "мая": 5,
        "июня": 6,
        "июля": 7,
        "августа": 8,
        "сентября": 9,
        "октября": 10,
        "ноября": 11,
        "декабря": 12,
    }
    month = month_map.get(month_str.lower())
    if not month:
        return None
    try:
        return date(int(year_str), month, int(day_str))
    except ValueError:
        return None


def _load_previous_update_date(data_dir: Path) -> Optional[date]:
    candidates = [
        data_dir / "tekstoj" / "renovigxo.md",
        BASE_DIR / "data" / "tekstoj" / "renovigxo.md",
    ]
    updates_path = next((path for path in candidates if path.exists()), None)
    if updates_path is None:
        return None
    unique_dates: List[date] = []
    with updates_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            parsed = _parse_russian_date(line)
            if not parsed:
                continue
            if not unique_dates or unique_dates[-1] != parsed:
                unique_dates.append(parsed)
            if len(unique_dates) >= 2:
                break
    if len(unique_dates) >= 2:
        return unique_dates[1]
    if unique_dates:
        return unique_dates[0]
    return None


def run_import(
    data_dir: Path,
    truncate: bool = True,
    status_callback: Optional[ProgressCallback] = None,
    last_ru_letter: Optional[str] = None,
) -> None:
    data_dir = data_dir.resolve()
    init_db()

    notify = _make_notifier(status_callback)
    notify("initializing", message="Старт импорта данных")

    run_time = datetime.now()
    previous_update_date = _load_previous_update_date(data_dir)
    eo_summary: Dict[str, int] = {}
    ru_summary: Dict[str, int] = {}

    with SessionLocal() as session:
        if truncate:
            notify("truncating", message="Очистка таблиц перед загрузкой")
            _truncate_tables(session)

        LOGGER.info("Processing Esperanto data…")
        notify("processing_files", lang="eo", current=0, total=0, message="Начало обработки файлов")
        eo_count, eo_summary, eo_structure_issues = _process_language(
            session,
            data_dir,
            "eo",
            run_time,
            previous_update_date=previous_update_date,
            progress_callback=lambda update: notify(
                "processing_files", lang="eo", **update
            ),
        )
        LOGGER.info("Inserted %d Esperanto articles", eo_count)
        notify("tracking_summary", lang="eo", summary=eo_summary)
        if eo_structure_issues:
            notify(
                "structure_issues",
                lang="eo",
                issues=eo_structure_issues,
            )
        LOGGER.info("Processing Russian data…")
        notify("processing_files", lang="ru", current=0, total=0, message="Начало обработки файлов")
        ru_count, ru_summary, ru_structure_issues = _process_language(
            session,
            data_dir,
            "ru",
            run_time,
            previous_update_date=previous_update_date,
            progress_callback=lambda update: notify(
                "processing_files", lang="ru", **update
            ),
        )
        LOGGER.info("Inserted %d Russian articles", ru_count)
        notify("tracking_summary", lang="ru", summary=ru_summary)
        if ru_structure_issues:
            notify(
                "structure_issues",
                lang="ru",
                issues=ru_structure_issues,
            )
        session.commit()

        LOGGER.info("Building search indices for Esperanto…")
        notify("building_index", lang="eo", current=0, total=0, message="Создание поисковых индексов")
        eo_words = _create_index_table(
            session,
            "eo",
            progress_callback=lambda update: notify(
                "building_index", lang="eo", **update
            ),
        )
        LOGGER.info("Inserted %d Esperanto search entries", eo_words)
        LOGGER.info("Building search indices for Russian…")
        notify("building_index", lang="ru", current=0, total=0, message="Создание поисковых индексов")
        ru_words = _create_index_table(
            session,
            "ru",
            progress_callback=lambda update: notify(
                "building_index", lang="ru", **update
            ),
        )
        LOGGER.info("Inserted %d Russian search entries", ru_words)
        session.commit()

        LOGGER.info("Updating fuzzy search table…")
        notify("updating_fuzzy", message="Обновление таблицы нечёткого поиска")
        fuzzy_count = _update_neklaraj(
            session,
            "sercxo",
            progress_callback=lambda update: notify("updating_fuzzy", **update),
        )
        LOGGER.info("Inserted %d fuzzy entries", fuzzy_count)
        session.commit()

        letter = _load_last_ru_letter(data_dir, last_ru_letter)
        if letter:
            _save_last_ru_letter(data_dir, letter)
        stats = _collect_stats(session, letter)
        if eo_summary:
            stats.setdefault("eo", {}).update({"tracking": eo_summary})
        if eo_structure_issues:
            stats.setdefault("eo", {})["structure_issues"] = eo_structure_issues
        if ru_summary:
            stats.setdefault("ru", {}).update({"tracking": ru_summary})
        if ru_structure_issues:
            stats.setdefault("ru", {})["structure_issues"] = ru_structure_issues
        stats.setdefault("meta", {})["run_at"] = run_time.isoformat()
        notify("finalizing", message="Формирование служебных файлов", stats=stats)
        _write_status_file(data_dir, stats, run_time)
        notify("completed", message="Импорт завершён", stats=stats)


def _truncate_tables(session: Session) -> None:
    tables = ["sercxo", "sercxo_ru", "artikoloj", "artikoloj_ru", "neklaraj"]
    for table in tables:
        session.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
    session.commit()


def _process_language(
    session: Session,
    data_dir: Path,
    lang: str,
    run_time: datetime,
    previous_update_date: Optional[date] = None,
    progress_callback: Optional[ProgressCallback] = None,
) -> Tuple[int, Dict[str, int], Dict[str, List[Dict[str, Any]]]]:
    lang_dir_name = LANG_DIRS[lang]
    lang_dir = data_dir / lang_dir_name
    if not lang_dir.exists():
        raise FileNotFoundError(f"Directory not found: {lang_dir}")

    article_table = Article.__table__ if lang == "eo" else ArticleRu.__table__

    files = sorted(
        file_path
        for file_path in lang_dir.iterdir()
        if file_path.is_file() and file_path.suffix.lower() == ".txt"
    )

    total_files = len(files)
    if progress_callback:
        progress_callback({"current": 0, "total": total_files})

    total_inserted = 0
    tracker = ArticleTracker(
        session,
        lang,
        run_time,
        previous_update_date=previous_update_date,
    )
    structure_alerts: Dict[str, List[Dict[str, Any]]] = {}

    for index, file_path in enumerate(files, start=1):
        entries, file_structure_issues = _parse_articles(file_path)
        if file_structure_issues:
            rel_path_str = str(Path(lang_dir_name) / file_path.name)
            structure_alerts[rel_path_str] = file_structure_issues
            LOGGER.warning(
                "Обнаружены структурные проблемы в %s (%d шт.)",
                rel_path_str,
                len(file_structure_issues),
            )
        if not entries:
            if progress_callback:
                progress_callback(
                    {
                        "current": index,
                        "total": total_files,
                        "filename": file_path.name,
                        "inserted": 0,
                    }
                )
            continue

        rel_path = Path(lang_dir_name) / file_path.name
        file_state = tracker.ensure_file_state(
            str(rel_path),
            datetime.fromtimestamp(file_path.stat().st_mtime),
        )

        insert_payload = []
        for article_index, entry in enumerate(entries):
            header_lines = list(entry.get("header_lines") or [])
            original_header_lines = list(header_lines)
            updated_lines = tracker.process_article(
                file_state=file_state,
                article_index=article_index,
                canonical_key=entry.get("canonical_key", ""),
                occurrence=entry.get("canonical_occurrence", 0),
                checksum=entry.get("checksum") or "",
                header_lines=header_lines,
            )
            if updated_lines is not None:
                entry["header_lines"] = list(updated_lines)
            if original_header_lines != entry.get("header_lines"):
                entry["header_changed"] = True
            if updated_lines:
                entry["komento"] = ", ".join(updated_lines)
            insert_payload.append(
                {
                    "priskribo": entry["priskribo"],
                    "lasta": "j",
                    "uz_id": 1,
                    "komento": entry["komento"],
                }
            )

        tracker.finalize_file(file_state)
        if lang == "ru":
            _rewrite_source_file_if_needed(file_path, entries)
        session.execute(insert(article_table), insert_payload)
        total_inserted += len(insert_payload)
        if progress_callback:
            progress_callback(
                {
                    "current": index,
                    "total": total_files,
                    "filename": file_path.name,
                    "inserted": len(insert_payload),
                }
            )

    return total_inserted, tracker.get_summary(), structure_alerts


def _parse_articles(file_path: Path) -> Tuple[List[Dict[str, Optional[str]]], List[Dict[str, Any]]]:
    raw = file_path.read_bytes()
    text_original = raw.decode("cp1251")
    text_cp = text_original
    text_cp += "\r\n\r\n"

    structure_issues = _detect_structure_issues(text_original.splitlines())
    entries: List[Dict[str, Optional[str]]] = []
    canonical_counts: Dict[str, int] = {}
    original_length = len(text_original)
    for match in ARTICLE_PATTERN.finditer(text_cp):
        redaktoroj = match.group("redaktoroj") or ""
        header_lines = [
            line.strip()
            for line in redaktoroj.replace("\r\n", "\n").split("\n")
            if line.strip()
        ]
        body_raw = match.group("vorto") or ""
        priskribo = body_raw.rstrip()
        canonical_key = extract_canonical_key(priskribo)
        if not canonical_key:
            canonical_key = f"{file_path.name}#{len(entries)}"
        occurrence = canonical_counts.get(canonical_key, 0)
        canonical_counts[canonical_key] = occurrence + 1

        span_start, span_end = match.span()
        span_start = min(span_start, original_length)
        span_end = min(span_end, original_length)

        total_header_text = redaktoroj
        total_body_text = body_raw
        matched_original = text_original[span_start:span_end]
        consumed = len(total_header_text) + len(total_body_text)
        if consumed > len(matched_original):
            consumed = len(matched_original)
        total_tail = matched_original[consumed:]
        checksum = calculate_checksum_from_text(priskribo)
        entries.append(
            {
                "komento": (", ".join(header_lines) if header_lines else None),
                "priskribo": priskribo,
                "header_lines": header_lines,
                "original_header_text": total_header_text,
                "body_raw": body_raw,
                "tail_text": total_tail,
                "full_block": match.group(0),
                "header_changed": False,
                "span": (span_start, span_end),
                "canonical_key": canonical_key,
                "canonical_occurrence": occurrence,
                "checksum": checksum,
            }
        )
    return entries, structure_issues


def _rewrite_source_file_if_needed(file_path: Path, entries: Sequence[Dict[str, Any]]) -> None:
    if not any(entry.get("header_changed") for entry in entries):
        return

    try:
        original_text = file_path.read_text(encoding="cp1251")
    except (UnicodeDecodeError, FileNotFoundError):
        return

    pieces: List[str] = []
    last_pos = 0
    text_length = len(original_text)

    for entry in entries:
        span = entry.get("span")
        if not span:
            continue
        start, end = span
        start = min(start, text_length)
        end = min(end, text_length)
        pieces.append(original_text[last_pos:start])

        original_header_text = entry.get("original_header_text") or ""
        header_lines = entry.get("header_lines") or []
        body_raw = entry.get("body_raw") or ""
        tail_text = entry.get("tail_text")
        if tail_text is None:
            full_block = entry.get("full_block") or (original_header_text + body_raw)
            consumed = len(original_header_text) + len(body_raw)
            tail_text = ""
            if full_block and consumed <= len(full_block):
                tail_text = full_block[consumed:]
        tail_text = tail_text or ""

        line_break = "\r\n" if "\r\n" in original_header_text else "\n"
        header_text = ""
        if header_lines:
            header_text = line_break.join(header_lines)
            if not header_text.endswith(line_break):
                header_text += line_break

        pieces.append(f"{header_text}{body_raw}{tail_text}")
        last_pos = end

    pieces.append(original_text[last_pos:])
    new_text = "".join(pieces)
    if new_text != original_text:
        file_path.write_text(new_text, encoding="cp1251")


def _create_index_table(
    session: Session,
    lang: str,
    progress_callback: Optional[ProgressCallback] = None,
) -> int:
    article_model = Article if lang == "eo" else ArticleRu
    search_table = SearchEntry.__table__ if lang == "eo" else SearchEntryRu.__table__

    session.execute(
        text(f"TRUNCATE TABLE {search_table.name} RESTART IDENTITY CASCADE")
    )

    total_articles = session.execute(
        select(func.count()).select_from(article_model)
    ).scalar()
    if total_articles is None:
        total_articles = 0
    if progress_callback:
        progress_callback({"current": 0, "total": total_articles})

    word_count = 0
    rows = session.execute(
        select(article_model.art_id, article_model.priskribo).order_by(
            article_model.art_id
        )
    )
    for index, (art_id, priskribo) in enumerate(rows, start=1):
        if not priskribo:
            continue
        tokens = _build_search_tokens(priskribo)
        if not tokens:
            continue

        payload = []
        for token in tokens:
            token = token.strip()
            if not token:
                continue
            normalized = token
            if lang == "ru":
                normalized = normalized.replace("`", "")
            payload.append({"art_id": art_id, "vorto": normalized})
            word_count += 1
            if lang == "ru" and "ё" in normalized:
                payload.append(
                    {"art_id": art_id, "vorto": normalized.replace("ё", "е")}
                )
                word_count += 1
        if payload:
            session.execute(insert(search_table), payload)
        if progress_callback and index % 200 == 0:
            progress_callback({"current": index, "total": total_articles})
    if progress_callback:
        progress_callback({"current": total_articles, "total": total_articles})
    return word_count


def _build_search_tokens(priskribo: str) -> List[str]:
    matches = HEADER_PATTERN.findall(priskribo)
    if not matches:
        return []

    cleaned_headers = [
        re.sub(r"(_.+_)", "", header, flags=re.IGNORECASE | re.DOTALL)
        for header in matches
    ]
    radiko_candidates = cleaned_headers[0].split(",")

    radiko: List[str] = []
    newarr: List[str] = []
    additional_headers: List[str] = []

    for candidate in radiko_candidates:
        candidate = candidate.strip()
        if not candidate:
            continue

        if "~" not in candidate:
            stripped = candidate.translate(str.maketrans("", "", "()|/"))
            stripped = stripped.strip()
            if stripped:
                newarr.append(stripped)

            cleaned = re.sub(r"\(\w+\)", "", candidate)
            cleaned = cleaned.replace("|", "").replace("/", "").strip()
            if cleaned:
                newarr.append(cleaned)

        tmp1_src = candidate.replace("/", "").strip()
        parts = tmp1_src.split("|")
        first = parts[0].strip() if parts else ""
        if not first:
            continue

        if not first.startswith("~"):
            without_parens = re.sub(r"\(\w+\)", "", first).strip()
            paren_removed = first.replace("(", "").replace(")", "").strip()
            if without_parens:
                radiko.append(without_parens)
            if paren_removed:
                radiko.append(paren_removed)
        else:
            additional_headers.append(first)

    match_words = cleaned_headers + additional_headers
    radiko_unique = _unique_preserve(radiko)

    for root in radiko_unique:
        root_clean = root.replace("!", "")
        root_clean = re.sub(r"( I+)", "", root_clean).strip()
        if not root_clean:
            continue

        for header in match_words[1:]:
            header = header.strip()
            if not header:
                continue
            header = header.replace("/", "")
            if not header:
                continue

            if not root_clean.endswith("-"):
                newarr.append(header.replace("~", root_clean))
            else:
                newarr.append(header.replace("~", root_clean[:-1]))

    newestarr: List[str] = []
    for entry in newarr:
        entry = entry.strip()
        if not entry:
            continue

        if "..." not in entry:
            parts = entry.split(",")
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                if "(" in part:
                    without_brackets = part.replace("(", "").replace(")", "").strip()
                    if without_brackets:
                        newestarr.append(without_brackets)
                    pattern_removed = re.sub(r"\(\w+\)", "", part).strip()
                    if pattern_removed:
                        newestarr.append(pattern_removed)
                else:
                    newestarr.append(part)

            if "." in entry:
                newestarr.append(entry.replace(".", ""))
                newestarr.append(entry.replace(".", ". ").strip())
        else:
            parts = entry.split(";")
            for part in parts:
                part = part.strip()
                if part:
                    newestarr.append(part)

    return _unique_preserve(newestarr)


def _unique_preserve(values: Sequence[str]) -> List[str]:
    seen = OrderedDict()
    for value in values:
        if not value:
            continue
        if value not in seen:
            seen[value] = None
    return list(seen.keys())


def _update_neklaraj(
    session: Session,
    table_name: str,
    progress_callback: Optional[ProgressCallback] = None,
) -> int:
    session.execute(text("TRUNCATE TABLE neklaraj RESTART IDENTITY CASCADE"))

    fuzzy_table = FuzzyEntry.__table__
    seen: set[str] = set()
    inserted = 0

    exclamation_rows = session.execute(
        text(f"SELECT DISTINCT vorto FROM {table_name} WHERE vorto LIKE :pattern"),
        {"pattern": "%!%"},
    ).scalars()

    for vorto in exclamation_rows:
        if not vorto or vorto in seen:
            continue
        seen.add(vorto)
        fuzzy = vorto.split("!")[0]
        session.execute(
            insert(fuzzy_table),
            [{"neklara_vorto": fuzzy, "klara_vorto": vorto}],
        )
        inserted += 1
        if progress_callback and inserted % 100 == 0:
            progress_callback({"count": inserted, "phase": "exclamation"})

    if progress_callback:
        progress_callback({"count": inserted, "phase": "exclamation"})

    hyphen_rows = session.execute(
        text(f"SELECT DISTINCT vorto FROM {table_name} WHERE vorto LIKE :pattern"),
        {"pattern": "%-%"},
    ).scalars()

    for vorto in hyphen_rows:
        if not vorto or vorto in seen:
            continue
        seen.add(vorto)
        part = vorto.split(" ")[0]
        fuzzy = part.replace("-", "")
        session.execute(
            insert(fuzzy_table),
            [{"neklara_vorto": fuzzy, "klara_vorto": vorto}],
        )
        inserted += 1
        if progress_callback and inserted % 100 == 0:
            progress_callback({"count": inserted, "phase": "hyphen"})

    if progress_callback:
        progress_callback({"count": inserted, "phase": "hyphen"})

    return inserted


def _load_last_ru_letter(data_dir: Path, provided: Optional[str]) -> Optional[str]:
    if provided:
        return provided.strip()
    candidate = data_dir / "last-ru-letter.txt"
    if candidate.exists():
        for encoding in ("utf-8", "cp1251"):
            try:
                return candidate.read_text(encoding=encoding).strip()
            except UnicodeDecodeError:
                continue
    return None


def get_last_ru_letter(data_dir: Path = DEFAULT_DATA_DIR) -> Optional[str]:
    data_dir = data_dir.resolve()
    return _load_last_ru_letter(data_dir, None)


def _collect_stats(session: Session, last_ru_letter: Optional[str]) -> Dict[str, Dict[str, Any]]:
    stats: Dict[str, Dict[str, Any]] = {
        "eo": {
            "articles": session.execute(select(func.count()).select_from(Article)).scalar() or 0,
            "words": session.execute(select(func.count()).select_from(SearchEntry)).scalar() or 0,
        },
        "ru": {
            "articles": session.execute(select(func.count()).select_from(ArticleRu)).scalar() or 0,
            "words": session.execute(select(func.count()).select_from(SearchEntryRu)).scalar() or 0,
        },
    }

    if last_ru_letter:
        ready_articles, ready_words = _calculate_ru_ready(session, last_ru_letter)
        stats["ru"]["ready_articles"] = ready_articles
        stats["ru"]["ready_words"] = ready_words
        stats["ru"]["ready_last_word"] = last_ru_letter
    return stats


def _calculate_ru_ready(session: Session, last_word: str) -> Tuple[int, int]:
    row = session.execute(
        select(SearchEntryRu.art_id, SearchEntryRu.id)
        .where(SearchEntryRu.vorto.like(f"{last_word}%"))
        .order_by(SearchEntryRu.vorto.desc())
        .limit(1)
    ).first()

    if not row:
        return 0, 0

    art_id, row_id = row
    # Total words up to this article
    total_words = session.execute(
        select(func.count()).select_from(SearchEntryRu).where(SearchEntryRu.art_id <= art_id)
    ).scalar() or 0
    # Words with ё should be excluded, как в оригинальном скрипте
    yo_words = session.execute(
        select(func.count()).select_from(SearchEntryRu).where(
            (SearchEntryRu.art_id <= art_id) & (SearchEntryRu.vorto.like("%ё%"))
        )
    ).scalar() or 0

    ready_words = total_words - yo_words
    ready_articles = session.execute(
        select(func.count()).select_from(ArticleRu).where(ArticleRu.art_id <= art_id)
    ).scalar() or art_id
    return ready_articles, ready_words


def _save_last_ru_letter(data_dir: Path, last_word: str) -> None:
    if not last_word:
        return
    target = data_dir / "last-ru-letter.txt"
    target.write_text(last_word, encoding="utf-8")


def _write_status_file(
    data_dir: Path,
    stats: Dict[str, Dict[str, Any]],
    run_time: datetime,
) -> None:
    base_dir = data_dir
    if base_dir.name == "src":
        base_dir = base_dir.parent
    tekstoj_dir = base_dir / "tekstoj"
    tekstoj_dir.mkdir(parents=True, exist_ok=True)

    eo_articles = stats["eo"].get("articles", 0)
    eo_words = stats["eo"].get("words", 0)

    ru_ready_articles = stats["ru"].get("ready_articles", stats["ru"].get("articles", 0))
    ru_ready_words = stats["ru"].get("ready_words", stats["ru"].get("words", 0))
    last_word = stats["ru"].get("ready_last_word")
    range_text = f"диапазон А — {last_word}" if last_word else "диапазон А — …"

    content = (
        "Открыты для поиска:\n"
        f"большой эсперанто-русский словарь в актуальной редакции, {eo_words} cлова в {eo_articles} словарных статьях;\n"
        f"рабочие материалы большого русско-эсперантского словаря ({range_text}), {ru_ready_words} cлов в {ru_ready_articles} словарных статьях."
    )
    klarigo_path = tekstoj_dir / "klarigo.md"
    try:
        klarigo_path.write_text(content, encoding="utf-8")
    except PermissionError as exc:
        LOGGER.warning("Не удалось записать %s: %s", klarigo_path, exc)

    tracking_summary = {
        "run_at": stats.get("meta", {}).get("run_at") or run_time.isoformat(),
        "eo": stats.get("eo", {}).get("tracking", {}),
        "ru": stats.get("ru", {}).get("tracking", {}),
    }
    tracking_path = tekstoj_dir / "tracking-summary.json"
    try:
        tracking_path.write_text(
            json.dumps(tracking_summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except PermissionError as exc:
        LOGGER.warning("Не удалось записать %s: %s", tracking_path, exc)

    _update_renovigxo_file(tekstoj_dir, run_time)


def _format_russian_date(dt: datetime) -> str:
    months = {
        1: "января",
        2: "февраля",
        3: "марта",
        4: "апреля",
        5: "мая",
        6: "июня",
        7: "июля",
        8: "августа",
        9: "сентября",
        10: "октября",
        11: "ноября",
        12: "декабря",
    }
    month_name = months.get(dt.month, "")
    return f"{dt.day} {month_name} {dt.year} года"


def _update_renovigxo_file(tekstoj_dir: Path, run_time: datetime) -> None:
    renovigxo_path = tekstoj_dir / "renovigxo.md"
    latest_entry = _format_russian_date(run_time)

    existing_lines: List[str] = []
    if renovigxo_path.exists():
        try:
            existing_lines = [
                line.rstrip("\n")
                for line in renovigxo_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        except UnicodeDecodeError:
            existing_lines = []
        except PermissionError as exc:
            LOGGER.warning("Не удалось прочитать %s: %s", renovigxo_path, exc)
            return

    if existing_lines and existing_lines[0] == latest_entry:
        lines = existing_lines
    else:
        lines = [latest_entry, *existing_lines]

    try:
        renovigxo_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except PermissionError as exc:
        LOGGER.warning("Не удалось записать %s: %s", renovigxo_path, exc)


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Импорт словарных данных в PostgreSQL."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Каталог с ежедневными выгрузками (default: %(default)s)",
    )
    parser.add_argument(
        "--no-truncate",
        action="store_true",
        help="Не очищать таблицы перед импортом.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Включить подробный лог.",
    )
    parser.add_argument(
        "--last-ru-letter",
        type=str,
        help="Последнее готовое слово для Ру→Эо словаря (например, прегрешить). Если не указано, берётся из last-ru-letter.txt.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Iterable[str]] = None) -> None:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if not args.verbose else logging.DEBUG,
        format="%(levelname)s %(message)s",
    )
    run_import(
        args.data_dir,
        truncate=not args.no_truncate,
        last_ru_letter=args.last_ru_letter,
    )


if __name__ == "__main__":
    main()
