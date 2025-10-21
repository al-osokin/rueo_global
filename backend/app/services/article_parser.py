from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, Iterable, Iterator, List, Optional

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models import Article, ArticleParseState, ArticleRu
from app.parsing import get_parsing_pipeline
from app.services.translation_review import (
    apply_candidate_selection,
    build_translation_review,
    collect_translation_phrases,
)


SUPPORTED_LANGS = {"eo", "ru"}


@dataclass(slots=True)
class ArticleParseResult:
    art_id: int
    lang: str
    success: bool
    template: Optional[str]
    headword: Optional[str]
    examples: List[Dict[str, Optional[str]]] = field(default_factory=list)
    example_count: int = 0
    translations: List[str] = field(default_factory=list)
    needs_review: bool = False
    raw: Optional[Dict] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        data = asdict(self)
        return data


class ArticleParserService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.pipeline = get_parsing_pipeline()

    def parse_articles(
        self,
        lang: str,
        *,
        limit: Optional[int] = None,
        offset: int = 0,
        include_raw: bool = False,
    ) -> Iterator[ArticleParseResult]:
        if lang not in SUPPORTED_LANGS:
            raise ValueError(f"Unsupported language: {lang}")

        model = Article if lang == "eo" else ArticleRu
        stmt: Select = select(model.art_id, model.priskribo).order_by(model.art_id)
        if offset:
            stmt = stmt.offset(offset)
        if limit:
            stmt = stmt.limit(limit)

        rows = self.session.execute(stmt)
        for index, (art_id, content) in enumerate(rows, start=offset):
            yield self._build_result(
                lang=lang,
                art_id=art_id,
                content=content,
                index=index,
                include_raw=include_raw,
            )

    def summarize(
        self, results: Iterable[ArticleParseResult]
    ) -> Dict[str, Dict[str, int]]:
        summary: Dict[str, Dict[str, int]] = {
            "templates": {},
            "status": {"success": 0, "failed": 0},
        }
        for result in results:
            if result.success:
                summary["status"]["success"] += 1
            else:
                summary["status"]["failed"] += 1

            template = result.template or "<unknown>"
            summary["templates"][template] = summary["templates"].get(template, 0) + 1
        return summary

    def store_result(
        self,
        result: ArticleParseResult,
        *,
        replace_payload: bool = False,
    ) -> None:
        if not result.success:
            status = result.error or "failed"
        else:
            status = "needs_review" if result.needs_review else "reviewed"
        is_reviewed = status == "reviewed"
        state = self.session.execute(
            select(ArticleParseState).where(
                ArticleParseState.lang == result.lang,
                ArticleParseState.art_id == result.art_id,
            )
        ).scalar_one_or_none()

        if not state:
            state = ArticleParseState(lang=result.lang, art_id=result.art_id)

        state.parsing_status = status[:32]
        state.template = result.template
        state.headword = result.headword
        state.example_count = result.example_count

        if result.examples:
            first = result.examples[0]
            state.first_example_eo = first.get("eo")
            state.first_example_ru = first.get("ru")
        else:
            state.first_example_eo = None
            state.first_example_ru = None

        if result.translations:
            resolved = state.resolved_translations or {}
            if "auto_candidates" not in resolved:
                resolved["auto_candidates"] = result.translations
            state.resolved_translations = resolved

        if replace_payload:
            state.parsed_payload = result.raw
        elif state.parsed_payload is None and result.raw is not None:
            state.parsed_payload = result.raw

        if not is_reviewed:
            state.reviewed_at = None

        self.session.add(state)

    def store_results(
        self,
        results: Iterable[ArticleParseResult],
        *,
        replace_payload: bool = False,
        commit_interval: int = 200,
    ) -> None:
        for index, result in enumerate(results, start=1):
            self.store_result(result, replace_payload=replace_payload)
            if commit_interval and index % commit_interval == 0:
                self.session.flush()
        self.session.commit()

    def _extract_examples(self, parsed: Dict[str, Any]) -> List[Dict[str, Optional[str]]]:
        examples: List[Dict[str, Optional[str]]] = []

        def _render_ru_segments(segments: Optional[List[Dict[str, Any]]]) -> str:
            if not segments:
                return ""
            pieces: List[str] = []
            buffer = ""
            for part in segments:
                text = part.get("text") or ""
                if not text:
                    continue
                kind = part.get("kind")
                if kind == "term":
                    if buffer and not buffer.endswith((' ', '(', '—', '-')):
                        buffer += " "
                    buffer += text
                else:
                    buffer += text
                    if text and text[-1] in {",", ";"} and not buffer.endswith(" "):
                        buffer += " "
            if buffer:
                pieces.append(buffer.strip())
            return " ".join(pieces).strip()

        def _walk(node: Any) -> None:
            if isinstance(node, dict):
                if node.get("type") == "illustration":
                    eo_text = node.get("eo")
                    if not eo_text and node.get("content"):
                        eo_text = " ".join(
                            item.get("text", "")
                            for item in node.get("content", [])
                            if isinstance(item, dict)
                        ).strip() or None
                    ru_text = _render_ru_segments(node.get("ru_segments"))
                    examples.append(
                        {"eo": eo_text, "ru": ru_text or None}
                    )
                for key in ("children", "content"):
                    value = node.get(key)
                    if isinstance(value, list):
                        for child in value:
                            _walk(child)
            elif isinstance(node, list):
                for item in node:
                    _walk(item)

        _walk(parsed.get("body") or [])
        return [example for example in examples if example.get("eo") or example.get("ru")]

    def _build_result(
        self,
        *,
        lang: str,
        art_id: int,
        content: Optional[str],
        index: int,
        include_raw: bool,
    ) -> ArticleParseResult:
        if not content:
            return ArticleParseResult(
                art_id=art_id,
                lang=lang,
                success=False,
                template=None,
                headword=None,
                examples=[],
                example_count=0,
                translations=[],
                raw=None,
                error="empty_content",
            )

        try:
            parsed = self.pipeline.parse_article(content, index=index)
        except Exception as exc:  # pragma: no cover - defensive
            return ArticleParseResult(
                art_id=art_id,
                lang=lang,
                success=False,
                template=None,
                headword=None,
                examples=[],
                example_count=0,
                translations=[],
                raw=None,
                error=f"parse_error: {exc}",
            )

        headword_info = parsed.get("headword") or {}
        headword = headword_info.get("raw_form") or None
        template = (parsed.get("meta") or {}).get("template")
        success = bool(headword)
        examples = self._extract_examples(parsed)
        review = build_translation_review(parsed)

        resolved = self.session.execute(
            select(ArticleParseState.resolved_translations)
            .where(ArticleParseState.lang == lang, ArticleParseState.art_id == art_id)
        ).scalar_one_or_none()
        resolved_groups = {}
        if isinstance(resolved, dict):
            resolved_groups = resolved.get("groups") or {}

        apply_candidate_selection(review, resolved_groups)
        translations = collect_translation_phrases(review)

        needs_review = False
        for index, group in enumerate(review.groups):
            group_id = f"group_{index}"
            stored = resolved_groups.get(group_id)
            accepted = None
            if isinstance(stored, dict):
                accepted = stored.get("accepted")

            if accepted is True:
                continue

            if group.requires_review or (group.auto_generated and accepted is not True):
                needs_review = True
                break

        return ArticleParseResult(
            art_id=art_id,
            lang=lang,
            success=success,
            template=template,
            headword=headword,
            examples=examples,
            example_count=len(examples),
            translations=translations,
            needs_review=needs_review,
            raw=parsed if include_raw else None,
            error=None if success else "missing_headword",
        )

    def parse_article_by_id(
        self,
        lang: str,
        art_id: int,
        *,
        include_raw: bool = False,
    ) -> ArticleParseResult:
        if lang not in SUPPORTED_LANGS:
            raise ValueError(f"Unsupported language: {lang}")

        model = Article if lang == "eo" else ArticleRu
        content = self.session.execute(
            select(model.priskribo).where(model.art_id == art_id)
        ).scalar_one_or_none()
        return self._build_result(
            lang=lang,
            art_id=art_id,
            content=content,
            index=art_id,
            include_raw=include_raw,
        )
