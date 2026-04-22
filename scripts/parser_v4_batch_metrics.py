#!/usr/bin/env python3
"""Quick batch metrics for parser_v4 review routing."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Article
from app.parsing.parser_v4.pipeline import ParsingPipelineV4


@dataclass
class Counters:
    clean: int = 0
    line_merge_risk: int = 0
    many_to_many: int = 0
    errors: int = 0

    def as_dict(self):
        return {
            "clean": self.clean,
            "line-merge-risk": self.line_merge_risk,
            "many-to-many": self.many_to_many,
            "errors": self.errors,
        }


def classify_blocks(blocks: list[dict]) -> str:
    has_line_merge_risk = False
    has_many = False

    for b in blocks:
        raw = (b.get("raw") or "").lower()

        if "_или_" in raw or "(_или_" in raw or "(или" in raw:
            has_many = True

        if ";" in raw and "," in raw:
            has_line_merge_risk = True
        if "(" in raw and ")" in raw and (";" in raw or "," in raw):
            has_line_merge_risk = True
        if raw.count(";") >= 2 or raw.count(",") >= 3:
            has_line_merge_risk = True

    if has_many:
        return "many-to-many"
    if has_line_merge_risk:
        return "line-merge-risk"
    return "clean"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=300)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--samples", type=int, default=15)
    args = ap.parse_args()

    pipeline = ParsingPipelineV4()
    c = Counters()
    sample_non_clean: list[dict] = []

    with SessionLocal() as session:
        rows = session.execute(
            select(Article.art_id, Article.priskribo)
            .order_by(Article.art_id)
            .offset(args.offset)
            .limit(args.limit)
        ).all()

        for art_id, text in rows:
            try:
                parsed = pipeline.parse_article(text or "", index=art_id)
                forms = parsed.get("meta", {}).get("v4_ast", {}).get("forms", [])
                blocks: list[dict] = []
                for f in forms:
                    blocks.extend(f.get("blocks", []))

                cls = classify_blocks(blocks)
                if cls == "clean":
                    c.clean += 1
                elif cls == "line-merge-risk":
                    c.line_merge_risk += 1
                else:
                    c.many_to_many += 1

                if cls != "clean" and len(sample_non_clean) < args.samples:
                    sample_non_clean.append(
                        {"art_id": art_id, "headword": parsed.get("headword", {}).get("raw_form"), "class": cls}
                    )
            except Exception:
                c.errors += 1

    out = {
        "window": {"offset": args.offset, "limit": args.limit},
        "counts": c.as_dict(),
        "sample_non_clean": sample_non_clean,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
