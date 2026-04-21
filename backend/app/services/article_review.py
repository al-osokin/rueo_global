from __future__ import annotations

from datetime import datetime
import json
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

import httpx
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
        before: Optional[int] = None,
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

        if before is not None:
            stmt_before = stmt.where(ArticleParseState.art_id < before).order_by(ArticleParseState.art_id.desc()).limit(1)
            row_before = self.session.execute(stmt_before).first()
            if row_before:
                art_id, headword, parsing_status = row_before
                return {
                    "art_id": art_id,
                    "headword": headword,
                    "parsing_status": parsing_status,
                }
            return None

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
        # Используем уже созданный review из result, чтобы не вызывать build_translation_review дважды
        review_data = result.review if hasattr(result, 'review') and result.review else (
            build_translation_review(result.raw) if result.raw else None
        )

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
                manual_override = None
                if isinstance(stored, dict):
                    accepted = stored.get("accepted")
                    manual_override = stored.get("manual_override")
                if accepted is None:
                    accepted = not group.requires_review
                
                candidates_list = [
                    {
                        "id": candidate.candidate_id,
                        "title": candidate.title,
                        "items": list(candidate.items),
                    }
                    for candidate in group.candidates
                ]
                
                if group.requires_review:
                    manual_items = []
                    if manual_override and isinstance(manual_override, str):
                        manual_items = [phrase.strip() for phrase in manual_override.split("|") if phrase.strip()]
                    candidates_list.append({
                        "id": "manual",
                        "title": "Свой вариант",
                        "items": manual_items,
                    })
                
                selected = group.selected_candidate
                if manual_override and isinstance(manual_override, str) and manual_override.strip():
                    selected = "manual"
                
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
                        "candidates": candidates_list,
                        "selected_candidate": selected,
                        "manual_override": manual_override or "",
                        "eo_source": group.eo_source,
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
            "parse_error": result.error,
            "review_diagnostic": result.review_diagnostic,
            "parsing_status": state.parsing_status,
            "groups": groups_payload,
            "auto_candidates": auto_candidates,
            "resolved_translations": resolved,
            "notes": notes,
            "review_notes": review_notes,
        }

    def load_article_ast(self, lang: str, art_id: int) -> Dict[str, Any]:
        result = self.parser.parse_article_by_id(lang, art_id, include_raw=True)
        raw = result.raw if isinstance(result.raw, dict) else {}
        meta = raw.get("meta") if isinstance(raw, dict) else {}
        v4_ast = meta.get("v4_ast") if isinstance(meta, dict) else None
        if not isinstance(v4_ast, dict):
            v4_ast = None

        return {
            "headword": result.headword,
            "lang": lang,
            "art_id": art_id,
            "parse_error": result.error,
            "review_diagnostic": result.review_diagnostic,
            "v4_ast": v4_ast,
        }

    def resolve_block_draft(
        self,
        lang: str,
        art_id: int,
        form_id: str,
        block_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self._ensure_state(lang, art_id)
        safe_context = context or {}

        lmstudio_base_url = os.getenv("LMSTUDIO_BASE_URL", "").strip().rstrip("/")
        lmstudio_model = os.getenv("LMSTUDIO_MODEL", "").strip() or os.getenv("GEMMA_MODEL", "").strip() or "gemma-4"
        timeout_seconds = float(os.getenv("LMSTUDIO_TIMEOUT_SECONDS", "45"))

        lmstudio_error: Optional[str] = None
        if lmstudio_base_url:
            try:
                return self._resolve_block_with_lmstudio(
                    base_url=lmstudio_base_url,
                    model=lmstudio_model,
                    timeout_seconds=timeout_seconds,
                    lang=lang,
                    art_id=art_id,
                    form_id=form_id,
                    block_id=block_id,
                    context=safe_context,
                )
            except Exception as exc:
                # Fallback ниже сохраняет обратную совместимость экрана review-v4,
                # но отдаём причину для дебага в UI.
                lmstudio_error = f"{type(exc).__name__}: {exc}"

        items = safe_context.get("items") if isinstance(safe_context, dict) else None
        candidates: List[str] = []
        if isinstance(items, list):
            candidates = [str(item).strip() for item in items if str(item).strip()]

        if not candidates:
            label = safe_context.get("label") if isinstance(safe_context, dict) else None
            base = str(label).strip() if label else block_id
            candidates = [f"{base}", f"{base} (уточнить)"]

        candidates = list(dict.fromkeys(candidates))[:5]

        rationale = "Stub provider: черновые варианты сформированы локально без вызова модели."
        provider = "gemma-assist-stub"
        if lmstudio_error:
            provider = "lmstudio-fallback"
            rationale = f"LM Studio fallback: {lmstudio_error}"

        return {
            "provider": provider,
            "candidates": candidates,
            "confidence": 0.42,
            "rationale_short": rationale,
        }

    def _resolve_block_with_lmstudio(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float,
        lang: str,
        art_id: int,
        form_id: str,
        block_id: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        source_items = context.get("items") if isinstance(context, dict) else None
        source_text = " | ".join(str(x) for x in source_items if str(x).strip()) if isinstance(source_items, list) else ""
        label = str(context.get("label", "")).strip() if isinstance(context, dict) else ""

        prompt = (
            "Ты помогаешь разбирать словарные переводы RU/EO. "
            "Верни только JSON-объект без markdown: "
            "{\"candidates\":[строки],\"confidence\":число0..1,\"rationale_short\":строка}. "
            "Нужно предложить 1-5 вариантов разбиения/раскрытия блока на отдельные переводные элементы. "
            "Сохраняй исходный язык и смысл, не добавляй новые термины без основания."
        )

        user_payload = {
            "lang": lang,
            "article_id": art_id,
            "form_id": form_id,
            "block_id": block_id,
            "block_label": label,
            "block_items": source_items if isinstance(source_items, list) else [],
            "source_text": source_text,
        }

        request_payload = {
            "model": model,
            "temperature": 0.1,
            "max_tokens": 500,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
        }

        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.post(f"{base_url}/chat/completions", json=request_payload)
            response.raise_for_status()
            data = response.json()

        message = data.get("choices", [{}])[0].get("message", {})
        content = message.get("content", "")
        reasoning = message.get("reasoning_content", "")

        payload_text = content.strip() if isinstance(content, str) else ""
        if not payload_text and isinstance(reasoning, str) and reasoning.strip():
            # Некоторые локальные модели кладут финальный JSON в reasoning_content
            # или оставляют там единственный JSON-блок.
            reasoning_text = reasoning.strip()
            start = reasoning_text.find("{")
            end = reasoning_text.rfind("}")
            if start != -1 and end != -1 and end > start:
                payload_text = reasoning_text[start:end + 1].strip()

        if not payload_text:
            raise ValueError("Empty LM Studio response")
        if "```" in payload_text:
            payload_text = payload_text.replace("```json", "").replace("```", "").strip()

        parsed = json.loads(payload_text)
        raw_candidates = parsed.get("candidates", []) if isinstance(parsed, dict) else []
        candidates = [str(item).strip() for item in raw_candidates if str(item).strip()][:5]
        if not candidates:
            raise ValueError("LM Studio returned no candidates")

        confidence_raw = parsed.get("confidence", 0.0) if isinstance(parsed, dict) else 0.0
        try:
            confidence = max(0.0, min(1.0, float(confidence_raw)))
        except Exception:
            confidence = 0.0

        rationale_short = parsed.get("rationale_short", "") if isinstance(parsed, dict) else ""

        return {
            "provider": f"lmstudio:{model}",
            "candidates": candidates,
            "confidence": confidence,
            "rationale_short": str(rationale_short).strip() or "Ответ получен от LM Studio.",
        }

    def apply_resolution_action(
        self,
        lang: str,
        art_id: int,
        form_id: str,
        block_id: str,
        operator_action: Dict[str, Any],
    ) -> Dict[str, Any]:
        state = self._ensure_state(lang, art_id)
        resolved = state.resolved_translations if isinstance(state.resolved_translations, dict) else {}

        groups = resolved.get("groups")
        if isinstance(groups, dict):
            group_items: List[Dict[str, Any]] = []
            for group_id, payload in groups.items():
                if isinstance(payload, dict):
                    item = dict(payload)
                    item.setdefault("group_id", group_id)
                    group_items.append(item)
            groups = group_items
        if not isinstance(groups, list):
            groups = []

        updated = False
        for idx, group in enumerate(groups):
            if not isinstance(group, dict):
                continue
            if group.get("form_id") == form_id and group.get("block_id") == block_id:
                groups[idx] = {
                    **group,
                    "form_id": form_id,
                    "block_id": block_id,
                    "operator_action": operator_action,
                    "updated_at": datetime.utcnow().isoformat(),
                }
                updated = True
                break

        if not updated:
            groups.append(
                {
                    "form_id": form_id,
                    "block_id": block_id,
                    "operator_action": operator_action,
                    "updated_at": datetime.utcnow().isoformat(),
                }
            )

        resolved["groups"] = groups
        state.resolved_translations = resolved
        self.session.commit()

        return {
            "status": "ok",
            "article_id": art_id,
            "lang": lang,
            "form_id": form_id,
            "block_id": block_id,
            "operator_action": operator_action,
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
        # Используем результат из result вместо повторного парсинга через load_article
        payload = self._build_payload_from_result(result, lang, art_id)
        return payload, result
    
    def _build_payload_from_result(
        self, result: "ArticleParseResult", lang: str, art_id: int
    ) -> Dict[str, Any]:
        """Строит payload из уже созданного result без повторного парсинга"""
        state = self._ensure_state(lang, art_id)
        notes = self._fetch_notes(lang, art_id)
        review_data = result.review
        
        if not review_data:
            return {
                "art_id": art_id,
                "lang": lang,
                "headword": result.headword,
                "template": result.template,
                "success": result.success,
                "parse_error": result.error,
                "review_diagnostic": result.review_diagnostic,
                "parsing_status": state.parsing_status,
                "groups": [],
                "auto_candidates": [],
                "resolved_translations": state.resolved_translations or {},
                "notes": notes,
                "review_notes": [],
            }
        
        # Остальная логика как в load_article
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
                manual_override = None
                if isinstance(stored, dict):
                    accepted = stored.get("accepted")
                    manual_override = stored.get("manual_override")
                if accepted is None:
                    accepted = not group.requires_review
                
                candidates_list = [
                    {
                        "id": candidate.candidate_id,
                        "title": candidate.title,
                        "items": list(candidate.items),
                    }
                    for candidate in group.candidates
                ]
                
                if group.requires_review:
                    manual_items = []
                    if manual_override and isinstance(manual_override, str):
                        manual_items = [phrase.strip() for phrase in manual_override.split("|") if phrase.strip()]
                    candidates_list.append({
                        "id": "manual",
                        "title": "Свой вариант",
                        "items": manual_items,
                    })
                
                selected = group.selected_candidate
                if manual_override and isinstance(manual_override, str) and manual_override.strip():
                    selected = "manual"
                
                groups_payload.append(
                    {
                        "group_id": group_id,
                        "items": list(group.items),
                        "base_items": list(group.base_items),
                        "label": group.label,
                        "requires_review": group.requires_review,
                        "auto_generated": group.auto_generated,
                        "section": group.section,
                        "candidates": candidates_list,
                        "selected_candidate": selected,
                        "accepted": accepted,
                        "eo_source": group.eo_source,
                    }
                )
        
        auto_candidates = [
            {"headword": result.headword, "translations": result.translations}
        ] if result.headword and result.translations else []
        
        notes_payload = []
        for note in notes:
            created_at = note.get("created_at")
            if created_at and hasattr(created_at, "isoformat"):
                created_at_str = created_at.isoformat()
            elif isinstance(created_at, str):
                created_at_str = created_at
            else:
                created_at_str = None
            
            notes_payload.append({
                "id": note.get("id"),
                "author": note.get("author"),
                "body": note.get("body"),
                "created_at": created_at_str,
            })
        
        if review_notes:
            notes_payload.extend([{"id": None, "author": "system", "body": note, "created_at": None} for note in review_notes])
        
        return {
            "art_id": art_id,
            "lang": lang,
            "headword": result.headword,
            "template": result.template,
            "success": result.success,
            "parse_error": result.error,
            "review_diagnostic": result.review_diagnostic,
            "parsing_status": state.parsing_status,
            "groups": groups_payload,
            "auto_candidates": auto_candidates,
            "resolved_translations": resolved,
            "notes": notes_payload,
            "review_notes": review_notes,
        }

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
