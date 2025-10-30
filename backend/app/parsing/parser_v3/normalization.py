"""Utilities for normalising parsed articles into the v3 JSON shape."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .legacy_bridge import legacy_parser
from . import text_parser  # Новый чистый парсер

register_label = getattr(legacy_parser, 'register_label', lambda _text: None)

# Ensure legacy parser knows about shortenings when running inside v3 pipeline
try:
    if hasattr(legacy_parser, 'KNOWn_SHORTENINGS'):
        pass
except AttributeError:
    pass
try:
    if not getattr(legacy_parser, 'KNOWN_SHORTENINGS', None):
        legacy_parser.KNOWN_SHORTENINGS = legacy_parser.load_shortenings()
    if hasattr(legacy_parser, 'LOGGED_UNKNOWN_LABELS'):
        legacy_parser.LOGGED_UNKNOWN_LABELS.clear()
except Exception:
    pass

PREFERRED_ORDER: List[str] = [
    "type",
    "number",
    "mode",
    "text",
    "targets",
    "raw_form",
    "lemmas",
    "official_mark",
    "homonym",
    "content",
    "children",
    "eo",
    "eo_raw",
    "eo_expanded",
    "sentence_divider",
]

REFERENCE_LABELS = {
    "see": {"default_text": "см."},
    "compare": {"default_text": "ср."},
    "synonym": {"default_text": "="},
}

REFERENCE_LABEL_MODES = {
    "см": "see",
    "см.": "see",
    "ср": "compare",
    "ср.": "compare",
    "=": "synonym",
}

DIVIDER_KIND_BY_CHAR = {
    ',': 'near_divider',
    ';': 'far_divider',
    '.': 'sentence_divider',
    ':': 'phrase_divider',
}


def _detect_mixed_dividers(content: Iterable[Dict[str, Any]]) -> Tuple[bool, bool]:
    has_near = False
    has_far = False
    for item in content:
        if not isinstance(item, dict) or item.get("type") != "divider":
            continue
        divider_text = item.get("text", "")
        kind = item.get("kind") or DIVIDER_KIND_BY_CHAR.get(divider_text)
        if kind == "near_divider":
            has_near = True
        elif kind == "far_divider":
            has_far = True
    return has_near, has_far


def _reconstruct_ru_text_from_content(content: Iterable[Dict[str, Any]]) -> str:
    """Best-effort reconstruction of the Russian translation string."""

    pieces: List[str] = []

    def _needs_space(before: str, next_text: str) -> bool:
        if not before:
            return False
        if before[-1].isspace():
            return False
        if before[-1] in {',', ';', ':', '(', '—', '-', '‑'}:
            return False
        if not next_text:
            return False
        if next_text[0] in {',', ';', ':', '.', ')'}:
            return False
        return True

    buffer = ""
    for item in content:
        if not isinstance(item, dict):
            continue
        item_type = item.get("type")
        text = item.get("text", "")
        if not text:
            continue
        if item_type == "label":
            continue
        if item_type == "divider":
            buffer += text
            if text in {',', ';', ':'}:
                if not buffer.endswith(' '):
                    buffer += ' '
            continue
        if item_type == "text":
            if _needs_space(buffer, text):
                buffer += " "
            buffer += text
            continue
        # Fallback to appending raw text for any other node
        if _needs_space(buffer, text):
            buffer += " "
        buffer += text

    pieces.append(buffer.strip())
    return pieces[0] if pieces else ""


def _split_link_notation(raw: str) -> Tuple[str, Optional[str]]:
    value = raw.strip()
    if '@' not in value:
        return value, None
    parts = [part.strip() for part in value.split('@') if part.strip()]
    if len(parts) >= 3:
        parts = parts[1:]
    if not parts:
        return value, None
    target = parts[0]
    display = '@'.join(parts[1:]).strip() if len(parts) > 1 else None
    return target, display or None


def _contains_cyrillic(text: str) -> bool:
    return any('\u0400' <= ch <= '\u04FF' for ch in text)


def _merge_regular_text_with_spacing(left: str, right: str) -> str:
    if not left:
        return right.lstrip()
    if not right:
        return left
    left_trimmed = left.rstrip()
    right_trimmed = right.lstrip()
    if not left_trimmed:
        return right_trimmed
    if not right_trimmed:
        return left_trimmed
    left_guard = left_trimmed[-1]
    right_guard = right_trimmed[0]
    needs_space = (
        left_guard not in {" ", "-", "—", "‑", "/", "("}
        and right_guard not in {" ", ",", ";", ":", ".", ")", "!", "?", "—"}
    )
    merged = left_trimmed
    if needs_space:
        merged += " "
    merged += right_trimmed
    return merged


def _normalize_spacing(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _merge_illustration_continuations(block: Dict[str, Any]) -> None:
    if block.get("type") != "illustration":
        return
    children = block.get("children", []) or []
    if not children:
        return

    merged_children: List[Dict[str, Any]] = []
    for child in children:
        if child.get("type") == "illustration" and not child.get("eo"):
            addition_text = ""
            addition_note: Optional[str] = None
            addition_divider: Optional[str] = None
            for item in child.get("content", []) or []:
                item_type = item.get("type")
                if item_type == "text":
                    addition_text += item.get("text", "")
                elif item_type == "note":
                    addition_note = item.get("text", "")
                elif item_type == "divider":
                    addition_divider = item.get("text", "")

            addition_text = addition_text.strip()
            if addition_text:
                ru_segments = block.setdefault("ru_segments", [])
                for seg in reversed(ru_segments):
                    if seg.get("kind") == "term":
                        seg["text"] = (seg.get("text", "") + " " + addition_text).strip()
                        break
                else:
                    ru_segments.append({"kind": "term", "text": addition_text})

            if addition_note:
                clean_note = addition_note.strip().strip('_')
                if clean_note:
                    if not clean_note.startswith('('):
                        clean_note = f'({clean_note})'
                    block.setdefault("ru_segments", []).append({
                        "kind": "note",
                        "text": clean_note,
                        "style": "italic",
                    })

            if addition_divider:
                divider_kind = DIVIDER_KIND_BY_CHAR.get(addition_divider, "divider")
                block.setdefault("ru_segments", []).append({"kind": divider_kind, "text": addition_divider})
        else:
            merged_children.append(child)

    if merged_children:
        block["children"] = merged_children
    else:
        block.pop("children", None)


def normalize_article(
    article: Dict[str, Any],
    *,
    template_name: Optional[str] = None,
    collect_sections: bool = False,
) -> Dict[str, Any]:
    """Return a normalised copy of ``article``."""

    normalised_article = dict(article)
    body = article.get("body", []) or []

    transformed_body: List[Dict[str, Any]] = [
        _transform_block(block) for block in body
    ]

    transformed_body = _attach_orphan_references(transformed_body)
    transformed_body = _merge_plain_russian_illustrations(transformed_body)

    trailing_sentence = ""
    if transformed_body:
        last_block = transformed_body[-1]
        trailing_sentence = last_block.pop("_trailing_sentence", "")
        if not trailing_sentence and last_block.get("type") == "headword":
            trailing_sentence = _collect_trailing_sentence_from_headword(last_block)

    normalised_article["body"] = transformed_body

    if trailing_sentence:
        normalised_article["body"].append({"type": "sentence_divider", "text": trailing_sentence})

    if template_name:
        normalised_article.setdefault("meta", {})["template"] = template_name

    if collect_sections:
        normalised_article.setdefault("meta", {})["sections"] = _build_sections(transformed_body)

    base_variants = []
    if normalised_article.get("headword"):
        base_variants = _expand_headword_node(normalised_article["headword"], parent_bases=None)
    _expand_headwords_in_list(normalised_article.get("body", []), base_variants)

    top_context = normalised_article.get("headword", {}).get("_tilde_context", {}) if normalised_article.get("headword") else {}
    _expand_tilde_in_blocks(normalised_article.get("body", []), top_context)
    _cleanup_tilde_context(normalised_article)

    return normalised_article


def _transform_block(block: Dict[str, Any]) -> Dict[str, Any]:
    block_copy = dict(block)
    block_type = block_copy.get("type")

    if block_type == "reference":
        _normalize_reference(block_copy)
    if block_copy.get("content"):
        block_copy["content"] = _normalize_segments(block_copy["content"])

    if block_type == "note":
        block_copy = _normalize_note(block_copy)
    elif block_type == "idiomatics":
        block_copy = _normalize_idiomatics(block_copy)
    elif block_type == "translation":
        block_copy = _normalize_translation(block_copy)
    elif block_type == "explanation":
        block_copy = _normalize_explanation(block_copy)
    elif block_type == "headword":
        block_copy = _normalize_headword(block_copy)

    if block_copy.get("children"):
        block_copy["children"] = [_transform_block(child) for child in block_copy["children"]]

    return _reorder_keys(block_copy)


def _normalize_segments(segments: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalised: List[Dict[str, Any]] = []
    for segment in segments:
        if not isinstance(segment, dict):
            normalised.append(segment)
            continue
        normalised.append(segment)
    return normalised


def _normalize_reference(block: Dict[str, Any]) -> None:
    mode = block.get("mode")
    config = REFERENCE_LABELS.get(mode or "")
    if config and not block.get("text"):
        block["text"] = config["default_text"]

    if mode == "synonym":
        targets = block.get("targets") or []
        if targets:
            joined = ", ".join(f"<{target}>" for target in targets)
            block["text"] = f"(= {joined})"
        else:
            block["text"] = "(=)"


def _normalize_note(block: Dict[str, Any]) -> Dict[str, Any]:
    new_block = dict(block)
    new_content: List[Dict[str, Any]] = []
    for item in block.get("content", []):
        if isinstance(item, dict) and item.get("type") == "explanation":
            new_content.append({"type": "illustration", "content": item.get("content", [])})
        else:
            new_content.append(item if isinstance(item, dict) else item)
    new_block["content"] = new_content

    children = block.get("children") or []
    if children:
        new_children: List[Dict[str, Any]] = []
        for child in children:
            if child.get("type") == "explanation":
                new_children.append({"type": "illustration", "content": child.get("content", [])})
            else:
                new_children.append(child)
        new_block["children"] = new_children
    else:
        new_block.pop("children", None)

    return new_block


def _normalize_idiomatics(block: Dict[str, Any]) -> Dict[str, Any]:
    new_block = dict(block)
    extra_content: List[Dict[str, Any]] = []
    remaining_children: List[Dict[str, Any]] = []
    for child in block.get("children", []) or []:
        if child.get("type") == "explanation":
            extra_content.extend(child.get("content", []))
        else:
            remaining_children.append(child)
    if extra_content:
        new_block.setdefault("content", []).extend(extra_content)
    if remaining_children:
        new_block["children"] = remaining_children
    else:
        new_block.pop("children", None)
    return new_block


def _normalize_translation(block: Dict[str, Any]) -> Dict[str, Any]:
    new_block = dict(block)
    content = block.get("content", []) or []
    normalized_content = _normalize_segments(content)

    seen_near, seen_far = _detect_mixed_dividers(normalized_content)

    if seen_near and seen_far:
        raw_ru_text = _reconstruct_ru_text_from_content(normalized_content)
        meta = new_block.setdefault("meta", {})
        if raw_ru_text:
            meta["raw_ru_text"] = raw_ru_text
        new_block["ru_requires_review"] = True
    new_block["content"] = normalized_content
    ru_segments = _build_ru_segments_from_translation(normalized_content)
    if ru_segments:
        prefix: List[Dict[str, Any]] = []
        for item in normalized_content:
            if item.get("type") == "text" and item.get("style") == "regular":
                continue
            if (
                item.get("type") == "text"
                and item.get("style") == "italic"
                and _should_include_italic_segment(item.get("text", "").strip())
            ):
                continue
            prefix.append(item)
        segment_nodes, variant_terms = _convert_ru_segments_to_content(ru_segments)
        new_block["content"] = prefix + segment_nodes
        if variant_terms:
            meta = new_block.setdefault("meta", {})
            search_terms = meta.setdefault("search_terms", [])
            for term in variant_terms:
                if term not in search_terms:
                    search_terms.append(term)
        div_kinds = {seg.get("kind") for seg in ru_segments if seg.get("kind") and "divider" in seg.get("kind")}
        if {"near_divider", "far_divider"}.issubset(div_kinds):
            new_block["ru_requires_review"] = True
    else:
        new_block["content"] = normalized_content

    return new_block


def _normalize_explanation(block: Dict[str, Any]) -> Dict[str, Any]:
    new_block = dict(block)
    segments = _normalize_segments(block.get("content", []))
    reference_block = _convert_segments_to_reference(segments)
    if reference_block:
        return reference_block
    new_block["content"] = segments
    return new_block


def _normalize_headword(block: Dict[str, Any]) -> Dict[str, Any]:
    new_block = dict(block)
    children = new_block.get("children") or []
    if children:
        last_child = children[-1]
        if last_child.get("type") in {"explanation", "translation"}:
            trailing = _strip_sentence_ending(last_child.get("content", []))
            if trailing:
                new_block["_trailing_sentence"] = trailing
    return new_block


def _build_ru_segments_from_translation(content: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
    filtered_items: List[Dict[str, Any]] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        item_type = item.get("type")
        if item_type == "divider":
            divider_text = item.get("text", "")
            if divider_text:
                filtered_items.append(
                    {
                        "type": "divider",
                        "text": divider_text,
                        "kind": item.get("kind"),
                    }
                )
            continue
        if item_type != "text":
            continue

        style = item.get("style", "regular")
        raw_text = item.get("text", "")
        if not raw_text:
            continue
        text = raw_text.strip()
        if not text:
            continue
        if style == "regular":
            if text in {"(", ")"}:
                continue
            filtered_items.append(
                {
                    "type": "text",
                    "style": "regular",
                    "text": text,
                }
            )
        elif style == "italic":
            if _should_include_italic_segment(text):
                filtered_items.append(
                    {
                        "type": "text",
                        "style": "italic",
                        "text": text,
                    }
                )

    if not filtered_items:
        return None

    combined_text = _reconstruct_ru_text_from_content(filtered_items)
    if not combined_text:
        return None

    # Используем новый text_parser
    parts = text_parser.parse_rich_text(combined_text, preserve_punctuation=False)
    segments = text_parser.split_ru_segments(parts)
    return segments or None


_ITALIC_NOTE_PATTERN = re.compile(r"\b(?:или(?:\s+же)?|либо)\b", re.IGNORECASE)
_INLINE_REFERENCE_NOTE_PATTERN = re.compile(r"^\(=\s*<\s*([^>]+)$")


def _should_include_italic_segment(text: str) -> bool:
    if not text:
        return False
    if text.startswith("(") or text.endswith(")"):
        return True
    if _ITALIC_NOTE_PATTERN.search(text):
        return True
    return False


def _convert_ru_segments_to_content(segments: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    converted: List[Dict[str, Any]] = []
    variants: List[str] = []
    i = 0
    while i < len(segments):
        segment = segments[i]
        kind = segment.get("kind")
        text = segment.get("text", "")

        if kind == "note":
            raw_note = (text or "").strip()
            if not raw_note:
                i += 1
                continue
            inline_match = _INLINE_REFERENCE_NOTE_PATTERN.match(raw_note)
            if inline_match:
                next_seg = segments[i + 1] if i + 1 < len(segments) else None
                if next_seg and next_seg.get("kind") == "term":
                    suffix_raw = (next_seg.get("text") or "").strip()
                    if suffix_raw:
                        target_prefix = inline_match.group(1).strip()
                        needs_parenthesis = not target_prefix.endswith(")")
                        suffix_clean = suffix_raw
                        if suffix_clean.endswith(">)"):
                            suffix_clean = suffix_clean[:-2]
                        elif suffix_clean.endswith(")"):
                            suffix_clean = suffix_clean[:-1]
                        closing_parenthesis = ")" if needs_parenthesis else ""
                        suffix_clean = suffix_clean.rstrip(" ,.;:")
                        combined_target = _normalize_spacing(
                            f"{target_prefix}{closing_parenthesis}{suffix_clean}"
                        )
                        display = f"(= <{combined_target}>)" if combined_target else "(=)"
                        if (
                            converted
                            and converted[-1].get("type") == "text"
                            and converted[-1].get("style") == "regular"
                        ):
                            base_text = converted[-1].get("text", "")
                            spacer = "" if base_text.endswith((" ", "(", "—", "-", "‑")) else " "
                            converted[-1]["text"] = f"{base_text}{spacer}{display}"
                        else:
                            converted.append({"type": "text", "style": "regular", "text": display})
                        if combined_target:
                            variants.append(combined_target)
                        i += 2
                        continue
            has_parens = raw_note.startswith('(') and raw_note.endswith(')')
            note_core = raw_note[1:-1].strip() if has_parens else raw_note
            display_note = raw_note if has_parens else f"({raw_note})"

            prev_seg = segments[i - 1] if i > 0 else None
            if prev_seg and prev_seg.get("kind") == "term" and converted:
                last_node = converted[-1]
                if last_node.get("type") == "text" and last_node.get("style") == "regular":
                    text_before = last_node.get("text", "")
                    if text_before and not text_before.endswith((' ', '(', '—', '-', '‑')):
                        if display_note.startswith("("):
                            last_node["text"] = text_before + display_note
                        else:
                            last_node["text"] = text_before + " " + display_note
                    else:
                        last_node["text"] = text_before + display_note
                    term_base = prev_seg.get("text") or ""
                    if term_base:
                        variants.append(term_base)
                    if term_base or note_core:
                        if term_base and note_core and _looks_like_inline_suffix(note_core):
                            combined_variant = term_base + note_core
                        else:
                            combined_variant = " ".join(
                                filter(None, [term_base, note_core])
                            ).strip()
                        if combined_variant:
                            variants.append(combined_variant)
                    i += 1
                    continue

            next_seg = segments[i + 1] if i + 1 < len(segments) else None
            if next_seg and next_seg.get("kind") == "term":
                term_text = next_seg.get("text") or ""
                combined_display = display_note if display_note else ""
                if term_text:
                    spacer = ""
                    if combined_display:
                        last_char = combined_display[-1]
                        first_char = term_text[0]
                        if note_core and note_core[-1] in {'-', '—', '‑'}:
                            spacer = ""
                        elif last_char not in {'-', '—', '‑'} and first_char not in {'-', '—', '‑', ',', ';', ':', '.', ')'}:
                            spacer = " "
                    combined_display = combined_display + spacer + term_text if combined_display else term_text
                converted.append({"type": "text", "style": "regular", "text": combined_display})
                if note_core or term_text:
                    combined_variant = " ".join(filter(None, [note_core, term_text])).strip()
                    if combined_variant:
                        variants.append(combined_variant)
                if term_text:
                    variants.append(term_text)
                i += 2
                continue

            converted.append({"type": "text", "style": "regular", "text": display_note})
            if note_core:
                variants.append(note_core)
            i += 1
            continue

        if kind == "term":
            converted.append({"type": "text", "style": "regular", "text": text})
        elif kind == "label":
            converted.append({"type": "label", "text": text})
            register_label(text)
        elif kind and "divider" in kind:
            node = {"type": "divider", "kind": kind, "text": text}
            converted.append(node)
        elif kind == "reference":
            node = {"type": "reference", "text": text}
            if segment.get("mode"):
                node["mode"] = segment["mode"]
            converted.append(node)
        elif kind == "link":
            target_raw = segment.get("target") or text
            target, display = _split_link_notation(target_raw)
            node = {
                "type": "link",
                "text": display or text or target,
                "target": target,
            }
            if segment.get("mode"):
                node["mode"] = segment["mode"]
            converted.append(node)
        else:
            fallback = {"type": "text", "style": "regular", "text": text}
            if kind:
                fallback["kind"] = kind
            converted.append(fallback)
        i += 1

    # Convert standalone notes to italic text with parentheses
    for idx, item in enumerate(converted):
        if item.get("type") == "text" and item.get("style") == "regular" and item.get("kind") == "note":
            clean = item.get("text", "").strip().strip('_')
            if not clean:
                continue
            display = clean
            if not display.startswith('('):
                display = f"({display})"
            else:
                display = display
            if not display.startswith(' '):
                display = ' ' + display
            converted[idx] = {"type": "text", "style": "italic", "text": display}

    merged: List[Dict[str, Any]] = []
    idx = 0
    while idx < len(converted):
        item = converted[idx]
        if (
            idx + 1 < len(converted)
            and item.get("type") == "text"
            and item.get("style") == "regular"
            and converted[idx + 1].get("type") == "text"
            and converted[idx + 1].get("style") == "regular"
        ):
            first_text = item.get("text", "")
            second_text = converted[idx + 1].get("text", "")
            if first_text.endswith(")") and "(" in first_text:
                second_start = second_text[:1]
                if second_text and second_start not in {" ", ",", ";", ":", ".", ")"}:
                    combined = _merge_regular_text_with_spacing(first_text, second_text)
                    merged.append({"type": "text", "style": "regular", "text": combined})
                    variants.extend(_expand_pattern(combined))
                    idx += 2
                    continue
        merged.append(item)
        idx += 1

    converted = merged
    return converted, _unique_preserve_order(variants)


def _looks_like_inline_suffix(text: str) -> bool:
    stripped = text.translate({ord("`"): None, ord("´"): None, ord("'"): None}).replace("-", "")
    return bool(stripped) and stripped.isalpha()


def _convert_segments_to_reference(segments: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not segments:
        return None
    first = segments[0]
    if first.get("type") != "text":
        return None
    label_text = first.get("text", "").strip()
    label_mode = REFERENCE_LABEL_MODES.get(label_text.lower())
    if not label_mode:
        return None

    remaining: List[str] = []
    trailing_nodes: List[Dict[str, Any]] = []
    link_nodes: List[Dict[str, Any]] = []
    for segment in segments[1:]:
        if segment.get("type") == "text":
            remaining.append(segment.get("text", ""))
        elif segment.get("type") == "divider":
            trailing_nodes.append(segment)

    remaining_text = "".join(remaining)
    targets: List[str] = []
    link_matches = list(re.finditer(r"<([^>]+)>", remaining_text))
    if not link_matches:
        return None

    for match in link_matches:
        raw_target = match.group(1).strip()
        target, display = _split_link_notation(raw_target)
        targets.append(target)
        link_nodes.append({"type": "link", "target": target, "text": display or target})

    leftover_text = re.sub(r"<[^>]+>", "", remaining_text)
    for char in leftover_text:
        if char.isspace():
            continue
        if char == ',' and targets:
            continue
        kind = DIVIDER_KIND_BY_CHAR.get(char)
        if kind:
            trailing_nodes.append({"type": "divider", "kind": kind, "text": char})

    reference_block: Dict[str, Any] = {
        "type": "reference",
        "mode": label_mode,
        "text": label_text,
        "targets": targets,
    }

    content_nodes = link_nodes + trailing_nodes
    if content_nodes:
        reference_block["content"] = content_nodes

    return reference_block


def _strip_sentence_ending(segments: List[Dict[str, Any]]) -> str:
    if not segments:
        return ""
    last_segment = segments[-1]
    if last_segment.get("type") != "text":
        return ""
    text = last_segment.get("text", "")
    stripped = text.rstrip()
    if not stripped:
        segments.pop()
        return ""
    if stripped[-1:] in {".", "!", "?"}:
        ending = stripped[-1]
        remaining = stripped[:-1].rstrip()
        if remaining:
            last_segment["text"] = remaining
        else:
            segments.pop()
        return ending
    return ""


def _collect_trailing_sentence_from_headword(block: Dict[str, Any]) -> str:
    children = block.get("children") or []
    if not children:
        return ""
    last_child = children[-1]
    if last_child.get("type") in {"explanation", "translation"}:
        return _strip_sentence_ending(last_child.get("content", []))
    return ""


def _attach_orphan_references(blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not blocks:
        return blocks
    result: List[Dict[str, Any]] = []
    for block in blocks:
        if block.get("type") == "reference" and result:
            parent = result[-1]
            if parent.get("type") in {"translation", "explanation", "illustration", "headword"}:
                _insert_reference_child(parent, block)
                continue
        result.append(block)
    return result


def _insert_reference_child(parent: Dict[str, Any], reference: Dict[str, Any]) -> None:
    children = parent.setdefault("children", [])
    insert_at = len(children)
    for idx, child in enumerate(children):
        ctype = child.get("type")
        if ctype not in {"explanation", "note", "reference"}:
            insert_at = idx
            break
    children.insert(insert_at, reference)
    _adjust_parenthetical_reference(parent, reference)


def _adjust_parenthetical_reference(parent: Dict[str, Any], reference: Dict[str, Any]) -> None:
    children = parent.get("children") or []
    open_parenthesis = False
    for child in children:
        if child is reference:
            break
        if child.get("type") != "explanation":
            continue
        for segment in child.get("content", []):
            if segment.get("type") != "text":
                continue
            seg_text = segment.get("text", "")
            if seg_text.strip().startswith("("):
                open_parenthesis = True
                break
        if open_parenthesis:
            break

    text_value = reference.get("text", "")
    if open_parenthesis:
        if text_value.startswith("(="):
            text_value = text_value[2:].lstrip()
        if text_value:
            if not text_value.startswith("="):
                text_value = "= " + text_value
        else:
            text_value = "="
        if not text_value.endswith(")"):
            text_value = text_value.rstrip() + ")"
        reference["text"] = " " + text_value.lstrip()
    else:
        if text_value and not text_value.startswith(" "):
            reference["text"] = " " + text_value.lstrip()

    content_nodes = parent.get("content") or []
    trailing_text_node = None
    for node in reversed(content_nodes):
        if node.get("type") == "text":
            trailing_text_node = node
            break
    if not trailing_text_node:
        return

    text_payload = trailing_text_node.get("text", "") or ""
    match = re.search(r"\s*([A-Za-z0-9`´'’]+)\)\s*$", text_payload)
    if not match:
        return

    suffix = match.group(1)
    if not suffix:
        return

    had_trailing_paren = text_payload.rstrip().endswith(")")
    new_text = text_payload[: match.start()].rstrip()
    trailing_text_node["text"] = new_text

    targets = reference.get("targets") or []
    if targets:
        new_target = f"{targets[-1]}{suffix}"
        if had_trailing_paren:
            new_target += ")"
        targets[-1] = new_target
    if reference["text"].endswith(")"):
        updated_text = reference["text"][:-1] + suffix
        if had_trailing_paren:
            updated_text += ")"
        reference["text"] = updated_text
    else:
        updated_text = reference["text"] + suffix
        if had_trailing_paren:
            updated_text += ")"
        reference["text"] = updated_text


def _reorder_keys(block: Dict[str, Any]) -> Dict[str, Any]:
    ordered: Dict[str, Any] = {}
    for key in PREFERRED_ORDER:
        if key in block:
            ordered[key] = block[key]
    for key, value in block.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


def _build_sections(body: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    sections: List[Dict[str, Any]] = []
    main_indexes: List[int] = []
    for index, block in enumerate(body):
        btype = block.get("type")
        if btype == "headword":
            sections.append({
                "role": "wordform",
                "body_index": index,
                "raw_form": block.get("raw_form"),
            })
        elif btype == "idiomatics":
            sections.append({
                "role": "idiomatics",
                "body_index": index,
            })
        elif btype != "sentence_divider":
            main_indexes.append(index)
    if main_indexes:
        sections.insert(0, {"role": "main", "body_indexes": main_indexes})
    return sections


def _expand_headwords_in_list(blocks: Iterable[Dict[str, Any]], parent_bases: Optional[List[str]]) -> None:
    bases = parent_bases or []
    for block in blocks:
        if block.get("type") == "headword":
            child_bases = _expand_headword_node(block, bases)
            _expand_headwords_in_list(block.get("children", []) or [], child_bases)
        else:
            _expand_headwords_in_list(block.get("children", []) or [], bases)


def _expand_headword_node(node: Dict[str, Any], parent_bases: Optional[List[str]]) -> List[str]:
    lemmas = node.get("lemmas", []) or []
    expanded_entries: List[Dict[str, Any]] = []
    base_variants: List[str] = []
    for entry in lemmas:
        raw = entry.get("raw", "")
        expansions = _generate_lemmas_from_raw(raw, parent_bases)
        if expansions:
            for lemma in expansions:
                expanded_entries.append({"raw": raw, "lemma": lemma})
        else:
            expanded_entries.append(entry)
        base_variants.extend(_extract_base_variants(raw, parent_bases, expansions))

    if expanded_entries:
        node["lemmas"] = _dedupe_lemma_entries(expanded_entries)

    base_variants = _unique_preserve_order(base_variants)
    if not base_variants:
        base_variants = [entry.get("lemma") for entry in node.get("lemmas", []) if entry.get("lemma")]
        base_variants = _unique_preserve_order([b for b in base_variants if b])
    lemma_values = [entry.get("lemma") for entry in node.get("lemmas", []) if entry.get("lemma")]
    node["_tilde_context"] = {
        "lemmas": _unique_preserve_order(lemma_values),
        "bases": base_variants,
    }
    return base_variants


def _expand_tilde_in_blocks(blocks: Iterable[Dict[str, Any]], context: Optional[Dict[str, List[str]]]) -> None:
    context = context or {}
    lemmas = _unique_preserve_order(context.get("lemmas", []))
    bases = _unique_preserve_order(context.get("bases", []))
    for block in blocks:
        if block.get("type") == "headword":
            node_context = block.get("_tilde_context", {})
            next_context = {
                "lemmas": node_context.get("lemmas") or lemmas,
                "bases": node_context.get("bases") or bases or node_context.get("lemmas", []),
            }
            _expand_tilde_in_blocks(block.get("children", []) or [], next_context)
        else:
            if block.get("type") == "illustration":
                if not block.get("eo"):
                    text_fragments: List[str] = []
                    for item in block.get("content", []) or []:
                        if item.get("type") == "text":
                            text_fragments.append(item.get("text", ""))
                    raw_eo = " ".join(fragment.strip() for fragment in text_fragments if fragment.strip())
                    if raw_eo and not _contains_cyrillic(raw_eo):
                        block["eo"] = raw_eo
                        block["eo_raw"] = raw_eo
                        block["eo_expanded"] = [raw_eo]
                        block.pop("content", None)

                _merge_illustration_continuations(block)
                eo_text = block.get("eo")
                if eo_text and "~" in eo_text and (lemmas or bases):
                    expanded = _expand_tilde_text(eo_text, lemmas, bases)
                    if expanded:
                        block["eo_raw"] = eo_text
                        block["eo"] = expanded[0]
                        block["eo_expanded"] = expanded
            for child in block.get("children", []) or []:
                _expand_tilde_in_blocks([child], {"lemmas": lemmas, "bases": bases})


def _expand_tilde_text(text: str, lemmas: List[str], bases: List[str]) -> List[str]:
    results: List[str] = []
    max_len = max(len(lemmas), len(bases), 1)
    for idx in range(max_len):
        lemma = lemmas[idx] if idx < len(lemmas) else (lemmas[-1] if lemmas else "")
        base = bases[idx] if idx < len(bases) else (bases[-1] if bases else lemma)
        if not lemma and not base:
            continue
        results.append(_replace_tilde_with_strategy(text, lemma or base, base or lemma))
    return _unique_preserve_order(results)


def _replace_tilde_with_strategy(text: str, lemma: str, base: str) -> str:
    if not text:
        return text
    builder: List[str] = []
    length = len(text)
    i = 0
    while i < length:
        char = text[i]
        if char == '~':
            next_char = text[i + 1] if i + 1 < length else ''
            use_base = bool(next_char and (next_char.isalpha() or next_char in "'"))
            replacement = base if use_base else lemma
            builder.append(replacement)
            i += 1
            continue
        builder.append(char)
        i += 1
    return ''.join(builder)


def _generate_lemmas_from_raw(raw: str, parent_bases: Optional[List[str]]) -> List[str]:
    pattern = raw.replace("|", "")
    pattern = pattern.replace("/", "")
    expansions = _expand_pattern(pattern)
    bases = parent_bases or [""]
    results: List[str] = []
    for base in bases:
        for item in expansions:
            if "~" in item and not base:
                continue
            replaced = item.replace("~", base)
            if replaced:
                results.append(replaced)
    return _unique_preserve_order(results)


def _extract_base_variants(raw: str, parent_bases: Optional[List[str]], lemma_expansions: List[str]) -> List[str]:
    bases = parent_bases or [""]
    raw_no_slash = raw.replace("/", "")
    if "|" in raw_no_slash:
        prefix = raw_no_slash.split("|", 1)[0]
        prefix_expansions = _expand_pattern(prefix)
        results: List[str] = []
        for parent in bases:
            for variant in prefix_expansions:
                candidate = variant.replace("~", parent)
                if candidate:
                    results.append(candidate)
        return _unique_preserve_order(results)
    if "~" in raw_no_slash:
        if parent_bases:
            return _unique_preserve_order(parent_bases)
        return lemma_expansions
    return lemma_expansions


def _expand_pattern(pattern: str) -> List[str]:
    cleaned = pattern

    def recurse(index: int) -> Tuple[List[str], int]:
        results = [""]
        i = index
        while i < len(cleaned):
            char = cleaned[i]
            if char == '(':
                inner, new_index = recurse(i + 1)
                updated: List[str] = []
                for current in results:
                    updated.append(current)
                    for addition in inner:
                        updated.append(current + addition)
                results = updated
                i = new_index
            elif char == ')':
                return results, i + 1
            else:
                j = i
                while j < len(cleaned) and cleaned[j] not in '()':
                    j += 1
                literal = cleaned[i:j]
                results = [current + literal for current in results]
                i = j
                continue
        return results, i

    expanded, _ = recurse(0)
    return _unique_preserve_order([item for item in expanded if item])


def _dedupe_lemma_entries(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set = set()
    deduped: List[Dict[str, Any]] = []
    for entry in entries:
        key = (entry.get("raw"), entry.get("lemma"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)
    return deduped


def _unique_preserve_order(items: Iterable[str]) -> List[str]:
    seen: set = set()
    result: List[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _merge_plain_russian_illustrations(body: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    for block in body:
        if isinstance(block, dict) and block.get("children"):
            block["children"] = _merge_plain_russian_illustrations(block.get("children", []))
        if block.get("type") == "illustration" and (not block.get("eo") or not _has_letters(block.get("eo"))):
            content = block.get("content", []) or []
            if content and all(item.get("type") in {"text", "divider", "note", "link"} for item in content):
                if content:
                    target_translation = result[-1] if result and result[-1].get("type") == "translation" else None
                    if not target_translation:
                        target_translation = {"type": "translation", "content": []}
                        result.append(target_translation)

                    trailing_sentence = False
                    reference_mode: Optional[str] = None
                    reference_targets: List[str] = []
                    reference_text: Optional[str] = None
                    for item in content:
                        if item.get("type") == "text":
                            text_value = (item.get("text", "") or "").strip()
                            if text_value:
                                if item.get("style") == "italic":
                                    normalized = text_value.strip().rstrip('.').lower()
                                    if normalized in {"см", "ср"}:
                                        reference_mode = "compare" if normalized.startswith("ср") else "see"
                                        reference_text = text_value
                                        continue
                                content_list = target_translation.setdefault("content", [])
                                if content_list:
                                    last_item = content_list[-1]
                                    if (
                                        last_item.get("type") == "text"
                                        and last_item.get("style") == "regular"
                                    ):
                                        previous_text = last_item.get("text", "")
                                        if previous_text:
                                            last_char = previous_text.rstrip()[-1:]
                                            next_char = text_value[:1]
                                            if (
                                                last_char
                                                and last_char not in {",", ";", ":", ".", "(", "—", "-", "‑"}
                                                and next_char
                                                and next_char not in {",", ";", ":", ".", ")", "—", "-", "‑"}
                                            ):
                                                separator = "" if previous_text.endswith((" ", "-", "—", "‑")) else " "
                                                last_item["text"] = previous_text.rstrip() + separator + text_value
                                                continue
                                content_list.append({
                                    "type": "text",
                                    "style": "regular",
                                    "text": text_value,
                                })
                        elif item.get("type") == "divider":
                            divider_text = item.get("text", "")
                            if not divider_text:
                                continue
                            kind = DIVIDER_KIND_BY_CHAR.get(divider_text, "divider")
                            if divider_text == '.':
                                trailing_sentence = True
                            else:
                                target_translation.setdefault("content", []).append({
                                    "type": "divider",
                                    "kind": kind,
                                    "text": divider_text,
                                })
                        elif item.get("type") == "note":
                            note_text = _extract_plain_note_text(item)
                            if not note_text:
                                continue
                            display_text = note_text
                            if not display_text.startswith('('):
                                display_text = f"({display_text})"
                            content_list = target_translation.setdefault("content", [])
                            if content_list and content_list[-1].get("type") == "text":
                                previous = content_list[-1]
                                prev_text = previous.get("text", "")
                                separator = " " if prev_text and not prev_text.endswith(" ") else ""
                                previous["text"] = prev_text + separator + display_text
                            else:
                                content_list.append({
                                    "type": "text",
                                    "style": "italic",
                                    "text": display_text,
                                })
                        elif item.get("type") == "link":
                            target_value = (item.get("target") or item.get("text") or "").strip()
                            if target_value:
                                reference_targets.append(target_value)
                            continue

                    has_near, has_far = _detect_mixed_dividers(target_translation.get("content", []))
                    if has_near and has_far:
                        target_translation["ru_requires_review"] = True
                        raw_ru_text = _reconstruct_ru_text_from_content(target_translation.get("content", []))
                        if raw_ru_text:
                            target_translation.setdefault("meta", {})["raw_ru_text"] = raw_ru_text
                            prefix: List[Dict[str, Any]] = []
                            for item in target_translation.get("content", []):
                                if item.get("type") == "label":
                                    prefix.append(item)
                                    continue
                                break
                            target_translation["content"] = prefix + [{
                                "type": "text",
                                "style": "regular",
                                "text": raw_ru_text,
                            }]

                    if reference_targets:
                        reference_block: Dict[str, Any] = {
                            "type": "reference",
                            "mode": reference_mode or "see",
                            "targets": reference_targets,
                        }
                        if reference_text:
                            reference_block["text"] = reference_text
                        target_translation.setdefault("children", []).append(reference_block)

                    if trailing_sentence:
                        result.append({"type": "sentence_divider", "text": '.'})
                    continue
        result.append(block)
    return result


def _extract_plain_note_text(node: Dict[str, Any]) -> str:
    if not isinstance(node, dict):
        return ""
    if node.get("content"):
        pieces: List[str] = []
        for part in node.get("content") or []:
            if isinstance(part, dict) and part.get("type") == "text":
                pieces.append(part.get("text", ""))
        raw_text = "".join(pieces)
    else:
        raw_text = node.get("text", "")
    cleaned = " ".join(raw_text.replace("_", " ").split())
    return cleaned.strip()


def _has_letters(value: Optional[str]) -> bool:
    if not value:
        return False
    return any(char.isalpha() for char in value)


def _cleanup_tilde_context(article: Dict[str, Any]) -> None:
    if article.get("headword"):
        article["headword"].pop("_tilde_context", None)
    for block in article.get("body", []):
        _cleanup_tilde_context_block(block)


def _cleanup_tilde_context_block(block: Dict[str, Any]) -> None:
    if not isinstance(block, dict):
        return
    if block.get("type") == "headword":
        block.pop("_tilde_context", None)
    for child in block.get("children", []) or []:
        _cleanup_tilde_context_block(child)
