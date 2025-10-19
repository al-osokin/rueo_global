from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import select, text, func
from sqlalchemy.orm import Session

from app.models import Article, ArticleParseNote, ArticleParseState, ArticleRu
from app.services.article_parser import ArticleParserService
from app.services.translation_review import build_translation_review


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
        resolved_groups = (
            resolved.get("groups") if isinstance(resolved, dict) else {}
        )

        groups_payload: List[Dict[str, Any]] = []
        review_notes: List[str] = []
        if review_data:
            review_notes = review_data.notes
            for index, group in enumerate(review_data.groups):
                group_id = f"group_{index}"
                stored = (
                    resolved_groups.get(group_id)
                    if isinstance(resolved_groups, dict)
                    else None
                )
                accepted = None
                if isinstance(stored, dict):
                    accepted = stored.get("accepted")
                if accepted is None:
                    accepted = not group.requires_review
                groups_payload.append(
                    {
                        "group_id": group_id,
                        "items": group.items,
                        "base_items": group.base_items,
                        "label": group.label,
                        "requires_review": group.requires_review,
                        "auto_generated": group.auto_generated,
                        "section": group.section,
                        "accepted": bool(accepted),
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
        self.session.commit()

        next_id = self._find_next_art_id(lang, art_id)
        return {"next_art_id": next_id}

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
