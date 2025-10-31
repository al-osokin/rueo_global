import pytest

from app.parsing.parser_v3.legacy_bridge import legacy_parser, load_legacy_parser


legacy = load_legacy_parser()


def _processed_segments(text: str):
    segments = legacy.parse_rich_text(text, preserve_punctuation=True)
    segments = legacy.merge_punctuation_with_italic(segments)
    return legacy.absorb_parentheses_into_italic(segments)


def test_absorb_parentheses_simple_note():
    segments = _processed_segments("word (_note_)")
    assert len(segments) == 2
    assert segments[0]["text"] == "word "
    note_segment = segments[1]
    assert note_segment["style"] == "italic"
    assert note_segment["text"] == "(note)"


def test_absorb_parentheses_note_with_single_reference():
    segments = _processed_segments("word (_note_ = <ref>)")
    assert len(segments) == 2
    note_segment = segments[1]
    assert note_segment["style"] == "italic"
    assert note_segment["text"].startswith("(note")
    assert "= <ref>" in note_segment["text"]
    assert note_segment["text"].endswith(")")


def test_absorb_parentheses_note_with_multiple_references():
    segments = _processed_segments("счёты (_прибор_ = <globkalkulilo>, <bidkalkulilo>)")
    assert len(segments) == 2
    note_segment = segments[1]
    assert note_segment["style"] == "italic"
    assert note_segment["text"].startswith("(прибор")
    assert "globkalkulilo" in note_segment["text"]
    assert "bidkalkulilo" in note_segment["text"]
    assert note_segment["text"].endswith(")")


def test_parse_article_minimal_repro_has_note():
    article_text = "[test/o] 1. word (_note_ = <ref>);\n\t\tcontinuation;"
    result = legacy_parser.parse_article(article_text)
    block1 = [b for b in result["body"] if b.get("number") == 1][0]

    content_texts = [c.get("text", "") for c in block1.get("content", [])]
    assert ", )" not in content_texts

    note_nodes = [child for child in block1.get("children", []) if child.get("type") == "note"]
    assert note_nodes, "Expected a separate note node for numbered block"
    note_text = "".join(seg.get("text", "") for seg in note_nodes[0].get("content", []))
    assert note_text.startswith("(note")
    assert note_text.endswith(")")


def test_article_10_complex_note_kept_intact():
    article_text = """[abak/o] 1. _архит._ аб`ак(а);
\t2. _ист._ аб`ак(а), счётная доск`а (_древний счётный прибор_);
\t3. счёты (_прибор_ = <globkalkulilo>, <bidkalkulilo>);
\t\tjapana ~ _см._ <sorobano>;
\t4. _мат._ аб`ак(а), номогр`амма."""

    result = legacy_parser.parse_article(article_text)
    block3 = [b for b in result["body"] if b.get("number") == 3][0]

    content_texts = [c.get("text", "") for c in block3.get("content", [])]
    assert ", )" not in content_texts
    assert any("счёты" in text for text in content_texts)

    note_nodes = [child for child in block3.get("children", []) if child.get("type") == "note"]
    assert note_nodes, "Expected note child in numbered block 3"
    note_text = "".join(seg.get("text", "") for seg in note_nodes[0].get("content", []))
    assert note_text.startswith("(прибор")
    assert note_text.endswith(")")
    assert "globkalkulilo" in note_text
    assert "bidkalkulilo" in note_text
