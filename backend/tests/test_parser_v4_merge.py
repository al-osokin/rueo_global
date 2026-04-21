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


def test_numbered_boundary_is_not_merged_even_with_indent():
    text = """[ablaci/o]
1. первый смысл
  продолжение первого
  2. второй смысл
"""
    blocks = _first_form_blocks(text)
    assert len(blocks) == 2
    assert blocks[0]["type"] == "sense"
    assert blocks[0]["number"] == 1
    assert "продолжение первого" in blocks[0]["raw"]
    assert blocks[1]["type"] == "sense"
    assert blocks[1]["number"] == 2


def test_id77_like_numbered_note_and_examples_keep_sense_mapping():
    text = """[abort|i]
{vn} 1. _мед._ в`ыкинуть плод, преждевр`еменно род`ить;
  _ср._ <akusxi>;
  2. _перен._ останов`иться в разв`итии;
    ~igi sin сд`елать (себе) аб`орт;
"""
    blocks = _first_form_blocks(text)

    assert blocks[0]["type"] == "sense"
    assert blocks[0]["number"] == 1
    assert blocks[0]["sense_number"] == 1
    assert blocks[0]["scope"] == "sense"

    assert blocks[1]["type"] == "note"
    assert blocks[1]["note_scope"] == "sense"
    assert blocks[1]["sense_number"] == 1

    assert blocks[2]["type"] == "sense"
    assert blocks[2]["number"] == 2
    assert blocks[2]["sense_number"] == 2

    assert blocks[3]["type"] == "example_raw"
    assert blocks[3]["sense_number"] == 2
    assert blocks[3]["scope"] == "sense"


def test_id77_abortulo_first_numbered_reference_is_note_not_sense():
    text = """[~ul/o]
1. _см._ ~ajxo;
2. _груб._ в`ыродок, недон`осок.
"""
    blocks = _first_form_blocks(text)

    assert blocks[0]["type"] == "note"
    assert blocks[0]["number"] == 1
    assert blocks[0]["raw"].startswith("_см._")

    assert blocks[1]["type"] == "sense"
    assert blocks[1]["number"] == 2
    assert blocks[1]["sense_number"] == 2


def test_line_without_terminal_punctuation_is_merged_even_same_indent():
    text = """[а I]
да поможет вам Бог
помоги вам Бог;
"""
    blocks = _first_form_blocks(text)
    assert len(blocks) == 1
    assert blocks[0]["type"] == "text_raw"
    assert blocks[0]["raw"] == "да поможет вам Бог помоги вам Бог;"


def test_lines_with_terminal_punctuation_can_still_merge_for_continuation_lists():
    text = """[без]
~ всякой причины sen ia ajn kauxzo,
senkauxze;
"""
    blocks = _first_form_blocks(text)
    assert len(blocks) == 1
    assert "~ всякой причины sen ia ajn kauxzo, senkauxze;" == blocks[0]["raw"]


def test_note_start_is_hard_boundary_not_merged():
    text = """[ablaci/o]
иссечение, удаление
_ср._ <ektomio>;
"""
    blocks = _first_form_blocks(text)
    assert len(blocks) == 2
    assert blocks[0]["type"] == "text_raw"
    assert blocks[1]["type"] == "note"


def test_eo_line_with_italic_ru_parenthetical_is_not_classified_as_example():
    text = """[без]
ankaux tio havas lokon en la afero; (_и это имеет место_)
ankaux tio ne estas neadebla;
"""
    blocks = _first_form_blocks(text)
    assert len(blocks) == 1
    assert blocks[0]["type"] == "text_raw"
    assert "ankaux tio ne estas neadebla;" in blocks[0]["raw"]
