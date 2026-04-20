from app.parsing.parser_v4.pipeline import parse_headword_mvp


def test_parse_headword_mvp_basic_and_remainder():
    headword, remainder = parse_headword_mvp("[ab-] _note_")
    assert headword is not None
    assert headword["raw_form"] == "[ab-]"
    assert headword["lemmas"][0]["lemma"] == "ab-"
    assert remainder == "_note_"


def test_parse_headword_mvp_supports_homonym_and_official_mark():
    headword, remainder = parse_headword_mvp("[*foo 2] *3 tail")
    assert headword is not None
    assert headword["raw_form"] == "[*foo 2]"
    assert headword["homonym"] == 2
    assert headword["official_mark"] == "*3"
    assert remainder == "tail"
