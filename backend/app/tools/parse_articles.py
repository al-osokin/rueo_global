from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

from app.database import SessionLocal, init_db
from app.services.article_parser import ArticleParserService


def _export_results(path: Path, payload: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse dictionary articles using the v3 parsing pipeline.",
    )
    parser.add_argument("--lang", choices=["eo", "ru"], required=True, help="Article language")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of articles to parse")
    parser.add_argument("--offset", type=int, default=0, help="Offset when selecting articles")
    parser.add_argument(
        "--include-raw",
        action="store_true",
        help="Include raw parser payload in the output",
    )
    parser.add_argument(
        "--show",
        type=int,
        default=3,
        help="Display first N parsed articles in the console (default: 3)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path to save full results as JSON",
    )
    parser.add_argument(
        "--save-state",
        action="store_true",
        help="Persist parsing summaries into article_parse_state",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=200,
        help="How often to flush when saving state (default: 200)",
    )

    args = parser.parse_args()

    init_db()
    summary = {"status": {"success": 0, "failed": 0}, "templates": {}}
    samples: List = []
    payload: List[dict] = []

    with SessionLocal() as session:
        service = ArticleParserService(session)
        iterator = service.parse_articles(
            args.lang,
            limit=args.limit,
            offset=args.offset,
            include_raw=args.include_raw,
        )
        for index, result in enumerate(iterator, start=1):
            if result.success:
                summary["status"]["success"] += 1
            else:
                summary["status"]["failed"] += 1

            template = result.template or "<unknown>"
            summary["templates"][template] = summary["templates"].get(template, 0) + 1

            if args.show and len(samples) < args.show:
                samples.append(result)

            if args.output:
                payload.append(result.to_dict())

            if args.save_state:
                service.store_result(result, replace_payload=args.include_raw)
                if args.batch_size and index % args.batch_size == 0:
                    session.flush()

        if args.save_state:
            session.commit()

    total = summary["status"]["success"] + summary["status"]["failed"]
    print(f"Parsed articles: {total}")
    print("Status summary:", summary["status"])
    top_templates = sorted(
        summary["templates"].items(),
        key=lambda item: item[1],
        reverse=True,
    )
    print("Template usage (top 10):")
    for template, count in top_templates[:10]:
        print(f"  {template}: {count}")

    show_count = max(0, args.show or 0)
    if show_count:
        print("\nSample results:")
        for result in samples[:show_count]:
            example = result.examples[0] if result.examples else None
            if example:
                example_text = f"{example.get('eo') or ''} → {example.get('ru') or ''}".strip()
            else:
                example_text = "—"
            print(
                f"- art_id={result.art_id} lang={result.lang} success={result.success} "
                f"template={result.template} headword={result.headword}"
            )
            print(f"    примеры: {example_text}")

    if args.output and payload:
        _export_results(args.output, payload)
        print(f"\nSaved detailed results to {args.output}")

    if args.save_state:
        print("State saved to article_parse_state")


if __name__ == "__main__":
    main()
