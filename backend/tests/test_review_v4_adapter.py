import json
from pathlib import Path

from app.parsing.parser_v4.pipeline import ParsingPipelineV4
from app.services.translation_review import ReviewV4AstError, build_translation_review


FIXTURE = Path(__file__).parent / "fixtures" / "parser_v4_golden.json"


def _load_case(art_id: int):
    data = json.loads(FIXTURE.read_text())
    row = next(item for item in data if item["art_id"] == art_id)
    return {
        "headword": {"raw_form": row["headword"]},
        "meta": {"v4_ast": row["v4_ast"]},
        "body": [],
    }


def _example_blocks(art_id: int):
    data = json.loads(FIXTURE.read_text())
    row = next(item for item in data if item["art_id"] == art_id)
    blocks = []
    for form in row["v4_ast"].get("forms", []):
        for block in form.get("blocks", []):
            if block.get("type") == "example_raw":
                blocks.append(block)
    return blocks


def test_golden_fixture_examples_are_structured_for_3_6_and_56_boundaries():
    for art_id in (3, 6):
        blocks = _example_blocks(art_id)
        assert blocks, f"expected example_raw blocks for {art_id}"
        assert all(block.get("example_eo") for block in blocks)
        assert all(block.get("example_ru") for block in blocks)

    # В 56 примеров нет, но важно, что это действительно non-example кейс с ref-note.
    assert _example_blocks(56) == []


def test_v4_adapter_separates_examples_for_3_6_56(monkeypatch):
    monkeypatch.setenv("REVIEW_USE_PARSER_V4", "1")

    for art_id in (3, 6):
        review = build_translation_review(_load_case(art_id))
        assert review.groups, f"expected groups for {art_id}"

        has_example_group = any(g.eo_source for g in review.groups)
        assert has_example_group, f"expected eo_source example group for {art_id}"

    review_56 = build_translation_review(_load_case(56))
    assert review_56.groups
    # Для 56 важно, что note-отсылка не смешивается с переводом.
    assert any("ср." in note.lower() for note in review_56.notes)
    assert not any("ср." in item.lower() for g in review_56.groups for item in g.items)


def test_default_flag_off_keeps_old_behavior(monkeypatch):
    monkeypatch.delenv("REVIEW_USE_PARSER_V4", raising=False)
    review = build_translation_review(_load_case(3))
    # Без body старый поток не строит группы; это подтверждает, что флаг реально переключает путь.
    assert review.groups == []


def test_v4_adapter_maps_numbered_senses_and_scope_notes_for_77(monkeypatch):
    monkeypatch.setenv("REVIEW_USE_PARSER_V4", "1")

    parsed = ParsingPipelineV4().parse_article(
        """[abort|i]
{vn} 1. _мед._ в`ыкинуть плод, преждевр`еменно род`ить;
  _ср._ <akusxi>;
  2. _перен._ останов`иться в разв`итии;
    ~igi sin сд`елать (себе) аб`орт;
"""
    )
    review = build_translation_review(parsed)
    assert review.groups

    # Numbered senses are mapped into group labels for UI
    assert any((g.label or "").startswith("1.") for g in review.groups)
    assert any((g.label or "").startswith("2.") for g in review.groups)

    # Example groups preserve eo_source and sense-aware label
    assert any(g.eo_source and "пример" in (g.label or "") for g in review.groups)

    # Sense-scoped reference notes are preserved as notes, not translation items
    assert any("[1.]" in note and "ср." in note.lower() for note in review.notes)
    assert not any("ср." in item.lower() for g in review.groups for item in g.items)


def test_v4_only_mode_fails_fast_when_v4_ast_missing(monkeypatch):
    monkeypatch.setenv("REVIEW_USE_PARSER_V4", "1")
    parsed = {
        "headword": {"raw_form": "test"},
        "meta": {},
        "body": [{"type": "translation", "content": [{"type": "text", "text": "fallback"}]}],
    }

    try:
        build_translation_review(parsed)
        assert False, "expected ReviewV4AstError"
    except ReviewV4AstError as exc:
        assert exc.code == "missing_v4_ast"
        assert "meta.v4_ast" in str(exc)


def test_v4_only_mode_fails_fast_when_v4_ast_inconsistent(monkeypatch):
    monkeypatch.setenv("REVIEW_USE_PARSER_V4", "1")
    parsed = {
        "headword": {"raw_form": "test"},
        "meta": {"v4_ast": {"forms": [{"raw": "x", "blocks": "bad"}]}},
        "body": [],
    }

    try:
        build_translation_review(parsed)
        assert False, "expected ReviewV4AstError"
    except ReviewV4AstError as exc:
        assert exc.code == "invalid_v4_ast_blocks"
        assert "forms[0].blocks" in str(exc)


def test_v4_adapter_moves_trailing_parenthetical_explanations_to_notes_for_56(monkeypatch):
    monkeypatch.setenv("REVIEW_USE_PARSER_V4", "1")

    review = build_translation_review(_load_case(56))
    assert review.groups

    all_items = [item for g in review.groups for item in g.items]

    # base translation remains
    assert "разруш`ение" in all_items
    assert "сгор`ание" in all_items

    # parenthetical explanations should be notes, not duplicate translation items
    assert not any("разруш`ение (" in item for item in all_items)
    assert not any("сгор`ание (" in item for item in all_items)

    joined_notes = "\n".join(review.notes).lower()
    assert "под действием метеорологических факторов" in joined_notes
    assert "в атмосфере, вследствие радиации" in joined_notes


def test_v4_adapter_moves_trailing_parenthetical_explanations_to_notes_for_77(monkeypatch):
    monkeypatch.setenv("REVIEW_USE_PARSER_V4", "1")

    review = build_translation_review(_load_case(77))
    assert review.groups

    all_items = [item for g in review.groups for item in g.items]

    # base translation remains
    assert "лит. корнев`ая р`ифма" in all_items

    # parenthetical explanations should be notes, not duplicate translation items
    assert not any("лит. корнев`ая р`ифма (" in item for item in all_items)

    joined_notes = "\n".join(review.notes).lower()
    assert "в эсперанто называемая абортивной" in joined_notes
