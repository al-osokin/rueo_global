"""Modern text parsing for parser v3 - replaces legacy regex-based approach."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


# Сокращения, где точка НЕ является разделителем
ABBREVIATION_PATTERNS = [
    r'-л\.',      # что-л., кого-л., чего-л., где-л., куда-л.
    r'-то\.',     # что-то, кого-то
    r'\bт\.е\.',  # т.е.
    r'\bт\.п\.',  # т.п.
    r'\bи т\.д\.', # и т.д.
    r'\bи т\.п\.', # и т.п.
    r'\bи др\.',  # и др.
    r'\bср\.',    # ср.
    r'\bсм\.',    # см.
]

# Компилируем паттерны для быстрой проверки
ABBREVIATION_REGEX = re.compile('|'.join(ABBREVIATION_PATTERNS), re.IGNORECASE)


def is_abbreviation_context(text: str, position: int) -> bool:
    """Проверяет, находится ли точка в позиции position в контексте сокращения."""
    if position < 1 or position >= len(text):
        return False
    
    # Проверяем контекст вокруг точки (5 символов до, 2 после)
    start = max(0, position - 5)
    end = min(len(text), position + 3)
    context = text[start:end]
    
    # Проверяем по паттернам
    if ABBREVIATION_REGEX.search(context):
        return True
    
    # Дополнительная проверка: если перед точкой "-л" или "-то"
    if position >= 2:
        before = text[position-2:position]
        if before in ['-л', '-то']:
            return True
    
    # Проверка на однобуквенные сокращения: т., п., д.
    if position >= 1:
        before_char = text[position-1]
        if before_char in 'тпдср' and (position == 1 or text[position-2] in ' \t'):
            return True
    
    return False


def parse_rich_text(
    text: str,
    preserve_punctuation: bool = False,
    italic_open: bool = False
) -> List[Dict[str, Any]]:
    """
    Парсинг текста с разметкой - новая реализация без regex split.
    
    Args:
        text: Исходный текст с разметкой (_italic_, <link>, (note), {pos})
        preserve_punctuation: Если True, не создаёт divider узлы (для примечаний)
        italic_open: Начальное состояние italic (для продолжения текста)
    
    Returns:
        Список узлов: text, link, note, pos, divider
    """
    if not text:
        return []
    
    content: List[Dict[str, Any]] = []
    
    # Для preserve_punctuation - только обрабатываем курсив
    if preserve_punctuation:
        return _parse_italic_only(text, italic_open)
    
    # Основной парсинг
    i = 0
    current_text = ""
    italic = italic_open
    
    while i < len(text):
        char = text[i]
        
        # Обработка курсива
        if char == '_' and (i == 0 or text[i-1] != '\\'):
            if current_text:
                content.append({
                    'type': 'text',
                    'style': 'italic' if italic else 'regular',
                    'text': current_text
                })
                current_text = ""
            italic = not italic
            i += 1
            continue
        
        # Обработка ссылки <...>
        if char == '<':
            link_end = text.find('>', i + 1)
            if link_end != -1:
                if current_text:
                    content.append({
                        'type': 'text',
                        'style': 'italic' if italic else 'regular',
                        'text': current_text
                    })
                    current_text = ""
                
                link_content = text[i+1:link_end]
                content.append({
                    'type': 'link',
                    'text': link_content
                })
                i = link_end + 1
                continue
        
        # Обработка примечания (...)
        if char == '(':
            paren_end = text.find(')', i + 1)
            if paren_end != -1:
                note_content = text[i+1:paren_end]
                
                # Если содержимое слишком короткое (1 символ) - это не примечание
                if len(note_content.strip()) <= 1:
                    current_text += char
                    i += 1
                    continue
                
                if current_text:
                    content.append({
                        'type': 'text',
                        'style': 'italic' if italic else 'regular',
                        'text': current_text
                    })
                    current_text = ""
                
                content.append({
                    'type': 'note',
                    'text': note_content
                })
                i = paren_end + 1
                continue
        
        # Обработка части речи {...}
        if char == '{':
            brace_end = text.find('}', i + 1)
            if brace_end != -1:
                if current_text:
                    content.append({
                        'type': 'text',
                        'style': 'italic' if italic else 'regular',
                        'text': current_text
                    })
                    current_text = ""
                
                pos_content = text[i+1:brace_end]
                content.append({
                    'type': 'pos',
                    'text': pos_content
                })
                i = brace_end + 1
                continue
        
        # Обработка пунктуации (dividers)
        if char in ',;:.!?':
            # УМНАЯ обработка точки - проверяем, не сокращение ли это
            if char == '.' and is_abbreviation_context(text, i):
                # Это сокращение - не разделяем, добавляем к тексту
                current_text += char
                i += 1
                continue
            
            # Это разделитель
            if current_text:
                content.append({
                    'type': 'text',
                    'style': 'italic' if italic else 'regular',
                    'text': current_text
                })
                current_text = ""
            
            content.append({
                'type': 'divider',
                'text': char
            })
            i += 1
            continue
        
        # Обычный символ
        current_text += char
        i += 1
    
    # Добавляем остаток текста
    if current_text:
        content.append({
            'type': 'text',
            'style': 'italic' if italic else 'regular',
            'text': current_text
        })
    
    return content


def _parse_italic_only(text: str, italic_open: bool = False) -> List[Dict[str, Any]]:
    """Парсинг только курсива, без разделителей (для preserve_punctuation=True)."""
    content: List[Dict[str, Any]] = []
    
    # Особый случай: весь текст обрамлён в "_"
    if text.startswith('_') and text.endswith('_') and len(text) > 2:
        italic_text = text[1:-1]
        content.append({
            'type': 'text',
            'style': 'italic',
            'text': italic_text
        })
        return content
    
    # Обычный случай: переключение курсива на "_"
    i = 0
    current_text = ""
    italic = italic_open
    
    while i < len(text):
        char = text[i]
        
        if char == '_' and (i == 0 or text[i-1] != '\\'):
            if current_text:
                content.append({
                    'type': 'text',
                    'style': 'italic' if italic else 'regular',
                    'text': current_text
                })
                current_text = ""
            italic = not italic
        else:
            current_text += char
        
        i += 1
    
    if current_text:
        content.append({
            'type': 'text',
            'style': 'italic' if italic else 'regular',
            'text': current_text
        })
    
    return content


def parse_headword(line: str) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Парсинг заголовка статьи вида [aer|o] или [~a].
    
    Args:
        line: Строка заголовка
    
    Returns:
        Кортеж (headword_dict, remainder_text)
        headword_dict содержит: raw_form, lemmas, official_mark, homonym
    """
    line = line.strip()
    
    if not line.startswith('['):
        return None, line
    
    # Найти закрывающую скобку
    bracket_end = line.find(']')
    if bracket_end == -1:
        return None, line
    
    raw_form = line[:bracket_end + 1]
    remainder = line[bracket_end + 1:].lstrip()
    
    # Извлечь содержимое между скобками
    inside = raw_form[1:-1].strip()
    if not inside:
        return None, remainder
    
    # Разбор лемм (разделённых запятыми или слэшами)
    lemmas: List[Dict[str, str]] = []
    official_mark = None
    homonym = None
    
    # Проверка на официальную отметку *
    if inside.startswith('*'):
        official_mark = True
        inside = inside[1:].lstrip()
    
    # Проверка на номер омонима (цифра после пробела в конце)
    homonym_match = re.search(r'\s+(\d+)$', inside)
    if homonym_match:
        homonym = int(homonym_match.group(1))
        inside = inside[:homonym_match.start()].strip()
    
    # Разделение на леммы
    # Сначала по запятым (для случаев типа [A, a])
    if ',' in inside:
        parts = [p.strip() for p in inside.split(',')]
    else:
        # Иначе считаем одну лемму (может содержать | для корня и окончания)
        parts = [inside]
    
    for part in parts:
        if part:
            lemmas.append({
                'lemma': part,
                'raw': part
            })
    
    headword = {
        'raw_form': raw_form,
        'lemmas': lemmas
    }
    
    if official_mark is not None:
        headword['official_mark'] = official_mark
    if homonym is not None:
        headword['homonym'] = homonym
    
    return headword, remainder


