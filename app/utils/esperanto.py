from __future__ import annotations

from functools import lru_cache
from typing import Dict

_UX_TO_LETTER = {
    "Cx": "Ĉ",
    "cx": "ĉ",
    "Gx": "Ĝ",
    "gx": "ĝ",
    "Hx": "Ĥ",
    "hx": "ĥ",
    "Jx": "Ĵ",
    "jx": "ĵ",
    "Sx": "Ŝ",
    "sx": "ŝ",
    "Ux": "Ŭ",
    "ux": "ŭ",
}

_LETTER_TO_UX = {v: k for k, v in _UX_TO_LETTER.items()}

_ENTITY_TO_LETTER = {
    "&#264;": "Ĉ",
    "&#265;": "ĉ",
    "&#284;": "Ĝ",
    "&#285;": "ĝ",
    "&#292;": "Ĥ",
    "&#293;": "ĥ",
    "&#308;": "Ĵ",
    "&#309;": "ĵ",
    "&#348;": "Ŝ",
    "&#349;": "ŝ",
    "&#364;": "Ŭ",
    "&#365;": "ŭ",
}

_CARET_MAP = {
    "^C": "Cx",
    "^c": "cx",
    "^G": "Gx",
    "^g": "gx",
    "^H": "Hx",
    "^h": "hx",
    "^J": "Jx",
    "^j": "jx",
    "^S": "Sx",
    "^s": "sx",
    "^U": "Ux",
    "^u": "ux",
}


@lru_cache(maxsize=None)
def _entity_to_ux_map() -> Dict[str, str]:
    return {entity: _LETTER_TO_UX[letter] for entity, letter in _ENTITY_TO_LETTER.items()}


def oh_sencxapeligo(text: str) -> str:
    """Convert ^C style digraphs to ux format."""
    for src, dst in _CARET_MAP.items():
        text = text.replace(src, dst)
    return text


def cxapeligo(text: str) -> str:
    """Convert ux digraphs to accented Esperanto characters."""
    if not text:
        return text
    for ux, letter in _UX_TO_LETTER.items():
        text = text.replace(ux, letter)
    for entity, letter in _ENTITY_TO_LETTER.items():
        text = text.replace(entity, letter)
    return text


def sencxapeligo(text: str) -> str:
    """Convert accented Esperanto characters to ux digraphs."""
    if not text:
        return text
    for letter, ux in _LETTER_TO_UX.items():
        text = text.replace(letter, ux)
    for entity, ux in _entity_to_ux_map().items():
        text = text.replace(entity, ux)
    return text


def urlsencxapeligo(text: str) -> str:
    """Prepare text for URLs (convert accented letters and spaces)."""
    text = sencxapeligo(text)
    return text.replace(" ", "+").strip()
