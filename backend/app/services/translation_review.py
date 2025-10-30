from __future__ import annotations

import re
import copy
from collections import defaultdict
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from app.database import SessionLocal
from app.models import Article, ArticleRu


@dataclass(slots=True)
class TranslationCandidate:
    candidate_id: str
    title: str
    items: List[str]


@dataclass(slots=True)
class TranslationGroup:
    """Represents a group of synonymous Russian translations for review."""

    items: List[str]
    label: Optional[str] = None
    requires_review: bool = False
    base_items: List[str] = field(default_factory=list)
    auto_generated: bool = False
    section: Optional[str] = None
    candidates: List[TranslationCandidate] = field(default_factory=list)
    selected_candidate: Optional[str] = None
    eo_source: Optional[str] = None  # Esperanto text for examples/illustrations

    @property
    def is_empty(self) -> bool:
        return not self.items

    def find_candidate(self, candidate_id: Optional[str]) -> Optional[TranslationCandidate]:
        if not candidate_id:
            return None
        for candidate in self.candidates:
            if candidate.candidate_id == candidate_id:
                return candidate
        return None


@dataclass(slots=True)
class TranslationReview:
    headword: str
    groups: List[TranslationGroup]
    notes: List[str]


@lru_cache(maxsize=512)
def _load_article_text(lang: str, art_id: int) -> Optional[str]:
    if lang not in {"eo", "ru"}:
        return None
    model = Article if lang == "eo" else ArticleRu
    with SessionLocal() as session:
        record = session.get(model, art_id)
        if not record:
            return None
        return record.priskribo


@lru_cache(maxsize=512)
def _get_article_sections(lang: str, art_id: int) -> Dict[str, List[str]]:
    text = _load_article_text(lang, art_id)
    if not text:
        return {}
    sections: Dict[str, List[str]] = {"<main>": []}
    current = "<main>"
    for raw_line in text.splitlines():
        line = raw_line.rstrip("\r")
        if not line:
            continue
        if line.startswith("["):
            end_idx = line.find("]")
            if end_idx != -1:
                key = line[: end_idx + 1]
                sections.setdefault(key, [])
                current = key
                remainder = line[end_idx + 1 :]
                if remainder:
                    sections[current].append(remainder)
                continue
        sections.setdefault(current, []).append(line)
    return sections


def build_translation_review(parsed_article: Dict) -> TranslationReview:
    if not isinstance(parsed_article, dict):
        return TranslationReview(headword="<без заголовка>", groups=[], notes=[])

    headword = (parsed_article.get("headword") or {}).get("raw_form") or "<без заголовка>"
    meta = parsed_article.get("meta") or {}
    lang = meta.get("lang")
    art_id = meta.get("art_id")
    

    article_sections = _get_article_sections(lang, art_id) if lang and art_id else None
    groups, notes = _collect_groups_from_blocks(
        parsed_article.get("body") or [],
        section=headword,
        article_sections=article_sections,
    )
    return TranslationReview(headword=headword, groups=groups, notes=notes)


def format_translation_review(review: TranslationReview) -> str:
    lines = [review.headword]
    for group in review.groups:
        if group.is_empty:
            continue
        section_prefix = f"[{group.section}] " if group.section else ""
        label_prefix = f"{group.label} " if group.label else ""
        body = _format_group_items(group.items)
        suffix = "  [?]" if group.requires_review else ""
        lines.append(f"  ⮕ {section_prefix}{label_prefix}{body}{suffix}")
    for note in review.notes:
        lines.append(f"  ℹ {note}")
    return "\n".join(lines)


def _build_translation_candidates(
    base_items: Sequence[str],
    expanded_items: Sequence[str],
) -> List[TranslationCandidate]:
    cleaned_base = [item for item in base_items if item]
    cleaned_expanded = [item for item in expanded_items if item]

    candidates: List[TranslationCandidate] = []

    if cleaned_expanded:
        if cleaned_expanded == cleaned_base:
            candidates.append(
                TranslationCandidate(
                    candidate_id="base",
                    title="Как в источнике",
                    items=list(cleaned_expanded),
                )
            )
        else:
            candidates.append(
                TranslationCandidate(
                    candidate_id="expanded",
                    title="Расширенные комбинации",
                    items=list(cleaned_expanded),
                )
            )

    if cleaned_base and cleaned_base != cleaned_expanded:
        candidates.append(
            TranslationCandidate(
                candidate_id="base",
                title="Как в источнике",
                items=list(cleaned_base),
            )
        )

    if not candidates and cleaned_base:
        candidates.append(
            TranslationCandidate(
                candidate_id="base",
                title="Как в источнике",
                items=list(cleaned_base),
            )
        )

    if not candidates and cleaned_expanded:
        candidates.append(
            TranslationCandidate(
                candidate_id="expanded",
                title="Расширенные комбинации",
                items=list(cleaned_expanded),
            )
        )

    return candidates


def _select_candidate(group: TranslationGroup, candidate_id: Optional[str]) -> None:
    candidate = group.find_candidate(candidate_id)
    if candidate is None and group.candidates:
        candidate = group.candidates[0]

    if candidate:
        group.items = list(candidate.items)
        group.selected_candidate = candidate.candidate_id
    else:
        group.items = list(group.items)
        group.selected_candidate = None

    if group.base_items:
        group.auto_generated = bool(group.items != group.base_items)


def apply_candidate_selection(
    review: TranslationReview,
    resolved_groups: Optional[Dict[str, Any]],
) -> None:
    resolved_map = resolved_groups or {}
    for index, group in enumerate(review.groups):
        group_id = f"group_{index}"
        stored = resolved_map.get(group_id)
        candidate_id = None
        if isinstance(stored, dict):
            candidate_id = stored.get("selected_candidate")
        _select_candidate(group, candidate_id)


def _format_group_items(items: Sequence[str]) -> str:
    cleaned = [_clean_spacing(item) for item in items if item]
    cleaned = [item for item in cleaned if item]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    return "[" + " | ".join(cleaned) + "]"


