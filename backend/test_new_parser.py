"""Тестирование нового text_parser.py"""

import sys
sys.path.insert(0, '/home/avo/rueo_global/backend')

from app.parsing.parser_v3.text_parser import (
    parse_rich_text,
    parse_headword,
    split_ru_segments,
    is_abbreviation_context
)


def test_abbreviations():
    """Тест на правильную обработку сокращений"""
    print("=== Тест 1: Сокращения ===")
    
    # Тест 1: что-л.
    text1 = "д`елать что-л. неест`ественно"
    result1 = parse_rich_text(text1)
    print(f"\nВход: {text1}")
    print(f"Результат:")
    for node in result1:
        print(f"  {node}")
    
    # Проверка: точка должна быть в тексте "что-л.", а не отдельным divider
    text_nodes = [n for n in result1 if n['type'] == 'text']
    has_abbreviation = any('что-л.' in n.get('text', '') for n in text_nodes)
    print(f"✓ Сокращение 'что-л.' сохранено: {has_abbreviation}")
    
    # Тест 2: т.е.
    text2 = "_т.е._ равнод`ушный"
    result2 = parse_rich_text(text2)
    print(f"\nВход: {text2}")
    print(f"Результат:")
    for node in result2:
        print(f"  {node}")


def test_exclamation():
    """Тест на восклицательные знаки"""
    print("\n=== Тест 2: Восклицательные знаки ===")
    
    text = "не лом`айся!"
    result = parse_rich_text(text)
    print(f"\nВход: {text}")
    print(f"Результат:")
    for node in result:
        print(f"  {node}")
    
    # Восклицательный знак должен быть отдельным divider
    dividers = [n for n in result if n['type'] == 'divider']
    has_exclamation = any(n.get('text') == '!' for n in dividers)
    print(f"✓ Восклицательный знак как divider: {has_exclamation}")


def test_headword():
    """Тест на разбор заголовков"""
    print("\n=== Тест 3: Заголовки ===")
    
    tests = [
        "[aer|o] * 1. {vt} воздух",
        "[~a] воздушный",
        "[A, a] буква А",
    ]
    
    for line in tests:
        headword, remainder = parse_headword(line)
        print(f"\nВход: {line}")
        print(f"Headword: {headword}")
        print(f"Remainder: {remainder}")


def test_article_383():
    """Тест на реальную статью 383"""
    print("\n=== Тест 4: Статья 383 (фрагмент) ===")
    
    text = "аффект`ировать, д`елать что-л. неест`ественно"
    result = parse_rich_text(text)
    
    print(f"\nВход: {text}")
    print(f"Узлов: {len(result)}")
    for i, node in enumerate(result):
        print(f"  {i}. {node}")
    
    # Собираем обратно текст (без dividers для наглядности)
    reconstructed = []
    for node in result:
        if node['type'] == 'text':
            reconstructed.append(node['text'])
        elif node['type'] == 'divider':
            reconstructed.append(f" [{node['text']}] ")
    
    print(f"\nРеконструированный: {''.join(reconstructed)}")
    
    # Проверка: должно быть "что-л." с точкой
    text_content = ' '.join(n['text'] for n in result if n['type'] == 'text')
    if 'что-л.' in text_content:
        print("✓ Сокращение 'что-л.' НЕ разбито")
    else:
        print("✗ ОШИБКА: Сокращение 'что-л.' разбито!")


def test_context_detection():
    """Тест функции определения контекста сокращения"""
    print("\n=== Тест 5: Определение контекста сокращения ===")
    
    tests = [
        ("делать что-л. неестественно", 15, True),   # Позиция точки в "что-л."
        ("т.е. равнодушный", 3, True),               # Позиция точки в "т.е."
        ("Это предложение. Новое предложение", 15, False),  # Обычная точка
        ("См. <ventoli>", 2, True),                  # "см."
    ]
    
    for text, pos, expected in tests:
        result = is_abbreviation_context(text, pos)
        status = "✓" if result == expected else "✗"
        print(f"{status} '{text}' [pos={pos}]: {result} (ожидалось {expected})")


if __name__ == '__main__':
    test_context_detection()
    test_abbreviations()
    test_exclamation()
    test_headword()
    test_article_383()
    
    print("\n" + "="*60)
    print("Тестирование завершено!")
