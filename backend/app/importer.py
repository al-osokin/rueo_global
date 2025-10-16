from __future__ import annotations

import argparse
import logging
import re
from collections import OrderedDict
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

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = (BASE_DIR / "data/src").resolve()

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


def _make_notifier(callback: Optional[ProgressCallback]) -> ProgressCallback:
    def _notify(stage: str, **payload: Any) -> None:
        if callback:
            callback({"stage": stage, **payload})

    return _notify


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

    with SessionLocal() as session:
        if truncate:
            notify("truncating", message="Очистка таблиц перед загрузкой")
            _truncate_tables(session)

        LOGGER.info("Processing Esperanto data…")
        notify("processing_files", lang="eo", current=0, total=0, message="Начало обработки файлов")
        eo_count = _process_language(
            session,
            data_dir,
            "eo",
            progress_callback=lambda update: notify(
                "processing_files", lang="eo", **update
            ),
        )
        LOGGER.info("Inserted %d Esperanto articles", eo_count)
        LOGGER.info("Processing Russian data…")
        notify("processing_files", lang="ru", current=0, total=0, message="Начало обработки файлов")
        ru_count = _process_language(
            session,
            data_dir,
            "ru",
            progress_callback=lambda update: notify(
                "processing_files", lang="ru", **update
            ),
        )
        LOGGER.info("Inserted %d Russian articles", ru_count)
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
        notify("finalizing", message="Формирование служебных файлов", stats=stats)
        _write_status_file(data_dir, stats)
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
    progress_callback: Optional[ProgressCallback] = None,
) -> int:
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
    for index, file_path in enumerate(files, start=1):
        entries = _parse_articles(file_path)
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
        insert_payload = [
            {
                "priskribo": entry["priskribo"],
                "lasta": "j",
                "uz_id": 1,
                "komento": entry["komento"],
            }
            for entry in entries
        ]
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
    return total_inserted


def _parse_articles(file_path: Path) -> List[Dict[str, Optional[str]]]:
    raw = file_path.read_bytes()
    text_cp = raw.decode("cp1251")
    text_cp += "\r\n\r\n"

    entries: List[Dict[str, Optional[str]]] = []
    for match in ARTICLE_PATTERN.finditer(text_cp):
        redaktoroj = match.group("redaktoroj")
        komento = redaktoroj.replace("\r\n", ", ").rstrip(", ")
        priskribo = match.group("vorto").rstrip()
        entries.append({"komento": komento or None, "priskribo": priskribo})
    return entries


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
        for encoding in ("cp1251", "utf-8"):
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
    klarigo_path = tekstoj_dir / "klarigo.textile"
    try:
        klarigo_path.write_text(content, encoding="utf-8")
    except PermissionError as exc:
        LOGGER.warning("Не удалось записать %s: %s", klarigo_path, exc)


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