def _collect_groups_from_blocks(
    blocks: Iterable[Dict],
    section: Optional[str],
    article_sections: Optional[Dict[str, List[str]]],
) -> Tuple[List[TranslationGroup], List[str]]:
    groups: List[TranslationGroup] = []
    notes: List[str] = []
    buffer_content: List[List[Dict]] = []
    buffer_requires_review = False
    buffer_continues = False
    pending_suffixes: List[str] = []

    def _append_note(text: str) -> None:
        if not text:
            return
        notes.append(f"{section}: {text}" if section else text)

    def _flush_buffer() -> None:
        nonlocal buffer_content, buffer_requires_review, buffer_continues, pending_suffixes
        if not buffer_content:
            return
        
        combined: List[Dict] = []
        for chunk in buffer_content:
            combined.extend(chunk)

        label = _extract_label(combined)
        group_specs, extra_notes = _split_translation_groups(
            combined,
            section=section,
            article_sections=article_sections,
        )
        for note in extra_notes:
            _append_note(note)

        for index, spec in enumerate(group_specs):
            base_items = spec.get("base", [])
            expanded_items = spec.get("expanded", [])
            if not expanded_items or _is_pos_marker(base_items):
                continue

            if len(base_items) == 1 and base_items[0].lower().startswith("или "):
                pending_suffixes = expanded_items
                continue

            items = expanded_items
            auto_generated = items != base_items

            if pending_suffixes:
                suffix_expansions = [
                    _clean_spacing(f"{item} {suffix}")
                    for item in items
                    for suffix in pending_suffixes
                ]
                if suffix_expansions:
                    items = _deduplicate([*items, *suffix_expansions])
                    auto_generated = True
                pending_suffixes = []

            cleaned_base = []
            for base_item in base_items:
                stripped = base_item.strip()
                if _is_meaningful_item(stripped):
                    cleaned_base.append(stripped)

            if label and label.strip().lower().startswith("т.е"):
                items = _split_leading_adjectives(items)
            items = _normalize_compound_terms(items)
            label_text = label.strip().rstrip(".").lower() if label else ""
            if label_text in _IGNORABLE_LABELS:
                label = None
            if auto_generated and cleaned_base and any("(" in base for base in cleaned_base):
                cleaned_base = list(items)
            elif len(items) > len(cleaned_base):
                cleaned_base = list(items)
            items = _normalize_compound_terms(items)
            expanded = _expand_prepositional_variations(items, cleaned_base)
            items = expanded
            if len(items) > len(cleaned_base):
                cleaned_base = list(items)
            candidates = _build_translation_candidates(cleaned_base, items)
            group = TranslationGroup(
                items=list(items),
                label=label if index == 0 else None,
                requires_review=buffer_requires_review,
                base_items=cleaned_base,
                auto_generated=auto_generated,
                section=section,
                candidates=candidates,
            )
            _select_candidate(group, None)
            groups.append(group)

        buffer_content = []
        buffer_requires_review = False
        buffer_continues = False
        pending_suffixes = []

    for block in blocks or []:
        block_type = block.get("type")

        if block_type == "illustration" and (not block.get("eo") or not _has_letters(block.get("eo"))):
            ru_segments = block.get("ru_segments")
            if ru_segments:
                converted = _ru_segments_to_content(ru_segments)
                if converted:
                    transformed = dict(block)
                    transformed.pop("ru_segments", None)
                    transformed.pop("eo", None)
                    transformed["type"] = "translation"
                    transformed["content"] = converted
                    block = transformed
                    block_type = "translation"

        if block_type == "headword":
            _flush_buffer()
            raw_form = block.get("raw_form")
            child_groups, child_notes = _collect_groups_from_blocks(
                block.get("children") or [],
                section=raw_form,
                article_sections=article_sections,
            )
            groups.extend(child_groups)
            notes.extend(child_notes)
            continue

        if block_type == "illustration" and block.get("eo"):
            _flush_buffer()
            example_section = block.get("eo_raw") or block.get("eo")
            example_groups, example_notes = _build_groups_from_example(
                block,
                example_section,
                article_sections,
            )
            groups.extend(example_groups)
            notes.extend(example_notes)
            continue
        


        if block_type == "explanation":
            extracted_content, extra_notes = _extract_translation_from_explanation(block.get("content") or [])
            if extracted_content and buffer_content:
                has_regular = any(
                    node.get("type") == "text" and node.get("style") == "regular"
                    for node in extracted_content
                )
                if has_regular:
                    _flush_buffer()
                    buffer_content.append([])
                last_chunk = buffer_content[-1]
                _trim_trailing_parenthesis(last_chunk)
                first_node = extracted_content[0] if extracted_content else None
                if first_node and first_node.get("type") == "text":
                    for node in reversed(last_chunk):
                        if node.get("type") != "text":
                            continue
                        existing_text = node.get("text", "")
                        if _has_unclosed_parenthesis(existing_text):
                            if "(" in existing_text:
                                pivot = existing_text.rfind("(")
                                trimmed_text = existing_text[:pivot].rstrip()
                                node["text"] = trimmed_text
                            else:
                                trimmed_text = existing_text
                            raw_text = first_node.get("text", "")
                            stripped = raw_text.lstrip()
                            leading_ws_len = len(raw_text) - len(stripped)
                            leading_ws = raw_text[:leading_ws_len]
                            if stripped:
                                if stripped.startswith(")"):
                                    adjusted = leading_ws + stripped
                                else:
                                    adjusted = f"{leading_ws}) {stripped}"
                                first_node = dict(first_node)
                                first_node["text"] = adjusted
                                extracted_content = [first_node, *extracted_content[1:]]
                            break
            elif buffer_content and not extracted_content:
                _trim_trailing_parenthesis(buffer_content[-1])
            if extracted_content:
                if buffer_content:
                    buffer_content[-1].extend(extracted_content)
                else:
                    buffer_content.append(extracted_content)
                buffer_continues = _block_indicates_continuation({"content": extracted_content})
            if extra_notes:
                for note in extra_notes:
                    attached = False
                    if buffer_content:
                        last_chunk = buffer_content[-1]
                        for idx in range(len(last_chunk) - 1, -1, -1):
                            candidate_node = last_chunk[idx]
                            if candidate_node.get("type") != "text":
                                continue
                            candidate_text = candidate_node.get("text", "")
                            if _has_unclosed_parenthesis(candidate_text):
                                separator = "" if candidate_text.endswith((" ", "(", "—", "-", "‑")) else " "
                                candidate_node["text"] = f"{candidate_text.rstrip()}{separator}{note}"
                                attached = True
                                break
                    if not attached:
                        _append_note(note)
            continue

        if block_type == "translation" or (block_type == "illustration" and not block.get("eo")):
            block_number = block.get("number")
            if buffer_content and block_number is not None:
                _flush_buffer()
            
            # Если это пронумерованное значение (1., 2., ...), его content - это ПЕРВЫЙ перевод
            # (не заголовок!), а children - остальные переводы и примеры
            if block_number is not None:
                # Обрабатываем content как обычный translation (это первый перевод)
                block_content = _clone_nodes(block.get("content") or [])
                if block_content:
                    content_normalized = _normalize_labelled_content(block_content)
                    if content_normalized:
                        buffer_content.append(content_normalized)
                        if block.get("ru_requires_review"):
                            buffer_requires_review = True
                        buffer_continues = _block_indicates_continuation(block)
                
                # Затем обрабатываем детей пронумерованного значения
                for child in block.get("children") or []:
                    child_type = child.get("type")
                    if child_type == "translation":
                        if buffer_content and child.get("number") is not None:
                            _flush_buffer()
                        child_content_raw = _clone_nodes(child.get("content") or [])
                        child_content = _normalize_labelled_content(child_content_raw)
                        if child_content:
                            buffer_content.append(child_content)
                            if child.get("ru_requires_review"):
                                buffer_requires_review = True
                            buffer_continues = _block_indicates_continuation(child)
                        
                        # Обрабатываем детей child (примеры)
                        for grandchild in child.get("children") or []:
                            if grandchild.get("type") == "illustration" and grandchild.get("eo"):
                                _flush_buffer()
                                example_section = grandchild.get("eo_raw") or grandchild.get("eo")
                                example_groups, example_notes = _build_groups_from_example(
                                    grandchild,
                                    example_section,
                                    article_sections,
                                )
                                groups.extend(example_groups)
                                notes.extend(example_notes)
                    
                    elif child_type == "illustration":
                        if child.get("eo"):
                            _flush_buffer()
                            example_section = child.get("eo_raw") or child.get("eo")
                            example_groups, example_notes = _build_groups_from_example(
                                child,
                                example_section,
                                article_sections,
                            )
                            groups.extend(example_groups)
                            notes.extend(example_notes)
                        else:
                            child_content = _clone_nodes(child.get("content") or [])
                            if child_content:
                                buffer_content.append(child_content)
                                if child.get("ru_requires_review"):
                                    buffer_requires_review = True
                                buffer_continues = _block_indicates_continuation(child)
                
                # После обработки всех детей, flush buffer
                _flush_buffer()
                continue
            
            # Обычный translation (не numbered)
            block_requires_review = bool(block.get("ru_requires_review"))
            block_continuation = _block_indicates_continuation(block)
            is_plain_illustration = block_type == "illustration" and not block.get("eo")
            
            # Если в buffer уже есть контент и новый блок не является продолжением,
            # сбрасываем buffer перед добавлением нового контента
            if buffer_content and not buffer_continues and not block_continuation:
                _flush_buffer()
            merge_suffix = False
            if is_plain_illustration and buffer_content:
                raw_content = block.get("content") or []
                if raw_content:
                    leading_node = raw_content[0]
                    remaining_nodes = raw_content[1:]
                    if (
                        isinstance(leading_node, dict)
                        and leading_node.get("type") == "text"
                        and all(isinstance(node, dict) and node.get("type") == "divider" for node in remaining_nodes)
                    ):
                        merge_suffix = True
            should_force_flush = is_plain_illustration and not merge_suffix
            if (
                buffer_content
                and (
                    (
                        not buffer_requires_review
                        and not block_requires_review
                        and not buffer_continues
                        and not merge_suffix
                    )
                    or should_force_flush
                )
            ):
                _flush_buffer()

            cloned_content = _clone_nodes(block.get("content") or [])
            if cloned_content:
                if merge_suffix and buffer_content:
                    previous_chunk = buffer_content[-1]
                    leading = cloned_content[0]
                    trailing = cloned_content[1:]
                    if (
                        previous_chunk
                        and isinstance(leading, dict)
                        and leading.get("type") == "text"
                        and isinstance(previous_chunk[-1], dict)
                        and previous_chunk[-1].get("type") == "text"
                        and all(isinstance(node, dict) and node.get("type") == "divider" for node in trailing)
                    ):
                        merged_text = _join_parts(previous_chunk[-1].get("text", ""), leading.get("text", ""))
                        previous_chunk[-1]["text"] = merged_text
                        if trailing:
                            previous_chunk.extend(trailing)
                        cloned_content = []
                if cloned_content:
                    buffer_content.append(cloned_content)
            if block_requires_review:
                buffer_requires_review = True
            buffer_continues = block_continuation
            
            # Обрабатываем children (только для не-numbered translations)
            for child in block.get("children") or []:
                child_type = child.get("type")
                if child_type == "translation":
                    if buffer_content and child.get("number") is not None:
                        _flush_buffer()
                    child_content_raw = _clone_nodes(child.get("content") or [])
                    child_content = _normalize_labelled_content(child_content_raw)
                    if child_content:
                        buffer_content.append(child_content)
                        if child.get("ru_requires_review"):
                            buffer_requires_review = True
                        buffer_continues = _block_indicates_continuation(child)
                elif child_type == "illustration":
                    # Иллюстрации С разделением eo/ru должны обрабатываться отдельно
                    if child.get("eo"):
                        _flush_buffer()
                        example_section = child.get("eo_raw") or child.get("eo")
                        example_groups, example_notes = _build_groups_from_example(
                            child,
                            example_section,
                            article_sections,
                        )
                        groups.extend(example_groups)
                        notes.extend(example_notes)
                    else:
                        # Иллюстрации БЕЗ разделения попадают в переводы
                        child_content = _clone_nodes(child.get("content") or [])
                        if child_content:
                            buffer_content.append(child_content)
                            if child.get("ru_requires_review"):
                                buffer_requires_review = True
                            buffer_continues = _block_indicates_continuation(child)
            continue

        _flush_buffer()

        if block_type == "note":
            text = _consume_text(block.get("content") or [])
            if text:
                _append_note(text)

    _flush_buffer()
    return groups, notes


