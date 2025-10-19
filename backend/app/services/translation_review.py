from __future__ import annotations

import re
from collections import defaultdict
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


@dataclass(slots=True)
class TranslationGroup:
    """Represents a group of synonymous Russian translations for review."""

    items: List[str]
    label: Optional[str] = None
    requires_review: bool = False
    base_items: List[str] = field(default_factory=list)
    auto_generated: bool = False
    section: Optional[str] = None

    @property
    def is_empty(self) -> bool:
        return not self.items


@dataclass(slots=True)
class TranslationReview:
    headword: str
    groups: List[TranslationGroup]
    notes: List[str]


def build_translation_review(parsed_article: Dict) -> TranslationReview:
    headword = parsed_article.get("headword", {}).get("raw_form") or "<без заголовка>"
    groups, notes = _collect_groups_from_blocks(parsed_article.get("body") or [], section=None)
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


def _format_group_items(items: Sequence[str]) -> str:
    cleaned = [_clean_spacing(item) for item in items if item]
    cleaned = [item for item in cleaned if item]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    return "[" + " | ".join(cleaned) + "]"


def _collect_groups_from_blocks(blocks: Iterable[Dict], section: Optional[str]) -> Tuple[List[TranslationGroup], List[str]]:
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
        group_specs, extra_notes = _split_translation_groups(combined)
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

            groups.append(
                TranslationGroup(
                    items=items,
                    label=label if index == 0 else None,
                    requires_review=buffer_requires_review,
                    base_items=cleaned_base,
                    auto_generated=auto_generated,
                    section=section,
                )
            )

        buffer_content = []
        buffer_requires_review = False
        buffer_continues = False
        pending_suffixes = []

    for block in blocks or []:
        block_type = block.get("type")

        if block_type == "headword":
            _flush_buffer()
            raw_form = block.get("raw_form")
            child_groups, child_notes = _collect_groups_from_blocks(
                block.get("children") or [],
                section=raw_form,
            )
            groups.extend(child_groups)
            notes.extend(child_notes)
            continue

        if block_type == "illustration" and block.get("eo"):
            _flush_buffer()
            example_section = block.get("eo_raw") or block.get("eo")
            example_groups, example_notes = _build_groups_from_example(block, example_section)
            groups.extend(example_groups)
            notes.extend(example_notes)
            continue

        if block_type == "translation" or (block_type == "illustration" and not block.get("eo")):
            block_requires_review = bool(block.get("ru_requires_review"))
            block_continuation = _block_indicates_continuation(block)
            if (
                buffer_content
                and not buffer_requires_review
                and not block_requires_review
                and not buffer_continues
            ):
                _flush_buffer()

            buffer_content.append(block.get("content") or [])
            if block_requires_review:
                buffer_requires_review = True
            buffer_continues = block_continuation
            continue

        _flush_buffer()

        if block_type == "note":
            text = _consume_text(block.get("content") or [])
            if text:
                _append_note(text)

    _flush_buffer()
    return groups, notes


def _build_groups_from_example(block: Dict, section: Optional[str]) -> Tuple[List[TranslationGroup], List[str]]:
    segments = block.get("ru_segments") or []
    content = _ru_segments_to_content(segments)
    if not content:
        return [], []

    label = _extract_label(content)
    group_specs, extra_notes = _split_translation_groups(content)
    requires_review = bool(block.get("ru_requires_review"))

    groups: List[TranslationGroup] = []
    for spec in group_specs:
        base_items = spec.get("base", [])
        expanded_items = spec.get("expanded", [])
        if not expanded_items or _is_pos_marker(base_items):
            continue
        auto_generated = expanded_items != base_items
        groups.append(
            TranslationGroup(
                items=expanded_items,
                label=label,
                requires_review=requires_review,
                base_items=base_items,
                auto_generated=auto_generated,
                section=section,
            )
        )

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


def _split_translation_groups(content: Iterable[Dict]) -> Tuple[List[Dict[str, List[str]]], List[str]]:
    builder = _PhraseBuilder()
    current_group: List[str] = []
    base_groups: List[List[str]] = []
    extra_notes: List[str] = []

    content = _expand_inline_dividers(list(content))

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
            elif symbol == ".":
                _flush_builder()
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

    return results, extra_notes


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
            self._append_component_options(parts)
        else:
            self._append_component(normalized.rstrip(".,;:"))

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
            if option not in seen:
                base_options.append(option)
                seen.add(option)

    def add_note(self, note: str) -> None:
        cleaned = _clean_spacing(note.replace("_", " "))
        if cleaned:
            self._notes.append(cleaned)

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
        prepared = [_clean_spacing(option).rstrip(".,;:") for option in options]
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
    parts = [
        part.strip(" ,;/")
        for part in _ALT_SPLIT_RE.split(cleaned)
        if part.strip(" ,;/")
    ]
    if len(parts) == 1:
        tokens = [token.strip() for token in parts[0].split() if token.strip()]
        if len(tokens) > 1:
            parts = tokens
    if not parts:
        return None
    return parts


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
                variants: List[str] = []
                for replacement in [base_word] + alternatives:
                    prefix_part = prefix
                    if prefix_part and not prefix_part.endswith((" ", "-", "—", "/")):
                        prefix_part += " "
                    new_text = prefix_part + replacement
                    if rest and not rest.startswith((" ", ",", ".", ";", ":", ")")):
                        new_text += " "
                    new_text += rest.lstrip()
                    variants.extend(_recurse(new_text))
                return variants

        if " " not in inside_clean:
            without = before + after
            with_opt = before + inside_clean + after
            return _recurse(without) + _recurse(with_opt)

        return _recurse(before + " " + inside_clean + after)

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
    endings = ("ться", "сть", "сти", "чь", "ть", "ти")
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

    if adjective_candidates:
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
        for suffix_len in range(1, min(3, len(tokens))):
            prefix_tokens = tokens[:-suffix_len]
            suffix_tokens = tokens[-suffix_len:]
            if len(prefix_tokens) != 1:
                continue
            base_word = prefix_tokens[0]
            suffix_text = " ".join(suffix_tokens)

            if _looks_like_verb(base_word):
                verb_candidates = [
                    item
                    for item in singles
                    if _looks_like_verb(_first_token(item))
                ]
                if len(verb_candidates) >= 2:
                    for verb in verb_candidates:
                        extra_items.append(_clean_spacing(f"{verb} {suffix_text}"))
            elif _looks_like_adjective(base_word):
                adjective_candidates = [
                    item
                    for item in singles
                    if _looks_like_adjective(_first_token(item))
                ]
                if adjective_candidates:
                    last_token = suffix_tokens[-1]
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
    endings = ("ться", "сь", "ст", "ть", "ти", "чь")
    return any(stripped.endswith(ending) for ending in endings)


def _strip_trailing_punctuation(value: str) -> str:
    return value.rstrip(" ,.;:)")


def _is_meaningful_item(value: str) -> bool:
    if not value:
        return False
    stripped = value.strip()
    return stripped not in {",", ";", ".", ")", "("}


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
                        new_node["text"] = trimmed
                        result.append(new_node)
                    if idx != len(parts) - 1:
                        result.append({"type": "divider", "text": ";", "kind": "far_divider"})
                continue
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
    return collapsed.strip(" ;,")


def collect_translation_phrases(review: TranslationReview) -> List[str]:
    phrases: List[str] = []
    for group in review.groups:
        phrases.extend(group.items)
    return phrases
