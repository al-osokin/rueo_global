from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


def parse_headword_mvp(line: str) -> Tuple[Optional[Dict[str, Any]], str]:
    """Локальный минимальный парсер заголовка для v4 (без зависимостей от parser_v3)."""
    line = line.strip()

    if not line.startswith("["):
        return None, line

    bracket_end = line.find("]")
    if bracket_end == -1:
        return None, line

    raw_form = line[: bracket_end + 1]
    remainder = line[bracket_end + 1 :].lstrip()

    inside = raw_form[1:-1].strip()
    if not inside:
        return None, remainder

    official_mark: Optional[Any] = None
    if inside.startswith("*"):
        official_mark = True
        inside = inside[1:].lstrip()

    if remainder.startswith("*"):
        mark_match = re.match(r"^\*(\d+)", remainder)
        if mark_match:
            official_mark = f"*{mark_match.group(1)}"
            remainder = remainder[len(mark_match.group(0)) :].lstrip()
        else:
            official_mark = True
            remainder = remainder[1:].lstrip()

    homonym: Optional[int] = None
    homonym_match = re.search(r"\s+(\d+)$", inside)
    if homonym_match:
        homonym = int(homonym_match.group(1))
        inside = inside[: homonym_match.start()].strip()

    if not inside:
        return None, remainder

    parts = [p.strip() for p in inside.split(",")] if "," in inside else [inside]
    lemmas = [{"lemma": part, "raw": part} for part in parts if part]
    if not lemmas:
        return None, remainder

    headword: Dict[str, Any] = {
        "raw_form": raw_form,
        "lemmas": lemmas,
    }
    if official_mark is not None:
        headword["official_mark"] = official_mark
    if homonym is not None:
        headword["homonym"] = homonym

    return headword, remainder


def _split_example_raw(text: str) -> Tuple[Optional[str], str]:
    t = text.strip().strip(';').strip()
    if not t:
        return None, ''

    tokens = t.split()
    split_at = None
    for idx, token in enumerate(tokens):
        if any('а' <= ch.lower() <= 'я' or ch.lower() == 'ё' for ch in token):
            split_at = idx
            break

    if split_at is None or split_at == 0:
        return None, t

    eo_part = ' '.join(tokens[:split_at]).strip()
    ru_part = ' '.join(tokens[split_at:]).strip()
    return eo_part or None, ru_part


def _looks_like_eo_ru_example(text: str) -> bool:
    eo_part, ru_part = _split_example_raw(text)
    if not eo_part or not ru_part:
        return False

    eo_clean = eo_part.strip()
    # Не считаем примером пронумерованные/служебные префиксы вроде "{vn} 1. ..."
    if re.match(r"^(?:\{[^}]+\}\s*)?\d+\.$", eo_clean):
        return False
    if eo_clean.startswith("{"):
        return False

    # Если RU-часть начинается с курсивной поясняющей скобки,
    # это часто continuation перевода, а не EO->RU пример.
    ru_clean = ru_part.strip()
    if ru_clean.startswith("(_"):
        return False

    # Удаляем поясняющие скобки перед проверкой кириллицы,
    # чтобы не ловить ложные examples на конструкциях вида
    # "...; (_и это ... )".
    ru_no_parens = re.sub(r"\([^)]*\)", "", ru_part)

    # heuristic: eo token usually latin-ish, ru side usually cyrillic-rich
    has_latin = any(('a' <= ch.lower() <= 'z') or ch in 'ĉĝĥĵŝŭ' for ch in eo_part)
    has_cyr = any('а' <= ch.lower() <= 'я' or ch.lower() == 'ё' for ch in ru_no_parens)
    return has_latin and has_cyr