def _build_groups_from_example(
    block: Dict,
    section: Optional[str],
    article_sections: Optional[Dict[str, List[str]]],
) -> Tuple[List[TranslationGroup], List[str]]:
    segments = block.get("ru_segments") or []
    content = _ru_segments_to_content(segments)
    eo_text = block.get("eo")  # Esperanto source text for examples
    
    if not content:
        return [], []

    label = _extract_label(content)
    group_specs, extra_notes = _split_translation_groups(
        content,
        section=section,
        article_sections=article_sections,
    )
    
    requires_review = bool(block.get("ru_requires_review"))

    groups: List[TranslationGroup] = []
    for spec in group_specs:
        base_items = spec.get("base", [])
        expanded_items = spec.get("expanded", [])
        if not expanded_items or _is_pos_marker(base_items):
            continue
        auto_generated = expanded_items != base_items
        label_text = label.strip().lower() if label else None
        if label_text and label_text.startswith('т.е'):
            expanded_items = _split_leading_adjectives(expanded_items)
        expanded_items = _normalize_compound_terms(expanded_items)
        candidates = _build_translation_candidates(base_items, expanded_items)
        group = TranslationGroup(
            items=list(expanded_items),
            label=label,
            requires_review=requires_review,
            base_items=base_items,
            auto_generated=auto_generated,
            section=section,
            candidates=candidates,
            eo_source=eo_text,
        )
        _select_candidate(group, None)
        groups.append(group)

    notes = [f"{section}: {note}" if section else note for note in extra_notes]
    return groups, notes


def _extract_label(content: Iterable[Dict]) -> Optional[str]:
    pieces: List[str] = []
    for node in content:
        if node.get("type") == "label":
            text = node.get("text")
            if text:
                pieces.append(text.strip())
    if not pieces:
        return None
    return " ".join(pieces)


_ALT_SPLIT_RE = re.compile(r"\b(?:или(?:\s+же)?|либо|/)\b", re.IGNORECASE)
_PREPOSITIONAL_SPLIT_RE = re.compile(
    r"^(?P<prep>для|из|из-за|по|при|в|во|на|с|со|от|о|об|обо|к|ко|у|за|над|под|между)\b",
    re.IGNORECASE,
)
_REFERENCE_TRAIL_RE = re.compile(r"\s*[A-Za-z0-9_'`]+>$")


def _merge_clause_parts(parts: List[str]) -> List[str]:
    result: List[str] = []
    pending: Optional[str] = None

    for part in parts:
        segment = part.strip()
        if not segment:
            continue

        remaining = segment
        while remaining:
            if ";" in remaining:
                before, after = remaining.split(";", 1)
                before = before.strip()
                if pending:
                    if before:
                        before = _clean_spacing(f"{pending}, {before}")
                    else:
                        before = pending
                    pending = None
                if before:
                    result.append(before)
                remaining = after.strip()
                continue

            if pending:
                pending = _clean_spacing(f"{pending}, {remaining}")
            else:
                pending = remaining
            break

    if pending:
        result.append(pending)

    return result


def _split_translation_groups(
    content: Iterable[Dict],
    *,
    section: Optional[str],
    article_sections: Optional[Dict[str, List[str]]],
) -> Tuple[List[Dict[str, List[str]]], List[str]]:
    builder = _PhraseBuilder()
    current_group: List[str] = []
    base_groups: List[List[str]] = []
    extra_notes: List[str] = []

    content = _merge_adjacent_text_nodes(_expand_inline_dividers(list(content)))
    content = _merge_proverb_like_segments(content)

    proverb_phrase = _extract_proverb_phrase(content)
    proverb_notes: List[str] = []
    if proverb_phrase:
        for node in content:
            if node.get("type") == "note":
                note_text = _extract_note_text(node)
                if note_text:
                    proverb_notes.append(note_text)
        return ([{"base": [proverb_phrase], "expanded": [proverb_phrase]}], proverb_notes)

    def _flush_builder() -> None:
        phrases = builder.flush()
        if phrases:
            current_group.extend(phrases)
        extra_notes.extend(builder.take_notes())

    def _finalize_group() -> None:
        nonlocal current_group
        if current_group:
            base_groups.append(_deduplicate(current_group))
            current_group = []

    for node in content:
        node_type = node.get("type")
        if node_type == "label":
            continue
        if node_type == "divider":
            symbol = (node.get("text") or "").strip()
            if symbol == ",":
                _flush_builder()
            elif symbol == ";":
                _flush_builder()
                _finalize_group()
            elif symbol in (".", "!", "?"):
                # Знаки конца предложения/восклицания присоединяем к предыдущему слову
                builder.append_punctuation(symbol)
            else:
                builder.add_text(symbol)
            continue
        if node_type == "note":
            note_text = _extract_note_text(node)
            alternatives = _extract_note_alternatives(note_text)
            if alternatives:
                builder.add_alternatives(alternatives)
            else:
                builder.add_note(note_text)
            continue
        text = node.get("text")
        if text is not None:
            builder.add_text(text)

    _flush_builder()
    _finalize_group()

    results: List[Dict[str, List[str]]] = []
    for base in base_groups:
        cleaned_base: List[str] = []
        expanded: List[str] = []
        for item in base:
            raw_clean = item.strip()
            if _is_meaningful_item(raw_clean):
                cleaned_base.append(raw_clean)
            expanded.extend(
                variant
                for variant in _expand_parenthetical_forms(item)
                if variant
            )
        expanded = _deduplicate([_strip_trailing_punctuation(x) for x in expanded])
        expanded = [item for item in expanded if _is_meaningful_item(item)]
        expanded = _expand_cross_product(expanded)
        expanded = _expand_suffix_appending(expanded)
        expanded = _deduplicate(expanded)
        results.append(
            {
                "base": cleaned_base,
                "expanded": expanded or base,
            }
        )

    results, extra_notes = _apply_source_fallback(
        results,
        content,
        section=section,
        article_sections=article_sections,
        extra_notes=extra_notes,
    )
    normalized_results: List[Dict[str, List[str]]] = []
    seen_notes: set[str] = set(extra_notes)

    for spec in results:
        original_base = spec.get("base") or []
        original_expanded = spec.get("expanded") or []

        base_clean, base_notes = _sanitize_spec_values(original_base)
        expanded_clean, expanded_notes = _sanitize_spec_values(original_expanded)

        base_clean = _expand_inline_synonyms_list(base_clean)
        expanded_clean = _expand_inline_synonyms_list(expanded_clean or base_clean)

        for note in (*base_notes, *expanded_notes):
            if note and note not in seen_notes:
                extra_notes.append(note)
                seen_notes.add(note)

        spec["base"] = base_clean
        spec["expanded"] = expanded_clean or base_clean
        if spec.get("auto_generated") is None:
            spec["auto_generated"] = expanded_clean != original_expanded

        normalized_results.append(spec)

    return normalized_results, extra_notes


def _normalize_note_text(note: str) -> str:
    cleaned = note.replace("_", " ").strip()
    if cleaned.endswith('.'):
        cleaned = cleaned[:-1].strip()
    return cleaned


def _separate_trailing_note(text: str) -> Tuple[str, Optional[str]]:
    match = re.search(r"\(([^)]+)\)\.?$", text)
    if not match:
        return text, None
    note = _normalize_note_text(match.group(1))
    cleaned = _clean_spacing(text[: match.start()])
    return cleaned, note


_FALLBACK_TOKEN_RE = re.compile(r"[^\s,;:]+")


def _fallback_tokenize(value: str) -> List[str]:
    if not value:
        return []
    return [
        token
        for token in _FALLBACK_TOKEN_RE.findall(value.replace("_", " "))
        if token
    ]


def _sanitize_spec_values(values: Optional[Iterable[str]]) -> Tuple[List[str], List[str]]:
    sanitized: List[str] = []
    notes: List[str] = []
    seen_notes: set[str] = set()

    for raw in values or []:
        cleaned_value = _clean_spacing((raw or "").replace("_", " "))
        if not cleaned_value:
            continue
        cleaned_value = _normalize_optional_prefix_spacing(cleaned_value)
        stripped_value, note = _separate_trailing_note(cleaned_value)
        if stripped_value:
            stripped_value, placeholder_note = _strip_note_placeholder(stripped_value)
            if placeholder_note and placeholder_note not in seen_notes:
                notes.append(placeholder_note)
                seen_notes.add(placeholder_note)
            sanitized.append(stripped_value)
        if note and note not in seen_notes:
            notes.append(note)
            seen_notes.add(note)

    return _deduplicate(sanitized), notes


