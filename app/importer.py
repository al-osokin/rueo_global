from __future__ import annotations

import argparse
import logging
import re
from collections import OrderedDict
from pathlib import Path
from typing import Iterable, List, Sequence

from sqlalchemy import insert, select, text
from sqlalchemy.orm import Session

from app.database import SessionLocal, init_db
from app.models import (
    Article,
    ArticleRu,
    FuzzyEntry,
    SearchEntry,
    SearchEntryRu,
)

LOGGER = logging.getLogger(__name__)

LANG_DIRS = {
    "eo": "VortaroER-daily",
    "ru": "VortaroRE-daily",
}

ARTICLE_PATTERN = re.compile(
    r"(?P<redaktoroj>^\d\.[^\[]*)(?P<vorto>.*?)\r\n\s*\r\n",
    re.MULTILINE | re.DOTALL,
)

HEADER_PATTERN = re.compile(r"^\[(.+?)\]", re.MULTILINE | re.DOTALL)


def run_import(data_dir: Path, truncate: bool = True) -> None:
    init_db()
    with SessionLocal() as session:
        if truncate:
            _truncate_tables(session)

        LOGGER.info("Processing Esperanto data…")
        eo_count = _process_language(session, data_dir, "eo")
        LOGGER.info("Inserted %d Esperanto articles", eo_count)
        LOGGER.info("Processing Russian data…")
        ru_count = _process_language(session, data_dir, "ru")
        LOGGER.info("Inserted %d Russian articles", ru_count)
        session.commit()

        LOGGER.info("Building search indices for Esperanto…")
        eo_words = _create_index_table(session, "eo")
        LOGGER.info("Inserted %d Esperanto search entries", eo_words)
        LOGGER.info("Building search indices for Russian…")
        ru_words = _create_index_table(session, "ru")
        LOGGER.info("Inserted %d Russian search entries", ru_words)
        session.commit()

        LOGGER.info("Updating fuzzy search table…")
        fuzzy_count = _update_neklaraj(session, "sercxo")
        LOGGER.info("Inserted %d fuzzy entries", fuzzy_count)
        session.commit()


def _truncate_tables(session: Session) -> None:
    tables = ["sercxo", "sercxo_ru", "artikoloj", "artikoloj_ru", "neklaraj"]
    for table in tables:
        session.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
    session.commit()


def _process_language(session: Session, data_dir: Path, lang: str) -> int:
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

    total_inserted = 0
    for file_path in files:
        entries = _parse_articles(file_path)
        if not entries:
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
    return total_inserted


def _parse_articles(file_path: Path) -> List[dict[str, str | None]]:
    raw = file_path.read_bytes()
    text_cp = raw.decode("cp1251")
    text_cp += "\r\n\r\n"

    entries: List[dict[str, str | None]] = []
    for match in ARTICLE_PATTERN.finditer(text_cp):
        redaktoroj = match.group("redaktoroj")
        komento = redaktoroj.replace("\r\n", ", ").rstrip(", ")
        priskribo = match.group("vorto").rstrip()
        entries.append({"komento": komento or None, "priskribo": priskribo})
    return entries


def _create_index_table(session: Session, lang: str) -> int:
    article_model = Article if lang == "eo" else ArticleRu
    search_table = SearchEntry.__table__ if lang == "eo" else SearchEntryRu.__table__

    session.execute(
        text(f"TRUNCATE TABLE {search_table.name} RESTART IDENTITY CASCADE")
    )

    word_count = 0
    rows = session.execute(
        select(article_model.art_id, article_model.priskribo).order_by(
            article_model.art_id
        )
    )
    for art_id, priskribo in rows:
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


def _update_neklaraj(session: Session, table_name: str) -> int:
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

    return inserted


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Импорт словарных данных в PostgreSQL."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("References/base_update/src"),
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
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> None:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if not args.verbose else logging.DEBUG,
        format="%(levelname)s %(message)s",
    )
    run_import(args.data_dir, truncate=not args.no_truncate)


if __name__ == "__main__":
    main()
