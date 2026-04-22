import json
from pathlib import Path

from app.parsing.parser_v4.pipeline import ParsingPipelineV4


FIXTURE = Path(__file__).parent / "fixtures" / "parser_v4_mini_regression.json"


def _cases():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _project_block(block: dict, expected_block: dict) -> dict:
    # Compare only keys declared in expected fixture to keep tests stable
    # while still asserting important semantic fields.
    return {key: block.get(key) for key in expected_block.keys()}


def test_mini_regression_fixture_is_non_empty_and_ids_unique():
    cases = _cases()
    assert cases, "mini regression fixture is empty"

    ids = [case["id"] for case in cases]
    assert len(ids) == len(set(ids)), "fixture case ids must be unique"


def test_parser_v4_mini_regression_cases_match_expected_blocks():
    pipeline = ParsingPipelineV4()

    for case in _cases():
        parsed = pipeline.parse_article(case["article_text"])
        blocks = parsed["meta"]["v4_ast"]["forms"][0]["blocks"]

        expected_blocks = case["expected_blocks"]
        assert len(blocks) == len(expected_blocks), case["id"]

        projected_actual = [
            _project_block(block, expected)
            for block, expected in zip(blocks, expected_blocks)
        ]
        assert projected_actual == expected_blocks, case["id"]
