"""Template registry and default template implementations for parser v3."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from .legacy_bridge import legacy_parser
from .normalization import normalize_article

if False:  # pragma: no cover - type checking helper
    from .pipeline import ArticleContext


@dataclass
class TemplateMatchResult:
    """Represents the outcome of attempting to match a template."""

    matched: bool
    confidence: float = 0.0
    reason: Optional[str] = None


class ArticleTemplate:
    """Base class for all article templates."""

    name: str = "base"
    priority: int = 100

    def matches(self, context: "ArticleContext") -> TemplateMatchResult:
        return TemplateMatchResult(matched=False, confidence=0.0)

    def parse(self, context: "ArticleContext") -> Dict[str, Any]:  # noqa: D401
        """Parse article according to the template."""

        raise NotImplementedError


class TemplateRegistry:
    """Registry that selects the best matching template for a context."""

    def __init__(self, templates: Iterable[ArticleTemplate]) -> None:
        self._templates: List[ArticleTemplate] = sorted(
            templates, key=lambda tpl: (tpl.priority, tpl.name)
        )

    def select(self, context: "ArticleContext") -> ArticleTemplate:
        best_template: Optional[ArticleTemplate] = None
        best_score: float = -1.0
        for template in self._templates:
            result = template.matches(context)
            if not result.matched:
                continue
            score = result.confidence
            if score > best_score:
                best_template = template
                best_score = score

        return best_template or self._templates[-1]


class LetterEntryTemplate(ArticleTemplate):
    """Template for alphabet letter entries like `[A, a]`."""

    name = "letter_entry"
    priority = 5

    LETTER_PATTERN = re.compile(r"^\[([^\]]+)\]")

    def matches(self, context: "ArticleContext") -> TemplateMatchResult:
        head_line = context.head_line.strip()
        match = self.LETTER_PATTERN.match(head_line)
        if not match:
            return TemplateMatchResult(False)

        inside = [token.strip() for token in match.group(1).split(',')]
        if len(inside) != 2:
            return TemplateMatchResult(False)

        upper, lower = inside
        if not upper or not lower:
            return TemplateMatchResult(False)

        if upper.lower() != lower.lower():
            return TemplateMatchResult(False)

        if context.body_lines:
            return TemplateMatchResult(False)

        return TemplateMatchResult(True, confidence=0.85)

    def parse(self, context: "ArticleContext") -> Dict[str, Any]:
        headword, remainder = legacy_parser.parse_headword(context.head_line)

        body: List[Dict[str, Any]] = []
        if remainder:
            segments = legacy_parser.parse_rich_text(
                remainder,
                preserve_punctuation=True,
                italic_open=True if '_' in remainder else False,
            )
            segments = legacy_parser.merge_punctuation_with_italic(segments)
            segments = legacy_parser.absorb_parentheses_into_italic(segments)
            merged_segments = legacy_parser.merge_consecutive_text_segments(segments)

            def _attach_inline_punctuation(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
                result: List[Dict[str, Any]] = []
                for item in items:
                    if (
                        item.get("type") == "text"
                        and item.get("style") == "regular"
                    ):
                        text = item.get("text", "")
                        stripped = text.strip()
                        if stripped in {";", ",", ":"} and result:
                            prev = result[-1]
                            if prev.get("type") == "text":
                                suffix = " " if text.endswith(" ") else ""
                                prev['text'] = prev.get('text', '').rstrip() + stripped + suffix
                                continue
                    result.append(item)
                return result

            merged_segments = _attach_inline_punctuation(merged_segments)
            merged_segments = legacy_parser.merge_consecutive_text_segments(merged_segments)

            sentence_ending = ""
            if merged_segments:
                last = merged_segments[-1]
                if last.get("type") == "text":
                    text = last.get("text", "")
                    stripped = text.rstrip()
                    if stripped.endswith('.'):
                        sentence_ending = '.'
                        stripped = stripped[:-1].rstrip()
                        if stripped:
                            last['text'] = stripped
                        else:
                            merged_segments.pop()

            # Remove trailing whitespace-only items
            merged_segments = [seg for seg in merged_segments if seg.get("text", "").strip()]

            body.append({
                "type": "explanation",
                "content": merged_segments,
            })

            if sentence_ending:
                body.append({"type": "sentence_divider", "text": sentence_ending})

        return {
            "headword": headword if headword.get("raw_form") else None,
            "body": body,
        }


class MorphemeNumberedTemplate(ArticleTemplate):
    """Template for morphemes with numbered blocks, e.g. `[-a I]`."""

    name = "morpheme_numbered"
    priority = 8

    NUMBERED_PATTERN = re.compile(r"^\d+\.")

    def matches(self, context: "ArticleContext") -> TemplateMatchResult:
        head_line = context.head_line.strip()
        headword, _ = legacy_parser.parse_headword(head_line)
        lemmas = headword.get("lemmas", []) if headword else []

        if not lemmas:
            return TemplateMatchResult(False)

        is_morpheme = any(
            lemma.get("lemma", "").startswith('-') or lemma.get("lemma", "").endswith('-')
            for lemma in lemmas
        )
        if not is_morpheme:
            return TemplateMatchResult(False)

        if not context.body_lines:
            return TemplateMatchResult(False)

        has_numbered = any(self.NUMBERED_PATTERN.match(line) for line in context.body_lines)
        if not has_numbered:
            return TemplateMatchResult(False)

        return TemplateMatchResult(True, confidence=0.8)

    def parse(self, context: "ArticleContext") -> Dict[str, Any]:
        parsed = legacy_parser.parse_article(context.raw_text)
        return normalize_article(parsed, template_name=self.name, collect_sections=True)


class MorphemeArticleTemplate(ArticleTemplate):
    """Template for morpheme entries such as prefixes/suffixes."""

    name = "morpheme"
    priority = 10

    def matches(self, context: "ArticleContext") -> TemplateMatchResult:
        head_raw = context.head_line.strip()
        if not head_raw.startswith('[') or ']' not in head_raw:
            return TemplateMatchResult(False)

        headword, _ = legacy_parser.parse_headword(head_raw)
        lemmas = headword.get('lemmas', []) if headword else []
        is_morpheme = any(
            lemma.get('lemma', '').startswith('-') or lemma.get('lemma', '').endswith('-')
            for lemma in lemmas
        )
        if is_morpheme:
            return TemplateMatchResult(True, confidence=0.55)
        return TemplateMatchResult(False)

    def parse(self, context: "ArticleContext") -> Dict[str, Any]:
        parsed = legacy_parser.parse_article(context.raw_text)
        return normalize_article(parsed, template_name=self.name, collect_sections=True)


class LexemeNumberedTemplate(ArticleTemplate):
    """Template for lexeme entries with numbered translations, e.g. `[abak/o]`."""

    name = "lexeme_numbered"
    priority = 12

    NUMBERED_PATTERN = re.compile(r"^\d+\.")

    def matches(self, context: "ArticleContext") -> TemplateMatchResult:
        head_line = context.head_line.strip()
        headword, _ = legacy_parser.parse_headword(head_line)
        lemmas = headword.get("lemmas", []) if headword else []
        if not lemmas:
            return TemplateMatchResult(False)

        is_morpheme = any(
            lemma.get("lemma", "").startswith('-') or lemma.get("lemma", "").endswith('-')
            for lemma in lemmas
        )
        if is_morpheme:
            return TemplateMatchResult(False)

        if not context.body_lines:
            return TemplateMatchResult(False)

        has_numbered = any(self.NUMBERED_PATTERN.match(line) for line in context.body_lines)
        if not has_numbered:
            return TemplateMatchResult(False)

        return TemplateMatchResult(True, confidence=0.7)

    def parse(self, context: "ArticleContext") -> Dict[str, Any]:
        parsed = legacy_parser.parse_article(context.raw_text)
        return normalize_article(parsed, template_name=self.name, collect_sections=True)


class DefaultArticleTemplate(ArticleTemplate):
    """Fallback template that delegates to the legacy parser."""

    name = "default"
    priority = 100

    def matches(self, context: "ArticleContext") -> TemplateMatchResult:
        return TemplateMatchResult(True, confidence=0.1)

    def parse(self, context: "ArticleContext") -> Dict[str, Any]:
        parsed = legacy_parser.parse_article(context.raw_text)
        return normalize_article(parsed, template_name=self.name)


DEFAULT_TEMPLATES: List[ArticleTemplate] = [
    LetterEntryTemplate(),
    MorphemeNumberedTemplate(),
    MorphemeArticleTemplate(),
    LexemeNumberedTemplate(),
    DefaultArticleTemplate(),
]
