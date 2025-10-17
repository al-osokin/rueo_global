from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from sqlalchemy import delete, select

from app.database import SessionLocal, init_db
from app.models import ArticleFileState, ArticleState
from app.services.article_tracking import extract_canonical_key


def parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def load_state_file(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def import_states(state_dir: Path, lang: str, reset: bool = False) -> None:
    init_db()
    state_dir = state_dir.resolve()
    files = sorted(state_dir.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"No JSON files found in {state_dir}")

    with SessionLocal() as session:
        if reset:
            session.execute(
                delete(ArticleState).where(
                    ArticleState.file_state_id.in_(
                        select(ArticleFileState.id).where(ArticleFileState.lang == lang)
                    )
                )
            )
            session.execute(delete(ArticleFileState).where(ArticleFileState.lang == lang))
            session.commit()

        for json_file in files:
            data = load_state_file(json_file)
            articles = data.get("articles", [])
            if not articles:
                continue

            first_article = articles[0]
            file_path = first_article.get("file_path")
            if not file_path:
                continue

            stmt = (
                select(ArticleFileState)
                .where(ArticleFileState.lang == lang)
                .where(ArticleFileState.file_path == file_path)
                .limit(1)
            )
            file_state = session.execute(stmt).scalar_one_or_none()
            if file_state is None:
                file_state = ArticleFileState(
                    lang=lang,
                    file_path=file_path,
                )
                session.add(file_state)
                session.flush()

            file_state.last_run_at = parse_datetime(data.get("last_script_run_date"))
            file_state.last_modified_at = parse_datetime(data.get("file_modified_time"))

            for index, article in enumerate(articles):
                canonical_key = article.get("canonical_key") or extract_canonical_key(
                    article.get("key_info", "")
                )
                if not canonical_key:
                    canonical_key = f"__article_{index}"
                occurrence = article.get("canonical_occurrence") or 0
                checksum = article.get("checksum") or ""
                last_header = article.get("last_edited_line")

                stmt_state = (
                    select(ArticleState)
                        .where(ArticleState.file_state_id == file_state.id)
                        .where(ArticleState.canonical_key == canonical_key)
                        .where(ArticleState.canonical_occurrence == occurrence)
                        .limit(1)
                )
                state = session.execute(stmt_state).scalar_one_or_none()
                if state is None:
                    state = ArticleState(
                        file_state=file_state,
                        article_index=index,
                        canonical_key=canonical_key,
                        canonical_occurrence=occurrence,
                        checksum=checksum,
                        last_header_line=last_header,
                        last_seen_at=file_state.last_run_at,
                    )
                    session.add(state)
                else:
                    state.article_index = index
                    state.canonical_key = canonical_key
                    state.canonical_occurrence = occurrence
                    state.checksum = checksum
                    state.last_header_line = last_header
                    state.last_seen_at = file_state.last_run_at

        session.commit()


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Импорт JSON-состояний статей в таблицы Postgres."
    )
    parser.add_argument(
        "--state-dir",
        type=Path,
        required=True,
        help="Каталог с JSON-файлами состояний (dictionary_states).",
    )
    parser.add_argument(
        "--lang",
        type=str,
        choices=["ru", "eo"],
        default="ru",
        help="Язык словаря, для которого импортируются состояния.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Удалить существующие записи для указанного языка перед импортом.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Iterable[str]] = None) -> None:
    args = parse_args(argv)
    import_states(args.state_dir, args.lang, reset=args.reset)


if __name__ == "__main__":
    main()
