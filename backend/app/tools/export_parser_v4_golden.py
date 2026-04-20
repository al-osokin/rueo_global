"""Export golden parser-v4 fixtures from DB for selected art_ids."""

from __future__ import annotations

import json
import os
from pathlib import Path

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Article
from app.parsing.parser_v4 import ParsingPipelineV4

GOLDEN_IDS = [1, 2, 3, 6, 56, 77]
OUT = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "parser_v4_golden.json"


def main() -> None:
    pipeline = ParsingPipelineV4()
    rows = []
    with SessionLocal() as session:
        for art_id in GOLDEN_IDS:
            text = session.execute(select(Article.priskribo).where(Article.art_id == art_id)).scalar_one_or_none()
            if not text:
                continue
            parsed = pipeline.parse_article(text, index=art_id)
            rows.append({
                "art_id": art_id,
                "headword": (parsed.get("headword") or {}).get("raw_form"),
                "v4_ast": (parsed.get("meta") or {}).get("v4_ast"),
            })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"written: {OUT}")


if __name__ == "__main__":
    if os.getenv("DATABASE_URL") is None:
        print("warning: DATABASE_URL not set; using app default")
    main()
