from app.parsing.parser_v4.pipeline import ParsingPipelineV4


def _first_form_blocks(text: str):
    parsed = ParsingPipelineV4().parse_article(text)
    return parsed["meta"]["v4_ast"]["forms"][0]["blocks"]


def test_id3_like_note_continuation_merges_into_single_note():
    text = """[-a II]
_элемент_ -a_, являющийся конечной частью корня в названиях
 ряда греч. букв_:
  beta б`ета;
"""
    blocks = _first_form_blocks(text)
    assert blocks[0]["type"] == "note"
    assert "ряда греч. букв_:" in blocks[0]["raw"]


def test_id6_like_note_continuation_merges_but_examples_stay_separate():
    text = """[ab-]
_спец. приставка_ аб- _со значением <<абсолютный>>,
 присоединяемая к названиям физических величин
 в абсолютной системе единиц_:
  ab/ampero абамп`ер, абсол`ютный амп`ер;
"""
    blocks = _first_form_blocks(text)
    assert blocks[0]["type"] == "note"
    assert "абсолютной системе единиц_:" in blocks[0]["raw"]
    assert blocks[1]["type"] == "example_raw"


def test_id56_like_sense_continuation_merges_and_sr_note_stays_separate():
    text = """[ablaci/o]
1. _мед._ иссеч`ение, удал`ение (_ткани, члена
  или органа_ = <fortrancxo>, <desekco>);
  _ср._ <ektomio>;
"""
    blocks = _first_form_blocks(text)
    assert blocks[0]["type"] == "sense"
    assert "или органа_ = <fortrancxo>, <desekco>);" in blocks[0]["raw"]
    assert blocks[1]["type"] == "note"
    assert blocks[1]["raw"].startswith("_ср._")