def split_ru_segments(parts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Преобразование parse_rich_text() результата в русские сегменты.
    
    Args:
        parts: Результат parse_rich_text()
    
    Returns:
        Список сегментов с полями: text, kind (term/label/reference/link/note/divider)
    """
    segments: List[Dict[str, Any]] = []
    
    label_modes = {
        'см': 'see',
        'см.': 'see',
        'ср': 'compare',
        'ср.': 'compare'
    }
    
    active_reference_mode: Optional[str] = None
    pending_label_segment: Optional[Dict[str, Any]] = None
    
    for part in parts:
        part_type = part.get('type')
        
        if part_type == 'text':
            raw_text = part.get('text', '')
            if not raw_text:
                continue
            text = raw_text.strip()
            if not text:
                continue
            
            style = part.get('style', 'regular')
            
            # Проверка на метки-ссылки (см., ср.)
            if style == 'italic' and text in label_modes:
                mode = label_modes[text]
                label_segment: Dict[str, Any] = {
                    'text': text,
                    'kind': 'reference',
                    'mode': mode
                }
                segments.append(label_segment)
                active_reference_mode = mode
                pending_label_segment = label_segment
                continue
            
            # Обычный термин
            segments.append({'text': text, 'kind': 'term'})
            active_reference_mode = None
            pending_label_segment = None
        
        elif part_type == 'divider':
            divider = part.get('text', '')
            if divider:
                # Если есть pending label "см" и divider - это точка, присоединяем
                if pending_label_segment and divider == '.':
                    pending_label_segment['text'] += '.'
                    pending_label_segment = None
                    continue
                
                # Определяем тип divider
                kind = _categorize_divider(divider)
                segments.append({'text': divider, 'kind': kind})
                
                # Точка/восклицательный/вопросительный сбрасывают режим ссылки
                if divider in '.!?':
                    active_reference_mode = None
                
                pending_label_segment = None
        
        elif part_type == 'link':
            target = part.get('text', '').strip()
            if target:
                segment: Dict[str, Any] = {
                    'text': target,
                    'kind': 'link',
                    'target': target
                }
                if active_reference_mode:
                    segment['mode'] = active_reference_mode
                segments.append(segment)
            pending_label_segment = None
        
        elif part_type == 'note':
            note_text = part.get('text', '').strip()
            if note_text:
                segments.append({'text': note_text, 'kind': 'note'})
            pending_label_segment = None
    
    return segments


def _categorize_divider(symbol: str) -> str:
    """Определяет тип разделителя."""
    if symbol == ',':
        return 'near_divider'
    elif symbol == ';':
        return 'far_divider'
    elif symbol == '.':
        return 'sentence_divider'
    elif symbol in ':':
        return 'phrase_divider'
    elif symbol in '!?':
        return 'sentence_divider'
    else:
        return 'divider'


def preprocess_text(text: str) -> str:
    """
    Предобработка текста статьи.
    
    Удаляет лишние пробелы, нормализует переносы строк.
    """
    if not text:
        return ""
    
    # Нормализация переносов строк
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # Удаление trailing пробелов на каждой строке
    lines = [line.rstrip() for line in text.split('\n')]
    
    return '\n'.join(lines)
