"""Core parsing pipeline for parser v3."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from .legacy_bridge import legacy_parser
from .templates import DEFAULT_TEMPLATES, ArticleTemplate, TemplateRegistry
from . import text_parser  # Новый чистый парсер


@dataclass
class ArticleContext:
    """Accumulated metadata used to choose a template."""

    raw_text: str
    preprocessed_text: str
    head_line: str
    body_lines: List[str]
    index: int


class ParsingPipeline:
    """High-level orchestrator that applies templates to articles."""

    def __init__(self, templates: Optional[Iterable[ArticleTemplate]] = None) -> None:
        self.registry = TemplateRegistry(list(templates or DEFAULT_TEMPLATES))

    def parse_content(self, content: str) -> List[Dict]:
        articles = split_articles_by_empty_lines(content)
        results: List[Dict] = []
        for idx, article in enumerate(articles):
            if not article.strip():
                continue
            parsed = self.parse_article(article, index=idx)
            if parsed.get('headword'):
                results.append(parsed)
        return results

    def parse_article(self, article_text: str, *, index: int = 0) -> Dict:
        # Используем новый text_parser
        preprocessed = text_parser.preprocess_text(article_text)
        filtered_lines = _filter_relevant_lines(preprocessed)
        if not filtered_lines:
            return {'headword': None, 'body': []}

        context = ArticleContext(
            raw_text=article_text,
            preprocessed_text=preprocessed,
            head_line=filtered_lines[0],
            body_lines=filtered_lines[1:],
            index=index,
        )
        template = self.registry.select(context)
        result = template.parse(context)
        extra_nodes = result.pop('extra_nodes', None)
        if extra_nodes:
            result.setdefault('meta', {})['post_template_extra'] = extra_nodes
        return result


def parse_content(content: str) -> List[Dict]:
    """Convenience helper that parses the provided raw content."""

    pipeline = ParsingPipeline()
    return pipeline.parse_content(content)


def parse_file(path: str, encoding: str = 'utf-8') -> List[Dict]:
    with open(path, 'r', encoding=encoding) as fh:
        return parse_content(fh.read())


def split_articles_by_empty_lines(content: str) -> List[str]:
    """Split raw dictionary text into individual articles."""

    lines = content.split('\n')
    articles: List[str] = []
    current: List[str] = []
    skip_initial_metadata = True

    for line in lines:
        stripped = line.strip()

        if skip_initial_metadata:
            if not stripped or stripped.startswith('$'):
                continue
            skip_initial_metadata = False

        if not stripped:
            if current:
                articles.append('\n'.join(current))
                current = []
            continue

        current.append(line)

    if current:
        articles.append('\n'.join(current))

    return articles


def _filter_relevant_lines(preprocessed_text: str) -> List[str]:
    lines = preprocessed_text.strip().split('\n')
    filtered: List[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r'^\d{4}-\d{2}-\d{2}', stripped):
            continue
        if re.match(r'^\w+ \w+$', stripped):
            continue
        filtered.append(stripped)
    return filtered
