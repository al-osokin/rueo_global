import json
from pathlib import Path

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Article
from app.parsing.parser_v4.pipeline import ParsingPipelineV4


FIXTURE = Path(__file__).parent / "fixtures" / "parser_v4_golden.json"
SMOKE_IDS = (1, 2, 3, 6, 56, 77)


def _fixture_rows():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return {row["art_id"]: row for row in data if row.get("art_id") in SMOKE_IDS}


def test_separator_token_is_kept_as_structural_token_and_blocks_merge_after_it():
    parsed = ParsingPipelineV4().parse_article(
        """[foo|i]
_первая строка
  продолжение
@
  после разделителя
"""
    )
    blocks = parsed["meta"]["v4_ast"]["forms"][0]["blocks"]

    assert blocks[0]["type"] == "note"
    assert "продолжение" in blocks[0]["raw"]

    assert blocks[1]["type"] == "separator"
    assert blocks[1]["raw"] == "@"

    assert blocks[2]["type"] == "text_raw"
    assert blocks[2]["raw"] == "после разделителя"


def test_tilde_expansion_for_a_and_ig_o_matches_abort_golden_cases():
    parsed = ParsingPipelineV4().parse_article(
        """[abort|i]
[~a]
[~ig/o]
"""
    )
    forms = parsed["meta"]["v4_ast"]["forms"]

    assert forms[0]["expanded"] == "aborti"
    assert forms[1]["expanded"] == "aborta"
    assert forms[2]["expanded"] == "abortigo"


def test_snapshot_ast_fixture_contains_expected_smoke_ids():
    rows = _fixture_rows()
    assert set(rows.keys()) == set(SMOKE_IDS)


def test_smoke_db_parse_matches_snapshot_ast_for_selected_ids():
    rows = _fixture_rows()
    pipeline = ParsingPipelineV4()

    with SessionLocal() as session:
        for art_id in SMOKE_IDS:
            text = session.execute(
                select(Article.priskribo).where(Article.art_id == art_id)
            ).scalar_one_or_none()
            assert text, f"missing article text for art_id={art_id}"

            parsed = pipeline.parse_article(text, index=art_id)
            assert parsed["headword"]["raw_form"] == rows[art_id]["headword"]
            assert parsed["meta"]["v4_ast"] == rows[art_id]["v4_ast"]
