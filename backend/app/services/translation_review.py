from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


@dataclass(slots=True)
class TranslationGroup:
    """Represents a group of synonymous Russian translations for review."""

    items: List[str]
    label: Optional[str] = None
    requires_review: bool = False

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
    groups: List[TranslationGroup] = []
    notes: List[str] = []

    buffer_content: List[List[Dict]] = []
    buffer_requires_review = False
    buffer_continues = False
    pending_suffixes: List[str] = []

    def _flush_buffer() -> None:
        nonlocal buffer_content, buffer_requires_review, buffer_continues, pending_suffixes
        if not buffer_content:
            return

        combined: List[Dict] = []
        for chunk in buffer_content:
            combined.extend(chunk)

        label = _extract_label(combined)
        synonym_groups, extra_notes = _split_translation_groups(combined)
        notes.extend(extra_notes)

        for index, items in enumerate(synonym_groups):
            if not items or _is_pos_marker(items):
                continue
            if len(items) == 1 and items[0].lower().startswith("или "):
                alternatives = _extract_note_alternatives(items[0]) or []
                pending_suffixes = _deduplicate(alternatives)
                continue
            if pending_suffixes:
                combos = [
                    _clean_spacing(f"{base} {suffix}")
                    for base in items
                    for suffix in pending_suffixes
                ]
                items = _deduplicate([*items, *combos])
                pending_suffixes = []
            groups.append(
                TranslationGroup(
                    items=items,
                    label=label if index == 0 else None,
                    requires_review=buffer_requires_review,
                )
            )

        buffer_content = []
        buffer_requires_review = False
        buffer_continues = False
        pending_suffixes = []

    for block in parsed_article.get("body", []):
        block_type = block.get("type")
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
                notes.append(text)

    _flush_buffer()

    return TranslationReview(headword=headword, groups=groups, notes=notes)


def format_translation_review(review: TranslationReview) -> str:
    lines = [review.headword]
    for group in review.groups:
        if group.is_empty:
            continue
        label_prefix = f"{group.label} " if group.label else ""
        body = _format_group_items(group.items)
        suffix = "  [?]" if group.requires_review else ""
        lines.append(f"  ⮕ {label_prefix}{body}{suffix}")
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


def _split_translation_groups(content: Iterable[Dict]) -> Tuple[List[List[str]], List[str]]:
    builder = _PhraseBuilder()
    groups: List[List[str]] = []
    extra_notes: List[str] = []
    current_group: List[str] = []

    def _flush_current() -> None:
        nonlocal current_group
        phrases = builder.flush()
        if phrases:
            current_group.extend(phrases)
        extra_notes.extend(builder.take_notes())

    for node in content:
        node_type = node.get("type")
        if node_type == "label":
            continue
        if node_type == "divider":
            symbol = (node.get("text") or "").strip()
            if symbol == ",":
                _flush_current()
            elif symbol == ";":
                _flush_current()
                if current_group:
                    groups.append(_deduplicate(current_group))
                current_group = []
            elif symbol == ".":
                _flush_current()
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

    _flush_current()
    if current_group:
        groups.append(_deduplicate(current_group))

    cleaned_groups: List[List[str]] = []
    for group in groups:
        expanded: List[str] = []
        for item in group:
            for variant in _expand_parenthetical_forms(item):
                normalized = _clean_spacing(variant).rstrip(".,;:")
                if normalized:
                    expanded.append(normalized)
        if expanded:
            expanded = _deduplicate(expanded)
            expanded = _expand_cross_product(expanded)
            cleaned_groups.append(expanded)

    return cleaned_groups, extra_notes


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
    suffix_options = [suffix] + singles

    combinations: List[str] = []
    for prefix in sorted(prefixes):
        for option in suffix_options:
            combinations.append(_clean_spacing(f"{prefix} {option}"))

    return _deduplicate(combinations)


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