def _is_separator_token(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if stripped in {"@", "@@", "§", "¶"}:
        return True
    if re.match(r"^[@#]+$", stripped):
        return True
    if re.match(r"^[-—=]{2,}$", stripped):
        return True
    return False


def _is_reference_note(text: str) -> bool:
    """Ссылочные заметки вида '_см._ <...>' / '_ср._ <...>' считаем note, а не sense."""
    stripped = text.strip()
    if not stripped.startswith("_"):
        return False
    return bool(re.match(r"^_(?:см|ср)\._", stripped, flags=re.IGNORECASE))


def _has_terminal_translation_punctuation(text: str) -> bool:
    """True, если строка явно выглядит завершённой (`,`, `;`, `.` в конце)."""
    stripped = text.rstrip()
    if not stripped:
        return False

    # Разрешаем закрывающие скобки/кавычки после финального знака.
    tail = stripped.rstrip(')]}"»')
    if not tail:
        return False
    return tail.endswith((",", ";", "."))


@dataclass
class StructuralBlock:
    type: str
    raw: str
    number: Optional[int] = None
    indent: int = 0
    example_eo: Optional[str] = None
    example_ru: Optional[str] = None


@dataclass
class StructuralForm:
    raw: str
    expanded: str
    blocks: List[StructuralBlock]


class ParsingPipelineV4:
    """
    Parser v4 (MVP):
    - строит структурный AST (forms/blocks)
    - отдает собственный минимальный payload (headword/body/meta), без parser_v3 pipeline
    """

    def parse_article(self, article_text: str, *, index: int = 0) -> Dict[str, Any]:
        v4_ast = self._build_structural_ast(article_text)
        return self._build_minimal_payload(v4_ast=v4_ast, index=index)

    def _build_minimal_payload(self, *, v4_ast: Dict[str, Any], index: int) -> Dict[str, Any]:
        forms = v4_ast.get("forms") or []
        first_form = forms[0] if forms else {}
        head_raw = first_form.get("raw") if isinstance(first_form, dict) else None

        body: List[Dict[str, Any]] = []
        for form in forms:
            if not isinstance(form, dict):
                continue
            form_label = form.get("raw") or form.get("expanded") or "<без заголовка>"
            children: List[Dict[str, Any]] = []
            for block in form.get("blocks") or []:
                if not isinstance(block, dict):
                    continue
                child = {
                    "type": block.get("type") or "text_raw",
                    "raw": block.get("raw") or "",
                    "number": block.get("number"),
                }
                if child["type"] == "example_raw":
                    child["example_eo"] = block.get("example_eo")
                    child["example_ru"] = block.get("example_ru")
                children.append(child)
            body.append(
                {
                    "type": "headword",
                    "raw_form": form_label,
                    "children": children,
                }
            )

        headword = None
        if head_raw:
            headword, _ = parse_headword_mvp(head_raw)

        if not headword:
            fallback = head_raw or "<без заголовка>"
            headword = {"raw_form": fallback, "lemmas": [{"lemma": fallback, "raw": fallback}]}

        return {
            "headword": headword,
            "body": body,
            "meta": {
                "parser_engine": "v4",
                "v4_ast": v4_ast,
                "parse_index": index,
            },
        }

    def _build_structural_ast(self, article_text: str) -> Dict[str, Any]:
        lines = [ln.rstrip("\r") for ln in article_text.splitlines()]
        forms: List[StructuralForm] = []

        current_form: Optional[StructuralForm] = None
        main_expanded = ""

        for raw_line in lines:
            if not raw_line.strip():
                continue

            indent = len(raw_line) - len(raw_line.lstrip(" \t"))
            stripped = raw_line.strip()

            hw, remainder = parse_headword_mvp(stripped)
            if hw and hw.get("raw_form"):
                raw_hw = hw["raw_form"]
                expanded = self._expand_headword(raw_hw, main_expanded)
                if not main_expanded:
                    main_expanded = expanded
                current_form = StructuralForm(raw=raw_hw, expanded=expanded, blocks=[])
                forms.append(current_form)
                if remainder:
                    self._append_block(current_form, remainder, indent)
                continue

            if current_form is None:
                # pre-headword garbage: keep as pseudo form
                current_form = StructuralForm(raw="<preamble>", expanded="<preamble>", blocks=[])
                forms.append(current_form)

            self._append_block(current_form, stripped, indent)

        ast_forms: List[Dict[str, Any]] = []
        for form in forms:
            blocks_payload: List[Dict[str, Any]] = []
            current_sense_number: Optional[int] = None
            for b in form.blocks:
                if b.type == "sense":
                    current_sense_number = b.number

                scope = "sense" if current_sense_number is not None else "form"
                block_payload: Dict[str, Any] = {
                    "type": b.type,
                    "raw": b.raw,
                    "number": b.number,
                    "indent": b.indent,
                    "scope": scope,
                    "sense_number": current_sense_number,
                }
                if b.type == "note":
                    block_payload["note_scope"] = scope
                if b.type == "example_raw":
                    block_payload["example_eo"] = b.example_eo
                    block_payload["example_ru"] = b.example_ru
                blocks_payload.append(block_payload)

            ast_forms.append(
                {
                    "raw": form.raw,
                    "expanded": form.expanded,
                    "blocks": blocks_payload,
                }
            )

        return {"forms": ast_forms}

    def _append_block(self, form: StructuralForm, text: str, indent: int) -> None:
        m = re.match(r"^(?:\{[^}]+\}\s*)?(\d+)\.\s*(.*)$", text)
        if m:
            sense_raw = m.group(2).strip()
            if _is_reference_note(sense_raw):
                form.blocks.append(
                    StructuralBlock(
                        type="note",
                        raw=sense_raw,
                        number=int(m.group(1)),
                        indent=indent,
                    )
                )
            else:
                form.blocks.append(
                    StructuralBlock(
                        type="sense",
                        raw=sense_raw,
                        number=int(m.group(1)),
                        indent=indent,
                    )
                )
            return

        # Minimal deterministic classification; semantics later
        if _is_separator_token(text):
            block_type = "separator"
        elif text.startswith("_"):
            block_type = "note"
        elif _looks_like_eo_ru_example(text):
            block_type = "example_raw"
        else:
            block_type = "text_raw"

        if self._should_merge_with_previous(form, block_type=block_type, indent=indent, text=text):
            form.blocks[-1].raw = f"{form.blocks[-1].raw} {text.strip()}".strip()
            return

        example_eo = None
        example_ru = None
        if block_type == "example_raw":
            example_eo, example_ru = _split_example_raw(text)

        form.blocks.append(
            StructuralBlock(
                type=block_type,
                raw=text,
                indent=indent,
                example_eo=example_eo,
                example_ru=example_ru,
            )
        )

    def _should_merge_with_previous(self, form: StructuralForm, *, block_type: str, indent: int, text: str) -> bool:
        if not form.blocks:
            return False

        prev = form.blocks[-1]

        # Жёсткие границы: examples/numbered/separators никогда не склеиваются.
        if block_type in {"example_raw", "separator"}:
            return False
        if prev.type == "separator":
            return False

        # Не склеиваем строку, которая сама выглядит началом numbered-смысла.
        if re.match(r"^(?:\{[^}]+\}\s*)?\d+\.\s*", text.strip()):
            return False

        # Начало примечания всегда отдельным блоком.
        if block_type == "note":
            return False

        mergeable_prev = prev.type in {"sense", "note", "text_raw"}
        mergeable_curr = block_type in {"text_raw"}
        if not (mergeable_prev and mergeable_curr):
            return False

        # Для multiline переводов склеиваем по умолчанию,
        # кроме жёстких границ выше (numbered/example/separator/note-start).
        # Запятая и точка с запятой в конце строки не запрещают склейку:
        # это часто продолжение перечисления на следующей строке.
        return True

    def _expand_headword(self, raw_headword: str, main_expanded: str) -> str:
        inside = raw_headword.strip()[1:-1] if raw_headword.startswith("[") else raw_headword
        first = inside.split(",")[0].strip()

        # crude lemma extraction from e.g. abort|i -> aborti
        def _lemma(token: str) -> str:
            return token.replace("|", "").replace("/", "")

        if first.startswith("~") and main_expanded:
            suffix = first[1:]
            base = main_expanded
            # Деривационные продолжения (~a, ~o, ~ig/o и т.п.)
            # цепляются к основе без финальной тематической гласной.
            if suffix and suffix[0].isalpha():
                base = re.sub(r"[aeiou]$", "", base)
            return _lemma(base + suffix)

        return _lemma(first)
