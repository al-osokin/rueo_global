from app.parsing.parser_v4.pipeline import ParsingPipelineV4


def test_v4_returns_minimal_payload_without_v3_pipeline_shape():
    text = """[ab-]\n_спец. приставка_ аб-:\n  ab/ampero абампер;\n"""
    parsed = ParsingPipelineV4().parse_article(text, index=42)

    assert parsed["meta"]["parser_engine"] == "v4"
    assert parsed["meta"]["parse_index"] == 42
    assert isinstance(parsed["meta"]["v4_ast"], dict)

    assert parsed["headword"]["raw_form"] == "[ab-]"
    assert parsed["body"]
    assert parsed["body"][0]["type"] == "headword"
    assert parsed["body"][0]["children"]