_NOTE_PLACEHOLDER_RE = re.compile(
    r"(?:\b[а-яё`]+(?:\s+[а-яё`]+)?-л\.?)$", re.IGNORECASE
)

_OPTIONAL_PREFIX_RE = re.compile(
    r"(\S)\(([^)]+)\)\s+([^\s,;:.])",
    re.UNICODE,
)


def _strip_note_placeholder(value: str) -> Tuple[str, Optional[str]]:
    match = _NOTE_PLACEHOLDER_RE.search(value)
    if not match:
        return value, None
    note = match.group(0)
    cleaned = _clean_spacing(value[: match.start()])
    return cleaned, _normalize_note_text(note.replace("-л", "-л.").rstrip("."))


def _normalize_optional_prefix_spacing(value: str) -> str:
    def _replacer(match: re.Match[str]) -> str:
        before, inside, after = match.groups()
        return f"{before} ({inside}){after}"

    return _OPTIONAL_PREFIX_RE.sub(_replacer, value)


def _strip_leading_markers(value: str) -> str:
    cleaned = re.sub(r"^\*\s*", "", value)
    cleaned = re.sub(r"^\{[^}]+\}\s*", "", cleaned)
    cleaned = re.sub(r"^\d+\.\s*", "", cleaned)
    return cleaned


_INLINE_CLAUSE_PREFIXES = {
    "что",
    "чтобы",
    "чтоб",
    "который",
    "которые",
    "которое",
    "которую",
    "которых",
    "которому",
    "когда",
    "куда",
    "где",
    "если",
    "будучи",
    "как",
    "будто",
    "словно",
}

_PARTICIPLE_SUFFIXES = (
    "ющий",
    "ющая",
    "ющее",
    "ющие",
    "ющим",
    "ющего",
    "ющей",
    "ющихся",
    "ющийся",
    "ющаяся",
    "ющееся",
    "ющимся",
    "ющегося",
)


def _should_attach_inline_segment(segment: str) -> bool:
    text = _clean_spacing(segment)
    if not text:
        return True
    tokens = text.split()
    if not tokens:
        return True
    first = _strip_accents(tokens[0]).lower()
    if first in _INLINE_CLAUSE_PREFIXES or any(first.startswith(prefix) for prefix in ("котор",)):
        return True
    if len(tokens) > 1:
        if first.endswith(_PARTICIPLE_SUFFIXES):
            return True
        if first in {"то", "же"}:
            return True
    return False


def _split_inline_synonyms(value: str) -> List[str]:
    normalized = _clean_spacing(value)
    if not normalized:
        return []

    segments: List[str] = []
    buffer: List[str] = []
    depth = 0
    for char in normalized:
        if char == "(":
            depth += 1
        elif char == ")":
            if depth:
                depth -= 1
        if char == "," and depth == 0:
            segment = "".join(buffer).strip()
            if segment:
                segments.append(segment)
            buffer = []
            continue
        buffer.append(char)
    tail = "".join(buffer).strip()
    if tail:
        segments.append(tail)

    if not segments:
        return []

    parts: List[str] = []
    current: Optional[str] = None

    for segment in segments:
        if not segment:
            continue
        if current is None:
            current = segment
            continue
        if _should_attach_inline_segment(segment):
            current = _clean_spacing(f"{current}, {segment}")
        else:
            parts.append(_clean_spacing(current))
            current = segment

    if current:
        parts.append(_clean_spacing(current))

    return _deduplicate(parts)


def _expand_inline_synonyms_list(items: List[str]) -> List[str]:
    expanded: List[str] = []
    for item in items:
        for chunk in _split_inline_synonyms(item):
            expanded.extend(_expand_parenthetical_forms(chunk))
    return _deduplicate(expanded)


def _apply_source_fallback(
    specs: List[Dict[str, List[str]]],
    content: Iterable[Dict],
    *,
    section: Optional[str],
    article_sections: Optional[Dict[str, List[str]]],
    extra_notes: List[str],
) -> Tuple[List[Dict[str, List[str]]], List[str]]:
    if not article_sections or not section:
        return specs, extra_notes
    section_lines = article_sections.get(section)
    if not section_lines:
        return specs, extra_notes
    
    # Если content содержит только простой текст (один text node без dividers),
    # не применяем fallback - это простой заголовочный перевод
    content_list = list(content)
    if len(content_list) == 1 and content_list[0].get("type") == "text":
        return specs, extra_notes
    
    # Фильтруем строки, содержащие латинские буквы или начинающиеся с ~ (это примеры)
    # ТАКЖЕ фильтруем пронумерованные значения (1., 2., ...), которые уже обработаны через numbered translation logic
    def _is_example_line(text: str) -> bool:
        # Убираем отступы
        stripped = text.strip()
        # Строки, начинающиеся с ~ - это примеры
        if stripped.startswith('~'):
            return True
        # Пронумерованные значения (1., 2., ...) - пропускаем, они уже обработаны
        if re.match(r'^\s*\*?\s*\d+\.', stripped):
            return True
        # Проверяем на латинские буквы (убрав маркеры)
        cleaned = text.replace('_', '').replace('<', '').replace('>', '').strip()
        return any('a' <= c <= 'z' or 'A' <= c <= 'Z' for c in cleaned)
    
    # Объединяем строки в группы по разделителям, исключая примеры и numbered values
    result_groups = []
    current_group = []
    is_example_group = False
    skip_until_semicolon = False  # Флаг для пропуска строк после numbered value
    
    for line in section_lines:
        if not line.strip():
            continue
        
        # Если строка - numbered value (1., 2., ...), пропускаем её и всё до следующего ;
        if _is_example_line(line):
            # Сохраняем предыдущую группу
            if current_group and not is_example_group and not skip_until_semicolon:
                result_groups.append(' '.join(current_group))
            current_group = []
            
            # Если это numbered value, пропускаем всё до ;
            stripped = line.strip()
            if re.match(r'^\*?\s*\d+\.', stripped):
                skip_until_semicolon = True
                is_example_group = False
            else:
                # Это example с ~ или латинскими буквами
                is_example_group = True
                skip_until_semicolon = False
            continue
        
        # Если мы в режиме пропуска (после numbered value), пропускаем всё до ;
        if skip_until_semicolon:
            if line.rstrip().endswith(';'):
                skip_until_semicolon = False
            continue
        
        # Если строка начинается с ~, начинается новая группа-пример
        if line.strip().startswith('~'):
            if current_group and not is_example_group:
                result_groups.append(' '.join(current_group))
            current_group = []
            is_example_group = True
            continue
        
        # Если это конец группы (заканчивается на ;)
        if line.rstrip().endswith(';'):
            if not is_example_group:
                current_group.append(line.strip())
                result_groups.append(' '.join(current_group))
            current_group = []
            is_example_group = False
        else:
            # Продолжение текущей группы
            if not is_example_group:
                current_group.append(line.strip())
    
    # Добавляем последнюю группу
    if current_group and not is_example_group and not skip_until_semicolon:
        result_groups.append(' '.join(current_group))
    
    source_text = " ".join(result_groups)
    if not source_text:
        return specs, extra_notes

    raw_parts = _split_source_segments(source_text)
    if len(raw_parts) <= 1:
        return specs, extra_notes

    cleaned_parts: List[Tuple[str, Optional[str]]] = []
    tokenized_parts: List[List[str]] = []
    reference_notes_buffer: List[str] = []
    for part in raw_parts:
        # Пропускаем чистые ссылки типа "_ср._ <ventoli>, <ventumi>"
        if _is_pure_reference_segment(part):
            continue
        
        cleaned = _clean_spacing(part.replace("_", " "))
        cleaned = _strip_leading_markers(cleaned)
        leading_note_match = re.match(r"\(([^)]+)\)\s*", cleaned)
        if leading_note_match:
            cleaned = cleaned[leading_note_match.end():]
        cleaned, reference_notes = _remove_reference_suffix(cleaned)
        note_match = re.search(r"\(([^)]+)\)\.?$", cleaned)
        note_value: Optional[str] = None
        if note_match:
            note_value = _normalize_note_text(note_match.group(1))
            cleaned = _clean_spacing(cleaned[: note_match.start()])
        for reference_note in reference_notes:
            if reference_note and reference_note not in reference_notes_buffer:
                reference_notes_buffer.append(reference_note)
        cleaned_parts.append((cleaned, note_value))
        tokenized_parts.append(_fallback_tokenize(cleaned))

    source_idx = 0
    updated_specs: List[Dict[str, List[str]]] = []
    collected_notes = list(extra_notes)
    for note in reference_notes_buffer:
        if note not in collected_notes:
            collected_notes.append(note)

    if (
        len(specs) == 1
        and any("(" in part for part in raw_parts)
        and any(
            " " not in _clean_spacing(item)
            for item in (specs[0].get("base") or specs[0].get("expanded") or [])
        )
    ):
        spec = specs[0]
        expanded_variants: List[str] = []
        for cleaned_text, note in cleaned_parts:
            variants = _expand_parenthetical_forms(cleaned_text)
            if variants:
                expanded_variants.extend(variants)
            else:
                expanded_variants.append(cleaned_text)
            if note and note not in collected_notes:
                collected_notes.append(note)
        expanded_variants = _deduplicate([
            _strip_trailing_punctuation(_clean_spacing(item))
            for item in expanded_variants
            if _clean_spacing(item)
        ])
        if expanded_variants:
            spec["base"] = expanded_variants
            spec["expanded"] = expanded_variants
            spec["auto_generated"] = True
        updated_specs.append(spec)
        return updated_specs, collected_notes

    for spec in specs:
        candidate_items = spec.get("base") or spec.get("expanded") or []
        normalized_items = [
            _clean_spacing((item or "").replace("_", " "))
            for item in candidate_items
            if _clean_spacing((item or "").replace("_", " "))
        ]
        target_text = _clean_spacing(" ".join(normalized_items))
        target_text, trailing_note = _separate_trailing_note(target_text)
        if trailing_note and trailing_note not in collected_notes:
            collected_notes.append(trailing_note)
        if not target_text:
            updated_specs.append(spec)
            continue
        target_tokens = _fallback_tokenize(target_text)
        if not target_tokens:
            updated_specs.append(spec)
            continue

        accum_texts: List[str] = []
        accum_notes: List[Optional[str]] = []
        accum_tokens: List[str] = []
        start_idx = source_idx
        matched = False

        while source_idx < len(cleaned_parts):
            part_text, part_note = cleaned_parts[source_idx]
            part_tokens = tokenized_parts[source_idx]
            if part_text:
                accum_texts.append(part_text)
            if part_note:
                accum_notes.append(part_note)
            source_idx += 1
            if not part_tokens:
                continue
            accum_tokens.extend(part_tokens)
            if accum_tokens == target_tokens:
                matched = True
                break
            if target_tokens[: len(accum_tokens)] != accum_tokens:
                matched = False
                break

        if not matched or not accum_texts:
            if start_idx < len(cleaned_parts):
                source_idx = start_idx + 1
                candidate_text, candidate_note = cleaned_parts[start_idx]
                final_list = _expand_source_variants(candidate_text)
                if final_list:
                    spec["base"] = final_list
                    spec["expanded"] = final_list
                    spec["auto_generated"] = True
                if candidate_note and candidate_note not in collected_notes:
                    collected_notes.append(candidate_note)
            updated_specs.append(spec)
            continue
        else:
            cleaned_list = [
                text for text in (_clean_spacing(item) for item in accum_texts) if text
            ]
            cleaned_list = _deduplicate(cleaned_list)
            if cleaned_list:
                expanded_variants: List[str] = []
                for value in cleaned_list:
                    expanded_variants.extend(_expand_source_variants(value))
                final_list = expanded_variants or cleaned_list
                spec["base"] = final_list
                spec["expanded"] = final_list
                spec["auto_generated"] = True
            for note in accum_notes:
                if note:
                    normalized_note = _normalize_note_text(note)
                    if normalized_note and normalized_note not in collected_notes:
                        collected_notes.append(normalized_note)
        updated_specs.append(spec)

    for idx in range(source_idx, len(cleaned_parts)):
        remaining_text, remaining_note = cleaned_parts[idx]
        final_list = _expand_source_variants(remaining_text)
        if not final_list:
            continue
        new_spec = {
            "base": final_list,
            "expanded": final_list,
            "auto_generated": True,
        }
        updated_specs.append(new_spec)
        if remaining_note and remaining_note not in collected_notes:
            collected_notes.append(remaining_note)

    return updated_specs, collected_notes


