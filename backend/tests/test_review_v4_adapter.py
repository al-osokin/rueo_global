import json
from pathlib import Path

from app.services.translation_review import build_translation_review


FIXTURE = Path(__file__).parent / "fixtures" / "parser_v4_golden.json"


def _load_case(art_id: int):
    data = json.loads(FIXTURE.read_text())
    row = next(item for item in data if item["art_id"] == art_id)
    return {
        "headword": {"raw_form": row["headword"]},
        "meta": {"v4_ast": row["v4_ast"]},
        "body": [],
    }


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
