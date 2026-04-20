from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.parsing.parser_v3.text_parser import parse_headword


def _looks_like_eo_ru_example(text: str) -> bool:
    t = text.strip().strip(';').strip()
    if not t or ' ' not in t:
        return False
    first, rest = t.split(' ', 1)
    # heuristic: eo token usually latin-ish, ru side usually cyrillic-rich
    has_latin = any(('a' <= ch.lower() <= 'z') or ch in 'ĉĝĥĵŝŭ' for ch in first)
    has_cyr = any('а' <= ch.lower() <= 'я' or ch.lower() == 'ё' for ch in rest)
    return has_latin and has_cyr


@dataclass
class StructuralBlock:
    type: str
    raw: str
    number: Optional[int] = None
    indent: int = 0


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
                children.append(
                    {
                        "type": block.get("type") or "text_raw",
                        "raw": block.get("raw") or "",
                        "number": block.get("number"),
                    }
                )
            body.append(
                {
                    "type": "headword",
                    "raw_form": form_label,
                    "children": children,
                }
            )

        headword = None
        if head_raw:
            headword, _ = parse_headword(head_raw)

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

            hw, remainder = parse_headword(stripped)
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

        return {
            "forms": [
                {
                    "raw": form.raw,
                    "expanded": form.expanded,
                    "blocks": [
                        {
                            "type": b.type,
                            "raw": b.raw,
                            "number": b.number,
                            "indent": b.indent,
                        }
                        for b in form.blocks
                    ],
                }
                for form in forms
            ]
        }

    def _append_block(self, form: StructuralForm, text: str, indent: int) -> None:
        m = re.match(r"^(\d+)\.\s*(.*)$", text)
        if m:
            form.blocks.append(
                StructuralBlock(
                    type="sense",
                    raw=m.group(2).strip(),
                    number=int(m.group(1)),
                    indent=indent,
                )
            )
            return

        # Minimal deterministic classification; semantics later
        if text.startswith("_"):
            block_type = "note"
        elif _looks_like_eo_ru_example(text):
            block_type = "example_raw"
        else:
            block_type = "text_raw"

        if self._should_merge_with_previous(form, block_type=block_type, indent=indent, text=text):
            form.blocks[-1].raw = f"{form.blocks[-1].raw} {text.strip()}".strip()
            return

        form.blocks.append(StructuralBlock(type=block_type, raw=text, indent=indent))

    def _should_merge_with_previous(self, form: StructuralForm, *, block_type: str, indent: int, text: str) -> bool:
        if not form.blocks:
            return False

        prev = form.blocks[-1]

        # Никогда не склеиваем примеры/новые numbered-блоки с предыдущим.
        if block_type == "example_raw":
            return False

        # Явный короткий маркер заметки (например "_ср._") оставляем отдельным блоком.
        if text.strip().startswith("_ср._"):
            return False

        # Склеиваем только продолжения с большим отступом, чтобы не ломать границы верхнего уровня.
        if indent <= prev.indent:
            return False

        # Склейка допустима только для структурно «продолжаемых» блоков.
        return prev.type in {"sense", "note", "text_raw"} and block_type in {"note", "text_raw"}

    def _expand_headword(self, raw_headword: str, main_expanded: str) -> str:
        inside = raw_headword.strip()[1:-1] if raw_headword.startswith("[") else raw_headword
        first = inside.split(",")[0].strip()

        # crude lemma extraction from e.g. abort|i -> aborti
        def _lemma(token: str) -> str:
            return token.replace("|", "").replace("/", "")

        if first.startswith("~") and main_expanded:
            suffix = first[1:]
            base = re.sub(r"[aeiou]$", "", main_expanded) if suffix and suffix[0].isalpha() else main_expanded
            return _lemma(base + suffix)

        return _lemma(first)
