from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import select, text, func
from sqlalchemy.orm import Session

from app.models import Article, ArticleParseNote, ArticleParseState, ArticleRu
from app.services.article_parser import ArticleParserService, ArticleParseResult
from app.services.translation_review import (
    apply_candidate_selection,
    build_translation_review,
)


class ArticleReviewService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.parser = ArticleParserService(session)
        self._ensure_schema()

    def search_articles(
        self,
        lang: str,
        query: Optional[str],
        limit: int = 20,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        stmt = select(
            ArticleParseState.art_id,
            ArticleParseState.headword,
            ArticleParseState.parsing_status,
        ).where(ArticleParseState.lang == lang)

        if query:
            normalized_query = _normalize_string(query)
            if not normalized_query:
                return []
            pattern = f"%{normalized_query}%"
            normalized_headword = _normalize_headword_expr(ArticleParseState.headword)
            stmt = stmt.where(ArticleParseState.headword.is_not(None))
            stmt = stmt.where(normalized_headword.ilike(pattern))
            stmt = stmt.order_by(ArticleParseState.headword)
        elif status:
            stmt = stmt.where(ArticleParseState.parsing_status == status)
            stmt = stmt.order_by(ArticleParseState.art_id)
        else:
            return []

        stmt = stmt.limit(limit)
        rows = self.session.execute(stmt).all()
        return [
            {
                "art_id": art_id,
                "headword": headword,
                "parsing_status": status,
            }
            for art_id, headword, status in rows
        ]

    def get_statistics(self, lang: str) -> Dict[str, int]:
        total = self.session.execute(
            select(func.count())
            .select_from(ArticleParseState)
            .where(ArticleParseState.lang == lang)
        ).scalar_one()

        needs_review = self.session.execute(
            select(func.count())
            .select_from(ArticleParseState)
            .where(
                ArticleParseState.lang == lang,
                ArticleParseState.parsing_status == "needs_review",
            )
        ).scalar_one()

        reviewed = self.session.execute(
            select(func.count())
            .select_from(ArticleParseState)
            .where(
                ArticleParseState.lang == lang,
                ArticleParseState.reviewed_at.is_not(None),
            )
        ).scalar_one()

        return {
            "total": int(total or 0),
            "needs_review": int(needs_review or 0),
            "reviewed": int(reviewed or 0),
        }

    def get_queue_item(
        self,
        lang: str,
        *,
        status: str = "needs_review",
        after: Optional[int] = None,
        random: bool = False,
    ) -> Optional[Dict[str, Any]]:
        stmt = select(
            ArticleParseState.art_id,
            ArticleParseState.headword,
            ArticleParseState.parsing_status,
        ).where(ArticleParseState.lang == lang)

        stmt = stmt.where(ArticleParseState.parsing_status == status)

        if random:
            stmt = stmt.order_by(func.random()).limit(1)
            row = self.session.execute(stmt).first()
            if not row:
                return None
            art_id, headword, parsing_status = row
            return {
                "art_id": art_id,
                "headword": headword,
                "parsing_status": parsing_status,
            }

        if after is not None:
            stmt_after = stmt.where(ArticleParseState.art_id > after).order_by(ArticleParseState.art_id).limit(1)
            row_after = self.session.execute(stmt_after).first()
            if row_after:
                art_id, headword, parsing_status = row_after
                return {
                    "art_id": art_id,
                    "headword": headword,
                    "parsing_status": parsing_status,
                }

        stmt = stmt.order_by(ArticleParseState.art_id).limit(1)
        row = self.session.execute(stmt).first()
        if not row:
            return None
        art_id, headword, parsing_status = row
        return {
            "art_id": art_id,
            "headword": headword,
            "parsing_status": parsing_status,
        }

    def load_article(self, lang: str, art_id: int) -> Dict[str, Any]:
        result = self.parser.parse_article_by_id(lang, art_id, include_raw=True)
        state = self._ensure_state(lang, art_id)
        notes = self._fetch_notes(lang, art_id)
        review_data = build_translation_review(result.raw) if result.raw else None

        resolved = state.resolved_translations or {}
        resolved_groups = resolved.get("groups") if isinstance(resolved, dict) else {}
        if not isinstance(resolved_groups, dict):
            resolved_groups = {}

        groups_payload: List[Dict[str, Any]] = []
        review_notes: List[str] = []
        if review_data:
            apply_candidate_selection(review_data, resolved_groups)
            review_notes = review_data.notes
            for index, group in enumerate(review_data.groups):
                group_id = f"group_{index}"
                stored = resolved_groups.get(group_id)
                accepted = None
                if isinstance(stored, dict):
                    accepted = stored.get("accepted")
                if accepted is None:
                    accepted = not group.requires_review
                groups_payload.append(
                    {
                        "group_id": group_id,
                        "items": list(group.items),
                        "base_items": list(group.base_items),
                        "label": group.label,
                        "requires_review": group.requires_review,
                        "auto_generated": group.auto_generated,
                        "section": group.section,
                        "accepted": bool(accepted),
                        "candidates": [
                            {
                                "id": candidate.candidate_id,
                                "title": candidate.title,
                                "items": list(candidate.items),
                            }
                            for candidate in group.candidates
                        ],
                        "selected_candidate": group.selected_candidate,
                    }
                )

        auto_candidates = (
            resolved.get("auto_candidates")
            if isinstance(resolved, dict)
            else None
        )
        if auto_candidates is None:
            auto_candidates = result.translations
            if isinstance(resolved, dict):
                resolved["auto_candidates"] = auto_candidates

        return {
            "art_id": art_id,
            "lang": lang,
            "headword": result.headword,
            "template": result.template,
            "success": result.success,
            "parsing_status": state.parsing_status,
            "groups": groups_payload,
            "auto_candidates": auto_candidates,
            "resolved_translations": resolved,
            "notes": notes,
            "review_notes": review_notes,
        }

    def save_review(
        self,
        lang: str,
        art_id: int,
        *,
        resolved_translations: Optional[Dict[str, Any]] = None,
        comment: Optional[str] = None,
        author: Optional[str] = None,
    ) -> Dict[str, Any]:
        state = self._ensure_state(lang, art_id)
        if resolved_translations is not None:
            state.resolved_translations = resolved_translations
        if comment:
            note = ArticleParseNote(lang=lang, art_id=art_id, author=author, body=comment)
            self.session.add(note)
            state.has_notes = True
        self.session.commit()

        updated_result = self.parser.parse_article_by_id(lang, art_id, include_raw=True)
        state.parsing_status = "needs_review" if updated_result.needs_review else "reviewed"
        if state.parsing_status == "reviewed":
            state.reviewed_at = datetime.utcnow()
        else:
            state.reviewed_at = None
        self.session.commit()

        next_id = self._find_next_art_id(lang, art_id)
        return {"next_art_id": next_id}

    def reset_article(self, lang: str, art_id: int) -> Dict[str, Any]:
        state = self._ensure_state(lang, art_id)
        state.resolved_translations = None
        state.has_notes = False
        state.reviewed_at = None
        self.session.commit()

        result = self.parser.parse_article_by_id(lang, art_id, include_raw=True)
        self.parser.store_result(result, replace_payload=True)
        self.session.commit()
        return self.load_article(lang, art_id)

    def _collect_reparse_ids(
        self,
        lang: str,
        *,
        art_ids: Optional[Sequence[int]] = None,
        include_pending: bool = False,
    ) -> List[int]:
        if art_ids:
            return sorted(
                {
                    int(item)
                    for item in art_ids
                    if isinstance(item, int) or (isinstance(item, str) and item.isdigit())
                }
            )

        status_filter = ["needs_review"]
        if include_pending:
            status_filter.append("pending")
        rows = self.session.execute(
            select(ArticleParseState.art_id)
            .where(ArticleParseState.lang == lang)
            .where(ArticleParseState.parsing_status.in_(status_filter))
        ).scalars()
        return sorted(set(rows))

    def reparse_articles(
        self,
        lang: str,
        *,
        art_ids: Optional[Sequence[int]] = None,
        include_pending: bool = False,
    ) -> Dict[str, Any]:
        ids = self._collect_reparse_ids(
            lang,
            art_ids=art_ids,
            include_pending=include_pending,
        )

        summary = {"requested": len(ids), "processed": 0, "failed": [], "skipped": 0}

        if not ids:
            summary["requested"] = 0 if art_ids else 0
            return {"summary": summary, "updated": 0, "failed": []}

        updated = 0
        failed: List[int] = []
        pipeline_errors: List[Dict[str, Any]] = []

        for art_id in ids:
            try:
                result = self.parser.parse_article_by_id(lang, art_id, include_raw=True)
                self.parser.store_result(result, replace_payload=True)
                if result.success:
                    updated += 1
                else:
                    failed.append(art_id)
                    if result.error:
                        pipeline_errors.append({"art_id": art_id, "error": result.error})
            except Exception as exc:  # pragma: no cover - defensive
                failed.append(art_id)
                pipeline_errors.append({"art_id": art_id, "error": str(exc)})

        self.session.commit()
        summary["processed"] = updated + len(failed)
        summary["failed"] = failed
        return {"summary": summary, "updated": updated, "failed_details": pipeline_errors}

    def reparse_article(
        self,
        lang: str,
        art_id: int,
    ) -> Tuple[Dict[str, Any], ArticleParseResult]:
        self._ensure_state(lang, art_id)
        result = self.parser.parse_article_by_id(lang, art_id, include_raw=True)
        self.parser.store_result(result, replace_payload=True)
        self.session.commit()
        payload = self.load_article(lang, art_id)
        return payload, result

    def _ensure_state(self, lang: str, art_id: int) -> ArticleParseState:
        state = self.session.execute(
            select(ArticleParseState).where(
                ArticleParseState.lang == lang,
                ArticleParseState.art_id == art_id,
            )
        ).scalar_one_or_none()
        if state is None:
            state = ArticleParseState(
                lang=lang,
                art_id=art_id,
                parsing_status="pending",
            )
            self.session.add(state)
            self.session.flush()
        return state

    def _fetch_notes(self, lang: str, art_id: int) -> List[Dict[str, Any]]:
        stmt = (
            select(
                ArticleParseNote.id,
                ArticleParseNote.author,
                ArticleParseNote.body,
                ArticleParseNote.created_at,
            )
            .where(
                ArticleParseNote.lang == lang,
                ArticleParseNote.art_id == art_id,
            )
            .order_by(ArticleParseNote.created_at.asc())
        )
        rows = self.session.execute(stmt).all()
        return [
            {
                "id": note_id,
                "author": author,
                "body": body,
                "created_at": created_at.isoformat() if created_at else None,
            }
            for note_id, author, body, created_at in rows
        ]

    def _find_next_art_id(self, lang: str, art_id: int) -> Optional[int]:
        model = Article if lang == "eo" else ArticleRu
        next_id = self.session.execute(
            select(model.art_id)
            .where(model.art_id > art_id)
            .order_by(model.art_id)
            .limit(1)
        ).scalar_one_or_none()
        if next_id is not None:
            return next_id
        return (
            self.session.execute(
                select(model.art_id).order_by(model.art_id).limit(1)
            ).scalar_one_or_none()
        )

    def _ensure_schema(self) -> None:
        self.session.execute(
            text(
                "ALTER TABLE article_parse_state "
                "ADD COLUMN IF NOT EXISTS resolved_translations JSONB"
            )
        )
        self.session.execute(
            text(
                "ALTER TABLE article_parse_state "
                "ADD COLUMN IF NOT EXISTS has_notes BOOLEAN DEFAULT FALSE NOT NULL"
            )
        )
        self.session.execute(
            text(
                "ALTER TABLE article_parse_state "
                "ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMP WITHOUT TIME ZONE"
            )
        )
        self.session.execute(
            text(
                "CREATE TABLE IF NOT EXISTS article_parse_notes ("
                "id SERIAL PRIMARY KEY,"
                "lang VARCHAR(4) NOT NULL,"
                "art_id INTEGER NOT NULL,"
                "author VARCHAR(128),"
                "body TEXT NOT NULL,"
                "created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()"
                ")"
            )
        )
        self.session.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_article_parse_notes_lang_art "
                "ON article_parse_notes (lang, art_id)"
            )
        )
        self.session.commit()


def _normalize_string(value: str) -> str:
    return (
        value.replace("/", "")
        .replace("[", "")
        .replace("]", "")
        .replace("`", "")
        .replace("'", "")
        .replace(" ", "")
        .strip()
        .lower()
    )


def _normalize_headword_expr(column):  # type: ignore[no-untyped-def]
    expr = column
    for ch in ["[", "]", "/", "`", "'", " "]:
        expr = func.replace(expr, ch, "")
    return func.lower(expr)
