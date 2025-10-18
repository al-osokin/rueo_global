from __future__ import annotations

import argparse
from typing import Iterable

from app.database import SessionLocal, init_db
from app.services.article_parser import ArticleParserService
from app.services.translation_review import (
    build_translation_review,
    format_translation_review,
)


def iter_reviews(service: ArticleParserService, lang: str, offset: int, limit: int) -> Iterable[str]:
    for result in service.parse_articles(
        lang,
        offset=offset,
        limit=limit,
        include_raw=True,
    ):
        if not result.raw:
            continue
        review = build_translation_review(result.raw)
        yield format_translation_review(review)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render translation groups for manual review.",
    )
    parser.add_argument("--lang", choices=["eo", "ru"], required=True)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    init_db()
    with SessionLocal() as session:
        service = ArticleParserService(session)
        for block in iter_reviews(service, args.lang, args.offset, args.limit):
            print(block)
            print("-" * 40)


if __name__ == "__main__":
    main()