def _split_source_segments(text: str) -> List[str]:
    segments: List[str] = []
    current: List[str] = []
    depth = 0
    for char in text:
        if char == '(':
            depth += 1
        elif char == ')':
            depth = max(0, depth - 1)
        if (char == ';' or char == '\n') and depth == 0:
            part = ''.join(current).strip()
            if part:
                segments.append(part)
            current = []
            continue
        current.append(char)
    tail = ''.join(current).strip()
    if tail:
        segments.append(tail)
    return segments


def _is_pure_reference_segment(text: str) -> bool:
    """
    Проверяет, является ли сегмент чистой ссылкой (ср. <...>, см. <...>).
    Такие сегменты не должны попадать в переводы.
    """
    # Убираем markdown _ и пробелы
    cleaned = text.replace("_", "").strip()
    
    # Проверяем, начинается ли с "ср." или "см."
    if not (cleaned.startswith("ср.") or cleaned.startswith("см.")):
        return False
    
    # Убираем префикс
    rest = cleaned[3:].strip()
    
    # Должны остаться только ссылки <...> и разделители
    # Убираем все ссылки вида <что-то>
    without_refs = re.sub(r'<[^>]+>', '', rest)
    # Убираем запятые и пробелы
    without_refs = without_refs.replace(',', '').replace(' ', '').strip()
    
    # Если ничего не осталось - это чистая ссылка
    return len(without_refs) == 0


def _remove_reference_suffix(value: str) -> Tuple[str, List[str]]:
    notes: List[str] = []

    def _replace(match: re.Match[str]) -> str:
        mode = match.group(1).lower()
        target = match.group(2).strip()
        label = "ср." if mode.startswith("ср") else "см."
        note_text = _clean_spacing(f"{label} {target}")
        if note_text and note_text not in notes:
            notes.append(note_text)
        return ""

    cleaned = re.sub(r"(ср|см)\.?\s*<([^>]+)>", _replace, value, flags=re.IGNORECASE)

    def _replace_plain(match: re.Match[str]) -> str:
        mode = match.group(1).lower()
        target = match.group(2).strip()
        label = "ср." if mode.startswith("ср") else "см."
        note_text = _clean_spacing(f"{label} {target}")
        if note_text and note_text not in notes:
            notes.append(note_text)
        return ""

    cleaned = re.sub(r"(ср|см)\.?\s+([A-Za-z0-9`´'’_-]+)", _replace_plain, cleaned, flags=re.IGNORECASE)
    return cleaned.strip(" ,;"), notes


def _expand_source_variants(text: str) -> List[str]:
    variants: List[str] = []
    for option in _expand_parenthetical_forms(text):
        variants.extend(_expand_inline_synonyms_list([option]))
    return _deduplicate([
        _strip_trailing_punctuation(_clean_spacing(item))
        for item in variants
        if _clean_spacing(item)
    ])


