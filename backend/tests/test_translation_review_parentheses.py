from app.services.translation_review import _expand_parenthetical_forms


def test_inword_optional_without_space_expands_word_variants():
    variants = _expand_parenthetical_forms("(с)делать")
    assert "делать" in variants
    assert "сделать" in variants


def test_token_optional_with_space_expands_segment_variants():
    variants = _expand_parenthetical_forms("анализ (крови) на диабет")
    assert "анализ на диабет" in variants
    assert "анализ крови на диабет" in variants


def test_inword_suffix_optional():
    variants = _expand_parenthetical_forms("орангутан(г)")
    assert "орангутан" in variants
    assert "орангутанг" in variants
