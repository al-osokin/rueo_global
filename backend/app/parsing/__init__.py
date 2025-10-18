from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

from .parser_v3.pipeline import ParsingPipeline as _ParsingPipeline
from .parser_v3.pipeline import ArticleContext
from .parser_v3.legacy_bridge import legacy_parser


PARSER_ROOT = Path(__file__).resolve().parent

_RESOURCE_MAPPING = {
    "SHORTENINGS_FILE": "shortenings.txt",
    "ABBREVIATIONS_FILE": "w.txt",
    "INPUT_FILENAME": "test_articles.txt",
    "OUTPUT_FILENAME": "output.json",
    "LOG_FILENAME": "parser_log.txt",
}

for attr_name, file_name in _RESOURCE_MAPPING.items():
    if hasattr(legacy_parser, attr_name):
        setattr(legacy_parser, attr_name, str(PARSER_ROOT / file_name))

if hasattr(legacy_parser, "KNOWN_SHORTENINGS") and not getattr(
    legacy_parser, "KNOWN_SHORTENINGS", None
):
    try:
        legacy_parser.KNOWN_SHORTENINGS = legacy_parser.load_shortenings()
    except Exception:
        pass


@lru_cache(maxsize=1)
def get_parsing_pipeline() -> _ParsingPipeline:
    return _ParsingPipeline()


def parse_article(text: str, *, index: int = 0) -> Dict[str, Any]:
    pipeline = get_parsing_pipeline()
    return pipeline.parse_article(text, index=index)


__all__ = ["ArticleContext", "get_parsing_pipeline", "parse_article"]