def _merge_adjacent_text_nodes(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    for node in nodes:
        if (
            merged
            and node.get("type") == "text"
            and not node.get("kind")
            and merged[-1].get("type") == "text"
            and merged[-1].get("style") == node.get("style")
            and not merged[-1].get("kind")
        ):
            prev_text = merged[-1].get("text", "")
            merged[-1]["text"] = prev_text + (node.get("text") or "")
            continue
        merged.append(node)
    return merged


def _has_letters(value: Optional[str]) -> bool:
    if not value:
        return False
    return any(char.isalpha() for char in value)


def _merge_proverb_like_segments(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not nodes:
        return nodes

    has_proverb_label = any(
        node.get("type") == "label" and _is_proverb_label(node.get("text"))
        for node in nodes
        if isinstance(node, dict)
    )
    if not has_proverb_label:
        return nodes

    merged: List[Dict[str, Any]] = []
    pending_text: Optional[str] = None

    def _flush_pending() -> None:
        nonlocal pending_text
        if pending_text is not None:
            merged.append({"type": "text", "style": "regular", "text": _clean_spacing(pending_text)})
            pending_text = None

    for node in nodes:
        if not isinstance(node, dict):
            _flush_pending()
            merged.append(node)
            continue

        node_type = node.get("type")
        if node_type == "text" and (node.get("style") or "regular") == "regular":
            text_value = node.get("text", "")
            if pending_text is None:
                pending_text = text_value
            else:
                needs_space = bool(text_value) and not text_value.startswith((",", ";", ":", ".", " "))
                if needs_space and pending_text and not pending_text.endswith(" "):
                    pending_text += " "
                pending_text += text_value
            continue

        if node_type == "divider" and (node.get("text") or "").strip() == ",":
            if pending_text is None:
                merged.append(node)
            else:
                if not pending_text.rstrip().endswith(","):
                    pending_text = pending_text.rstrip() + ","
            continue

        _flush_pending()
        merged.append(node)

    _flush_pending()
    return merged


def _is_proverb_label(text: Optional[str]) -> bool:
    if not text:
        return False
    lowered = text.strip().lower()
    return any(keyword in lowered for keyword in ("посл", "погов", "афор"))


def _extract_proverb_phrase(nodes: List[Dict[str, Any]]) -> Optional[str]:
    if not nodes:
        return None
    if not any(node.get("type") == "label" and _is_proverb_label(node.get("text")) for node in nodes if isinstance(node, dict)):
        return None

    text_nodes = [node for node in nodes if isinstance(node, dict) and node.get("type") == "text" and (node.get("style") or "regular") == "regular"]
    if not text_nodes:
        return None
    if len(text_nodes) == 1:
        phrase = _clean_spacing(text_nodes[0].get("text", ""))
        if "," not in phrase:
            return None
        return phrase or None

    dividers = [node for node in nodes if isinstance(node, dict) and node.get("type") == "divider" and (node.get("text") or "").strip()]
    unexpected_divider = any(node.get("text") not in {",", ";"} for node in dividers)
    if unexpected_divider:
        return None

    combined_parts: List[str] = []
    for node in text_nodes:
        combined_parts.append(node.get("text", ""))
    phrase = _clean_spacing(" ".join(part for part in combined_parts if part))
    return phrase or None


_PREPOSITION_PREFIXES = {"в", "во", "на", "по", "к", "ко", "с", "со", "про", "для", "при"}
_IGNORABLE_LABELS = {
    "т.е",
    "т. е",
    "т е",
    "то есть",
    "см",
    "см.",
    "ср",
    "ср.",
    "мед",
    "физ",
    "бот",
    "зоол",
    "анат",
    "ист",
    "хим",
    "прям",
    "прям.",
    "перен",
    "перен.",
    "биол",
    "линг",
    "геол",
    "полит",
}


def _split_leading_adjectives(items: List[str]) -> List[str]:
    result: List[str] = []

    for item in items:
        stripped = _clean_spacing(item)
        if not stripped:
            continue
        parts = stripped.split(" ", 1)
        if (
            len(parts) == 2
            and _looks_like_adjective(parts[0])
            and parts[1]
        ):
            remainder = parts[1].strip()
            if remainder.split(" ", 1)[0].lower() not in _PREPOSITION_PREFIXES:
                result.append(parts[0])
                result.append(remainder)
                continue

        result.append(stripped)

    collapsed = [_collapse_repeated_segment(item) for item in result]
    return _deduplicate(collapsed)


def _normalize_compound_terms(items: List[str]) -> List[str]:
    result: List[str] = []
    for item in items:
        stripped = _clean_spacing(item)
        if not stripped:
            continue
        if " аб`ортус" in stripped:
            parts = stripped.split(" аб`ортус")
            prefix = parts[0].strip()
            if prefix:
                result.append(prefix)
            result.append("аб`ортус")
            continue
        if stripped.startswith("аб") and " аб" in stripped[1:]:
            first, rest = stripped.split(" аб", 1)
            rest_clean = rest.replace("`", "").lower()
            if rest_clean.startswith("орт"):
                result.append(first)
                result.append("аб" + rest)
                continue
        stripped = _REFERENCE_TRAIL_RE.sub("", stripped).rstrip()
        stripped = re.sub(r"\s+сущ\.?$", "", stripped)
        result.append(stripped)
    return _deduplicate(result)


def _expand_prepositional_variations(
    items: List[str],
    base_items: Sequence[str],
) -> List[str]:
    if not items:
        return items

    adjective_tokens: List[str] = []
    for base in base_items:
        token = _first_token(base)
        if token and _looks_like_adjective(token):
            adjective_tokens.append(token)

    extras: List[str] = []
    updated_items: List[str] = []
    for item in items:
        cleaned_item = _clean_spacing(item)
        if not cleaned_item:
            continue
        tokens = cleaned_item.split()
        if not tokens:
            continue
        first = _strip_accents(tokens[0]).lower()
        if first not in _PREPOSITION_PREFIXES:
            updated_items.append(cleaned_item)
            continue

        prep_tokens: List[str] = [tokens[0]]
        rest_tokens: List[str] = []
        for token in tokens[1:]:
            normalized = _strip_accents(token).lower()
            if normalized in _PREPOSITION_PREFIXES and not rest_tokens:
                prep_tokens.append(token)
                continue
            if _looks_like_verb(token) or _looks_like_participle(token):
                rest_tokens = tokens[len(prep_tokens):]
                break
            prep_tokens.append(token)
        else:
            rest_tokens = tokens[len(prep_tokens):]

        prep_phrase = _clean_spacing(" ".join(prep_tokens))
        remainder = _clean_spacing(" ".join(rest_tokens)) if rest_tokens else ""
        if remainder:
            extras.append(remainder)
        for adjective in adjective_tokens:
            extras.append(_clean_spacing(f"{adjective} {prep_phrase}"))

    if not extras:
        return items

    return _deduplicate([*updated_items, *extras])


def _collapse_repeated_segment(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        return value
    length = len(cleaned)
    for size in range(1, length // 2 + 1):
        suffix = cleaned[-size:]
        if cleaned.endswith(suffix * 2):
            return cleaned[:-size].strip()
    return cleaned


class _PhraseBuilder:
    def __init__(self) -> None:
        self.components: List[List[str]] = []
        self._notes: List[str] = []

    def add_text(self, text: str) -> None:
        normalized = _clean_spacing(text.replace("_", " "))
        if not normalized:
            return
        parts = [part.strip() for part in re.split(r",(?![^()]*\))", normalized) if part.strip()]
        if len(parts) > 1:
            parts = _merge_clause_parts(parts)
        if len(parts) > 1:
            self._append_component_options(parts)
        else:
            self._append_component(normalized.rstrip(".,:"))

    def add_alternatives(self, alternatives: Sequence[str]) -> None:
        options = [_clean_spacing(option) for option in alternatives if _clean_spacing(option)]
        if not options:
            return
        if not self.components:
            self.components.append(list(options))
            return
        base_options = self.components[-1]
        seen = {opt for opt in base_options}
        for option in options:
            enriched = _inherit_prose_prefix(base_options, option)
            if enriched not in seen:
                base_options.append(enriched)
                seen.add(enriched)

    def add_note(self, note: str) -> None:
        cleaned = _clean_spacing(note.replace("_", " "))
        if cleaned:
            self._notes.append(cleaned)

    def append_punctuation(self, punct: str) -> None:
        """Присоединяет знак пунктуации к последнему компоненту (для сокращений типа 'что-л.')"""
        if not self.components or not punct:
            return
        last_options = self.components[-1]
        if last_options:
            # Присоединяем пунктуацию к каждому варианту в последнем компоненте
            for i in range(len(last_options)):
                last_options[i] = last_options[i].rstrip() + punct

    def flush(self) -> List[str]:
        return self._flush_into([])

    def _append_component(self, text: str) -> None:
        if not text:
            return
        if not self.components:
            self.components.append([text])
            return
        self.components.append([text])

    def _append_component_options(self, options: Sequence[str]) -> None:
        prepared = [_clean_spacing(option).rstrip(".,:") for option in options]
        prepared = [option for option in prepared if option]
        if not prepared:
            return
        if not self.components:
            self.components.append(list(prepared))
            return
        self.components.append(list(prepared))

    def _flush_into(self, accumulator: List[str]) -> List[str]:
        if not self.components:
            return accumulator
        combos = [""]
        for options in self.components:
            combos = [
                _join_parts(prefix, option)
                for prefix in combos
                for option in options
            ]
        self.components = []
        combos = [_clean_spacing(item) for item in combos if _clean_spacing(item)]
        if combos:
            accumulator.extend(combos)
        return accumulator

    def take_notes(self) -> List[str]:
        notes = self._notes
        self._notes = []
        return notes


def _inherit_prose_prefix(base_options: Sequence[str], candidate: str) -> str:
    if not candidate or " " in candidate:
        return candidate

    for option in reversed(base_options):
        if not option:
            continue
        stripped = option.strip()
        last_space = stripped.rfind(" ")
        if last_space <= 0:
            continue
        prefix = stripped[: last_space + 1]
        combined = _clean_spacing(prefix + candidate)
        if combined:
            return combined
    return candidate


def _extract_note_text(node: Dict) -> str:
    if node.get("content"):
        return _consume_text(node.get("content") or [])
    text = node.get("text", "")
    return _clean_spacing(text.replace("_", " "))


def _extract_note_alternatives(text: str) -> Optional[List[str]]:
    cleaned = _clean_spacing(text.replace("_", " "))
    if not cleaned:
        return None
    if not any(keyword in cleaned.lower() for keyword in ("или", "либо", "/")):
        return None
    def _normalize_option(value: str) -> str:
        stripped = value.strip()
        stripped = stripped.strip(" ,;/:")
        stripped = stripped.strip("()[]{}")
        return _clean_spacing(stripped)

    parts = []
    for raw_part in _ALT_SPLIT_RE.split(cleaned):
        candidate = _normalize_option(raw_part)
        if candidate:
            parts.append(candidate)
    if len(parts) == 1:
        tokens = [_normalize_option(token) for token in parts[0].split() if _normalize_option(token)]
        if len(tokens) > 1:
            parts = tokens
    if not parts:
        return None
    return parts


def _extract_translation_from_explanation(content: Iterable[Dict]) -> Tuple[List[Dict], List[str]]:
    translation_nodes: List[Dict] = []
    notes: List[str] = []
    pending_parenthesis_close = False

    def _attach_to_previous(cleaned: str) -> bool:
        nonlocal pending_parenthesis_close
        if not cleaned:
            return False
        if not translation_nodes:
            return False
        last_node = translation_nodes[-1]
        if last_node.get("type") != "text" or last_node.get("style") != "regular":
            return False
        last_text = last_node.get("text", "")
        if not last_text or not _has_unclosed_parenthesis(last_text):
            return False
        separator = "" if last_text.endswith((" ", "(", "—", "-", "‑")) else " "
        last_node["text"] = f"{last_text.rstrip()}{separator}{cleaned}"
        pending_parenthesis_close = True
        return True

    for node in content:
        if not isinstance(node, dict):
            continue
        node_type = node.get("type")
        if node_type == "text":
            raw_text = node.get("text", "")
            if not raw_text:
                continue
            style = node.get("style", "regular")
            if style == "italic":
                cleaned_note = _clean_spacing(raw_text.replace("_", " "))
                cleaned_note = cleaned_note.strip("()")
                if cleaned_note and _attach_to_previous(cleaned_note):
                    continue
                if cleaned_note:
                    notes.append(cleaned_note)
                continue
            if pending_parenthesis_close:
                stripped = raw_text.lstrip()
                leading_ws_len = len(raw_text) - len(stripped)
                leading_ws = raw_text[:leading_ws_len]
                if stripped.startswith(")"):
                    normalized = leading_ws + stripped
                elif stripped:
                    normalized = f"{leading_ws}) {stripped}"
                else:
                    normalized = f"{leading_ws})"
                raw_text = normalized
                pending_parenthesis_close = False
            translation_nodes.append(
                {
                    "type": "text",
                    "style": "regular",
                    "text": raw_text,
                    "kind": node.get("kind"),
                }
            )
        elif node_type == "divider":
            divider_text = node.get("text", "")
            if divider_text:
                translation_nodes.append(
                    {
                        "type": "divider",
                        "text": divider_text,
                        "kind": node.get("kind"),
                    }
                )
        elif node_type == "note":
            note_text = _extract_note_text(node)
            if note_text:
                notes.append(note_text)

    if pending_parenthesis_close and translation_nodes:
        last = translation_nodes[-1]
        if last.get("type") == "text" and last.get("style") == "regular":
            last_text = last.get("text", "")
            if last_text and not last_text.rstrip().endswith(")"):
                last["text"] = f"{last_text.rstrip()})"
    translation_nodes = _normalize_labelled_content(translation_nodes)
    cleaned_nodes: List[Dict] = []
    for item in translation_nodes:
        if item.get("type") == "text":
            text = _clean_spacing(item.get("text", ""))
            if not text:
                continue
            if text and text[0] in {";", ",", ":"}:
                text = text[1:].lstrip()
            new_item = dict(item)
            new_item["text"] = text
            cleaned_nodes.append(new_item)
        else:
            cleaned_nodes.append(item)

    substantive = False
    for node in cleaned_nodes:
        if node.get("type") == "text":
            payload = node.get("text", "")
            if payload and not payload.lstrip().startswith("="):
                substantive = True
                break

    if not substantive and cleaned_nodes:
        for node in cleaned_nodes:
            if node.get("type") == "text":
                text = node.get("text", "").lstrip()
                if text.startswith("="):
                    text = text.lstrip("= ")
                if text:
                    notes.append(text)
        cleaned_nodes = []

    return cleaned_nodes, notes


def _clone_nodes(nodes: Iterable[Dict]) -> List[Dict]:
    return [copy.deepcopy(node) for node in nodes if isinstance(node, dict)]


def _expand_parenthetical_forms(phrase: str) -> List[str]:
    phrase = phrase.replace("_", " ")

    def _recurse(text: str) -> List[str]:
        start = text.find("(")
        if start == -1:
            return [_clean_spacing(text)]
        end = _find_matching_parenthesis(text, start)
        if end == -1:
            return [_clean_spacing(text)]

        before = text[:start]
        inside = text[start + 1 : end]
        after = text[end + 1 :]

        inside_clean = inside.strip()
        if not inside_clean:
            return _recurse(before + after)
        if "=" in inside_clean:
            return _recurse(before + after)

        lower = inside_clean.lower()
        if any(keyword in lower for keyword in ("или", "либо")):
            alternatives = [
                part.strip(" ,;/")
                for part in _ALT_SPLIT_RE.split(inside_clean)
                if part.strip(" ,;/")
            ]
            before_trim = before.rstrip()
            match = re.search(r"(\S+)$", before_trim)
            if match:
                prefix = before_trim[: match.start()].rstrip()
                base_word = match.group(1)
                rest = after
                rest_lstrip = rest.lstrip()
                needs_space = (
                    bool(rest)
                    and rest[0].isspace()
                    and rest_lstrip
                )
                variants: List[str] = []
                for replacement in [base_word] + alternatives:
                    prefix_part = prefix
                    if prefix_part and not prefix_part.endswith((" ", "-", "—", "/")):
                        prefix_part += " "
                    new_text = prefix_part + replacement
                    if needs_space and not new_text.endswith((" ", "-", "—", "/")):
                        new_text += " "
                    if rest and not rest.startswith((" ", ",", ".", ";", ":", ")")):
                        new_text += " "
                    new_text += rest_lstrip
                    variants.extend(_recurse(new_text))
                return variants

        if " " not in inside_clean and "," not in inside_clean:
            before_trimmed = before.rstrip()
            after_trimmed = after.lstrip()

            needs_space_between = (
                bool(before_trimmed)
                and bool(after_trimmed)
                and not before_trimmed.endswith((" ", "-", "—", "‑", "/"))
                and not after_trimmed.startswith((",", ";", ":", ".", ")", "—", "-", "‑"))
            )

            if needs_space_between:
                without = f"{before_trimmed} {after_trimmed}"
            else:
                without = before_trimmed + after_trimmed

            after_without_space = after
            had_leading_space = False
            if after and after[0].isspace():
                after_without_space = after.lstrip()
                had_leading_space = True
            insert_space = (
                had_leading_space
                and bool(after_without_space)
                and not after_without_space.startswith((",", ";", ":", ".", ")", "—", "-", "‑"))
            )
            with_opt = before + inside_clean + (" " if insert_space else "") + after_without_space
            return _recurse(without) + _recurse(with_opt)

        preserved_before = before
        if preserved_before and not preserved_before.endswith((" ", "-", "—", "‑", "/")):
            preserved_before += " "
        preserved_after = after
        if preserved_after and preserved_after[0].isspace():
            preserved_after = preserved_after.lstrip()
            joiner = " "
        else:
            joiner = "" if not preserved_after or preserved_after.startswith(
                (",", ";", ":", ".", ")", "—", "-", "‑")
            ) else " "

        preserved = f"{preserved_before}({inside_clean}){joiner}{preserved_after or ''}"
        return _recurse(preserved)

    return _deduplicate([_clean_spacing(item) for item in _recurse(phrase)])


def _find_matching_parenthesis(text: str, start: int) -> int:
    depth = 0
    for index in range(start, len(text)):
        char = text[index]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index
    return -1


def _join_parts(prefix: str, part: str) -> str:
    prefix = prefix.strip()
    part = part.strip()
    if not prefix:
        return part
    if not part:
        return prefix
    if part[0] in ",.;:)" or prefix.endswith(("(", "-", "—", "/")):
        return prefix + part
    return f"{prefix} {part}"


def _deduplicate(items: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    result: List[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _has_unclosed_parenthesis(value: str) -> bool:
    if not value:
        return False
    return value.count("(") > value.count(")")


def _trim_trailing_parenthesis(nodes: List[Dict]) -> None:
    if not nodes:
        return
    for node in reversed(nodes):
        if node.get("type") != "text":
            continue
        text = node.get("text", "") or ""
        if _has_unclosed_parenthesis(text) and "(" in text:
            pivot = text.rfind("(")
            trimmed = text[:pivot].rstrip()
            node["text"] = trimmed
            break


def _is_pos_marker(items: Sequence[str]) -> bool:
    return bool(items) and all(item.startswith("{") and item.endswith("}") for item in items)


def _block_indicates_continuation(block: Dict) -> bool:
    content = block.get("content") or []
    for node in reversed(content):
        node_type = node.get("type")
        if node_type == "divider":
            text = (node.get("text") or "").strip()
            return text in {",", ":"}
        if node_type == "text":
            raw_text = node.get("text", "")
            text = _clean_spacing(raw_text)
            if text:
                if raw_text.strip().startswith("(") or text.startswith("или "):
                    return True
                return text.endswith((",", "-", "—"))
    return False


def _strip_accents(text: str) -> str:
    return text.translate({ord("`"): None, ord("´"): None, ord("'" ): None})


def _first_token(text: str) -> str:
    return text.strip().split()[0]


def _looks_like_verb(text: str) -> bool:
    stripped = _strip_accents(text).lower()
    endings = ("ться", "сь", "ст", "сть", "сти", "ть", "ти", "чь", "ся")
    return any(stripped.endswith(ending) for ending in endings)


def _looks_like_adjective(text: str) -> bool:
    stripped = _strip_accents(text).lower()
    endings = (
        "ая",
        "яя",
        "ий",
        "ый",
        "ой",
        "ое",
        "ее",
        "ые",
        "ие",
        "ний",
        "ный",
        "ской",
        "ский",
        "льный",
        "тельный",
        "чный",
        "ческий",
        "оватый",
        "истый",
    )
    return any(stripped.endswith(ending) for ending in endings)


_PREPOSITION_PREFIXES = {
    "в",
    "во",
    "из",
    "изо",
    "к",
    "ко",
    "по",
    "на",
    "за",
    "о",
    "об",
    "обо",
    "при",
    "под",
    "подо",
    "над",
    "надо",
    "с",
    "со",
    "от",
    "до",
    "для",
    "у",
    "между",
    "перед",
    "через",
    "из-за",
    "около",
    "про",
    "внутри",
    "вне",
}


def _is_preposition_prefix(token: str) -> bool:
    if not token:
        return False
    return token in _PREPOSITION_PREFIXES


def _expand_cross_product(items: List[str]) -> List[str]:
    multi = [item for item in items if " " in item]
    singles = [item for item in items if " " not in item]
    if not multi or not singles:
        return items

    suffix_to_prefixes: dict[str, set[str]] = defaultdict(set)
    for phrase in multi:
        tokens = phrase.split()
        if len(tokens) < 2:
            continue
        prefix = " ".join(tokens[:-1])
        suffix = tokens[-1]
        suffix_to_prefixes[suffix].add(prefix)

    if len(suffix_to_prefixes) != 1:
        return items

    suffix, prefixes = next(iter(suffix_to_prefixes.items()))

    adjective_candidates = [
        item for item in items if " " not in item and _looks_like_adjective(item)
    ]
    if len(prefixes) >= 2 and adjective_candidates:
        suffix_options = [suffix] + adjective_candidates
        combinations: List[str] = []
        for prefix in sorted(prefixes):
            for option in suffix_options:
                combinations.append(_clean_spacing(f"{prefix} {option}"))
        return _deduplicate(combinations)

    if adjective_candidates and len(adjective_candidates) > 1 and len(multi) > 1:
        combos = [
            _clean_spacing(f"{adj} {suffix}") for adj in adjective_candidates
        ]
        return _deduplicate([*items, *combos])

    return items


def _expand_suffix_appending(items: List[str]) -> List[str]:
    singles = [
        item for item in items if " " not in item and not item.strip().startswith("~")
    ]
    multi_candidates = [
        item for item in items if " " in item and not item.strip().startswith("~")
    ]
    extra_items: List[str] = []

    for candidate in multi_candidates:
        tokens = candidate.split()
        if len(tokens) < 2:
            continue
        for suffix_len in range(1, len(tokens)):
            prefix_tokens = tokens[:-suffix_len]
            suffix_tokens = tokens[-suffix_len:]
            if len(prefix_tokens) != 1:
                continue
            if len(suffix_tokens) < 2:
                continue
            base_word = prefix_tokens[0]
            first_suffix_token = _strip_accents(suffix_tokens[0]).lower()
            if not _is_preposition_prefix(first_suffix_token):
                continue
            suffix_text = _clean_spacing(" ".join(suffix_tokens))

            if _looks_like_adjective(base_word):
                adjective_candidates = [
                    item
                    for item in singles
                    if _looks_like_adjective(_first_token(item))
                ]
                if adjective_candidates:
                    if len(adjective_candidates) >= 1:
                        for adjective in adjective_candidates:
                            extra_items.append(
                                _clean_spacing(f"{adjective} {suffix_text}")
                            )
            else:
                continue

    if not extra_items:
        return items

    combined = _deduplicate([*items, *extra_items])
    singles_set = {item for item in items if " " not in item}
    if any(" " in item for item in extra_items):
        combined = [
            item for item in combined if (" " in item) or (item not in singles_set)
        ]
    return combined


def _ru_segments_to_content(segments: Iterable[Dict]) -> List[Dict]:
    content: List[Dict] = []
    for seg in segments:
        kind = seg.get("kind")
        text = seg.get("text")
        if not text:
            continue
        if kind == "label":
            content.append({"type": "label", "text": text})
        elif kind == "term":
            content.append({"type": "text", "style": "regular", "text": text})
        elif kind in {"near_divider", "far_divider", "sentence_divider", "phrase_divider"}:
            content.append({"type": "divider", "text": text, "kind": kind})
        elif kind == "note":
            content.append(
                {
                    "type": "note",
                    "content": [{"type": "text", "style": "regular", "text": text}],
                }
            )
        elif kind in {"reference", "link"}:
            content.append({"type": "text", "style": "regular", "text": text})
        else:
            content.append({"type": "text", "style": "regular", "text": text})
    return content


def _strip_accents(text: str) -> str:
    translations = {ord("`"): None, ord("´"): None, ord("'"): None}
    return text.translate(translations)


def _first_token(text: str) -> str:
    return text.strip().split()[0]


def _looks_like_verb(text: str) -> bool:
    stripped = _strip_accents(text).lower()
    endings = ("ться", "сь", "ст", "сть", "сти", "ть", "ти", "чь", "ся")
    return any(stripped.endswith(ending) for ending in endings)


def _strip_trailing_punctuation(value: str) -> str:
    return value.rstrip(" ,.;:)")


def _looks_like_participle(text: str) -> bool:
    stripped = _strip_accents(text).lower()
    endings = (
        "щий",
        "щая",
        "щее",
        "щие",
        "щийся",
        "щаяся",
        "щееся",
        "щиеся",
        "ющий",
        "ющая",
        "ющее",
        "ющие",
        "ющийся",
        "ющаяся",
        "ющееся",
        "ющиеся",
        "имый",
        "имая",
        "имое",
        "имые",
        "омый",
        "омая",
        "омое",
        "омые",
    )
    return any(stripped.endswith(ending) for ending in endings)


def _is_meaningful_item(value: str) -> bool:
    if not value:
        return False
    stripped = value.strip()
    return stripped not in {",", ";", ".", ")", "("}


_OPTIONAL_PREFIX_SPACE_RE = re.compile(r"\(([^)]+)\)\s+([^\s,;:.()]+)")


def _compress_optional_prefix_spacing(value: str) -> str:
    def _should_collapse(candidate: str) -> bool:
        if not candidate:
            return False
        normalized = _strip_accents(candidate).lower()
        if any(char in candidate for char in " ,.;:/"):
            return False
        if len(normalized) > 4:
            return False
        return True

    def _replace(match: re.Match[str]) -> str:
        inside = match.group(1).strip()
        tail = match.group(2)
        if not _should_collapse(inside):
            return match.group(0)
        return f"({inside}){tail}"

    return _OPTIONAL_PREFIX_SPACE_RE.sub(_replace, value)


def _expand_inline_dividers(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    for node in nodes:
        if node.get("type") == "text":
            raw_text = node.get("text") or ""
            if ";" in raw_text:
                parts = raw_text.split(";")
                for idx, part in enumerate(parts):
                    trimmed = part.strip()
                    if trimmed:
                        new_node = dict(node)
                        new_node["text"] = _compress_optional_prefix_spacing(trimmed)
                        result.append(new_node)
                    if idx != len(parts) - 1:
                        result.append({"type": "divider", "text": ";", "kind": "far_divider"})
                continue
        if node.get("type") == "text":
            adjusted = dict(node)
            adjusted["text"] = _compress_optional_prefix_spacing(node.get("text") or "")
            result.append(adjusted)
        else:
            result.append(node)
    return result


def _looks_like_adjective(text: str) -> bool:
    stripped = _strip_accents(text).lower()
    endings = (
        "ая",
        "яя",
        "ий",
        "ый",
        "ой",
        "ое",
        "ее",
        "ые",
        "ие",
        "ний",
        "ный",
        "ской",
        "ский",
        "льный",
        "тельный",
        "чный",
        "ческий",
        "оватый",
        "истый",
    )
    return any(stripped.endswith(ending) for ending in endings)


def _consume_text(content: Iterable[Dict]) -> str:
    parts: List[str] = []
    for node in content:
        if node.get("type") == "text":
            parts.append(node.get("text", ""))
        elif node.get("type") == "note":
            inner = _consume_text(node.get("content") or [])
            if inner:
                parts.append(inner)
    return _clean_spacing("".join(parts))


_SPACES_RE = re.compile(r"\s+")


def _clean_spacing(value: str) -> str:
    collapsed = _SPACES_RE.sub(" ", value or "")
    collapsed = collapsed.replace(" ,", ",").replace(" .", ".")
    return collapsed.strip(" ,")


def collect_translation_phrases(
    review: TranslationReview,
    manual_phrases: Optional[Sequence[str]] = None,
) -> List[str]:
    phrases: List[str] = []
    for group in review.groups:
        phrases.extend(group.items)
    for item in manual_phrases or []:
        cleaned = _clean_spacing(item)
        if cleaned and cleaned not in phrases:
            phrases.append(cleaned)
    return phrases
def _normalize_labelled_content(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    for node in nodes:
        if node.get("type") == "label":
            raw_label = node.get("text", "")
            normalized_label = _normalize_label_text(raw_label)
            if normalized_label in _IGNORABLE_LABELS:
                continue
        result.append(node)
    return result


def _normalize_label_text(value: str) -> str:
    if not value:
        return ""
    cleaned = value.strip().rstrip(".")
    cleaned = cleaned.replace("_", " ")
    cleaned = _clean_spacing(cleaned)
    return cleaned.lower()
