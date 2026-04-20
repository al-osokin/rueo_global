from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple


# NOTE:
# This module intentionally has no imports from translation_review to avoid
# circular dependencies. The caller injects constructors/helpers.

def build_translation_review_from_v4_ast(
    *,
    headword: str,
    v4_ast: Dict[str, Any],
    make_group: Callable[..., Any],
    build_candidates: Callable[[List[str], List[str]], List[Any]],
    select_candidate: Callable[[Any, Optional[str]], None],
    clean_spacing: Callable[[str], str],
    split_items_from_raw: Callable[[str], List[str]],
) -> Tuple[List[Any], List[str]]:
    groups: List[Any] = []
    notes: List[str] = []

    for form in v4_ast.get("forms") or []:
        if not isinstance(form, dict):
            continue

        section = clean_spacing(
            (form.get("raw") or form.get("expanded") or headword or "<без заголовка>")
        )
        blocks = form.get("blocks") or []
        current_items: List[str] = []
        current_sense_number: Optional[int] = None

        def flush_current() -> None:
            nonlocal current_items
            items = [clean_spacing(x) for x in current_items if clean_spacing(x)]
            if items:
                label = f"{current_sense_number}." if current_sense_number is not None else None
                group = make_group(
                    items=items,
                    base_items=list(items),
                    auto_generated=False,
                    requires_review=False,
                    section=section,
                    label=label,
                )
                group.candidates = build_candidates(group.base_items, group.items)
                select_candidate(group, None)
                groups.append(group)
            current_items = []

        for block in blocks:
            if not isinstance(block, dict):
                continue

            btype = block.get("type")
            raw = clean_spacing((block.get("raw") or "").replace("_", " "))
            if not raw:
                continue

            if btype == "sense":
                flush_current()

            mapped_sense = block.get("sense_number")
            if isinstance(mapped_sense, int):
                current_sense_number = mapped_sense
            elif btype == "sense" and isinstance(block.get("number"), int):
                current_sense_number = block.get("number")

            if btype == "example_raw":
                flush_current()
                eo_source = clean_spacing((block.get("example_eo") or "")) or None
                ru_text = clean_spacing((block.get("example_ru") or ""))
                if not ru_text:
                    # backward-compat fallback for fixtures without structured example fields
                    ru_text = raw
                example_items = split_items_from_raw(ru_text)
                if example_items:
                    sense_prefix = f"{current_sense_number}. " if current_sense_number is not None else ""
                    group = make_group(
                        items=example_items,
                        base_items=list(example_items),
                        auto_generated=False,
                        requires_review=False,
                        section=section,
                        eo_source=eo_source,
                        label=f"{sense_prefix}пример".strip(),
                    )
                    group.candidates = build_candidates(group.base_items, group.items)
                    select_candidate(group, None)
                    groups.append(group)
                continue

            if btype == "note" and raw.lower().startswith(("ср.", "см.")):
                note_scope = block.get("note_scope") or block.get("scope")
                if note_scope == "sense" and current_sense_number is not None:
                    notes.append(f"{section} [{current_sense_number}.]: {raw}")
                else:
                    notes.append(f"{section}: {raw}")
                continue

            if btype in {"sense", "text_raw", "note"}:
                current_items.extend(split_items_from_raw(raw))

        flush_current()

    return groups, notes
