#!/usr/bin/env python3
"""
Парсер словаря эсперанто v2.0 - ОЧИЩЕННАЯ ВЕРСИЯ
Реализация по спецификации PROJECT_MEMORY_250916.md
"""

import re
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# --- КОНФИГУРАЦИЯ ---
PARSER_VERSION = "2.0"
INPUT_FILENAME = "test_articles.txt"
OUTPUT_FILENAME = "output.json"
LOG_FILENAME = "parser_log.txt"
SHORTENINGS_FILE = "shortenings.txt"
ABBREVIATIONS_FILE = "w.txt"

# Debug options
DEBUG_MODE = True

# Настройки поведения (можно переключать при отладке)
ENABLE_PARAGRAPH_BREAKS = False

# Глобальные переменные для логов
parsing_issues = []
KNOWN_SHORTENINGS: Dict[str, str] = {}
BUILTIN_LABELS = {
    'мед', 'цер', 'воен', 'ист', 'фин', 'псих', 'архит', 'анат', 'энт', 'зоол', 'ихт', 'уст', 'гп', 'мат'
}
LOGGED_UNKNOWN_LABELS: set[str] = set()

def log_issue(issue_type: str, message: str, context: str = ""):
    """Логирование проблемы парсинга"""
    issue = {
        'type': issue_type,
        'message': message,
        'context': context,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    parsing_issues.append(issue)

def load_shortenings() -> Dict[str, str]:
    """Загрузка словаря сокращений"""
    shortenings = {}
    try:
        # Файл сокращений в кодировке Windows-1251
        with open(SHORTENINGS_FILE, 'r', encoding='windows-1251') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Парсим формат "сокр. - [расшифровка]"
                    if ' - ' in line:
                        abbr, full = line.split(' - ', 1)
                        key = re.sub(r"[`'\s]", "", abbr.strip().strip('.').lower())
                        shortenings[key] = full.strip()
    except FileNotFoundError:
        log_issue('file_missing', f'Файл сокращений не найден: {SHORTENINGS_FILE}')
    except Exception as e:
        log_issue('file_error', f'Ошибка чтения файла сокращений: {e}')

    return shortenings

def save_log():
    """Сохранение лога проблем"""
    if parsing_issues:
        with open(LOG_FILENAME, 'w', encoding='utf-8') as f:
            json.dump({
                'meta': {
                    'parser_version': PARSER_VERSION,
                    'total_issues': len(parsing_issues),
                    'generated_at': datetime.now(timezone.utc).isoformat()
                },
                'issues': parsing_issues
            }, f, ensure_ascii=False, indent=2)
        print(f"Лог проблем сохранён в {LOG_FILENAME} ({len(parsing_issues)} проблем)")

# --- ПРЕДВАРИТЕЛЬНАЯ ОБРАБОТКА ---

def normalize_encoding(text: str) -> str:
    """Нормализация кодировки из Windows-1251 в UTF-8"""
    # Замена x-системы на диакритику
    replacements = {
        'cx': 'ĉ', 'gx': 'ĝ', 'hx': 'ĥ', 'jx': 'ĵ', 'sx': 'ŝ', 'ux': 'ŭ',
        'Cx': 'Ĉ', 'Gx': 'Ĝ', 'Hx': 'Ĥ', 'Jx': 'Ĵ', 'Sx': 'Ŝ', 'Ux': 'Ŭ'
    }
    for x_form, unicode_form in replacements.items():
        text = text.replace(x_form, unicode_form)
    return text

def preprocess_text(text: str) -> str:
    """Предварительная обработка текста"""
    # Нормализация кодировки
    text = normalize_encoding(text)

    # Замена специальных символов
    text = text.replace('<<', '«')  # Кавычки-елочки
    text = text.replace('>>', '»')
    text = text.replace('--', '—')  # Тире
    # ,, оставляем как есть - это divider для дальних синонимов

    # Удаление комментариев !!!
    text = re.sub(r'!!!.*$', '', text, flags=re.MULTILINE)

    # Удаление двойных фигурных скобок с содержимым
    text = re.sub(r'\{\{.*?\}\}', '', text)

    return text

# --- СТРУКТУРНЫЕ ФУНКЦИИ ---

def build_raw_tree(lines: List[str]) -> List[Dict]:
    """Шаг 1: Построение сырого дерева по отступам"""
    root_nodes = []
    stack = []

    for line in lines:
        if not line.strip():
            continue

        # Определение уровня отступа
        indent_level = 0
        for char in line:
            if char == '\t':
                indent_level += 1
            elif char == ' ':
                pass
            else:
                break

        if indent_level == 0:
            space_count = 0
            for char in line:
                if char == ' ':
                    space_count += 1
                else:
                    break
            indent_level = space_count // 4

        node = {
            'text': line.strip(),
            'indent': indent_level,
            'children': []
        }

        # Проверяем, является ли текущая строка пронумерованным определением
        is_numbered = re.match(r'^\d+\.\s+', node['text']) is not None
        
        # Pop из stack, пока indent предыдущего >= текущего
        while stack and stack[-1]['indent'] >= indent_level:
            stack.pop()
        
        # Если текущая строка - numbered translation,
        # ищем в stack последний numbered translation и делаем pop до него
        # Это гарантирует, что numbered translations будут siblings, а не nested
        if is_numbered and stack:
            # Ищем последний numbered node в stack
            for i in range(len(stack) - 1, -1, -1):
                if re.match(r'^\d+\.\s+', stack[i]['text']):
                    # Нашли numbered node - делаем pop до него (не включая его)
                    while len(stack) > i:
                        stack.pop()
                    break

        if stack:
            stack[-1]['children'].append(node)
        else:
            root_nodes.append(node)

        stack.append(node)

    return root_nodes

def stitch_multiline_italic_blocks(tree: List[Dict], italic_open: bool = False) -> List[Dict]:
    """Шаг 2: Склейка многострочных курсивных блоков"""
    def stitch_recursive(nodes: List[Dict], italic_open: bool = False, in_note_context: bool = False) -> List[Dict]:
        result = []
        note_context_active = in_note_context
        italic_state_open = italic_open

        for idx, node in enumerate(nodes):
            current_text = node['text']
            current_indent = node['indent']

            node['italic_open_before'] = italic_state_open

            is_note_start = '_прим.' in current_text
            is_structural_line = (
                current_text.startswith('[') or
                re.match(r'^\d+\.', current_text) is not None or
                current_text.startswith('@')
            )

            node['note_context'] = note_context_active or is_note_start

            current_note_context = note_context_active or is_note_start
            should_stitch = False

            if result:
                prev_node = result[-1]
                same_indent = prev_node['indent'] == current_indent
                if same_indent and italic_state_open and not is_structural_line:
                    should_stitch = True
                
                # Проверка на продолжение иллюстрации с большим отступом
                if not should_stitch and current_indent > prev_node['indent']:
                    prev_text = prev_node['text'].strip()
                    current_stripped = current_text.strip()
                    
                    if DEBUG_MODE and current_indent == 2 and prev_node['indent'] == 1:
                        log_issue('debug_indent_check',
                                f"Found continuation candidate: prev_indent={prev_node['indent']}, "
                                f"current_indent={current_indent}, "
                                f"prev_text={repr(prev_text[:80])}, "
                                f"current_text={repr(current_stripped[:80])}")
                    
                    # Предыдущая строка должна содержать и латиницу и кириллицу (иллюстрация)
                    has_latin = any('a' <= c <= 'z' or 'A' <= c <= 'Z' for c in prev_text)
                    has_cyrillic = any('\u0400' <= c <= '\u04FF' for c in prev_text)
                    # Текущая строка начинается с кириллицы или подчёркиванием с кириллицей
                    starts_with_cyrillic = False
                    if current_stripped:
                        first_char = current_stripped.lstrip('_')[0] if current_stripped.lstrip('_') else ''
                        starts_with_cyrillic = first_char and '\u0400' <= first_char <= '\u04FF'
                    
                    if DEBUG_MODE and has_latin and has_cyrillic:
                        log_issue('debug_stitch_check', 
                                f"Checking continuation: prev_indent={prev_node['indent']}, "
                                f"current_indent={current_indent}, "
                                f"starts_with_cyrillic={starts_with_cyrillic}, "
                                f"current_text={current_text[:50]}")
                    
                    if has_latin and has_cyrillic and starts_with_cyrillic and not is_structural_line:
                        should_stitch = True

            underscores = count_unescaped_underscores(current_text)
            next_italic_state = italic_state_open
            if underscores % 2 == 1:
                next_italic_state = not next_italic_state

            if should_stitch:
                target_node = result[-1]
                joiner = '' if target_node['text'].endswith('\n') else ' '
                newline_after = False
                stripped_text = current_text.rstrip()
                trimmed_current = current_text.lstrip()
                prev_text = target_node['text'].rstrip()
                apply_breaks = ENABLE_PARAGRAPH_BREAKS or current_note_context or italic_state_open
                if apply_breaks and italic_state_open and trimmed_current:
                    if prev_text and prev_text[-1] in '.?!' and trimmed_current[0].isupper():
                        joiner = '\n'
                        prev_text = prev_text.rstrip()
                    elif len(stripped_text) < 30 and stripped_text.endswith(('.', '!', '?')):
                        newline_after = True
                base_text = target_node['text'] if joiner == '' else prev_text
                target_node['text'] = base_text + joiner + trimmed_current
                if apply_breaks and newline_after and idx + 1 < len(nodes) and not target_node['text'].endswith('\n'):
                    target_node['text'] += '\n'
                stitched_children = stitch_recursive(
                    node['children'],
                    next_italic_state,
                    current_note_context
                )
                target_node['children'].extend(stitched_children)
            else:
                node['children'] = stitch_recursive(
                    node['children'],
                    next_italic_state,
                    current_note_context
                )
                
                # Проверяем, нужно ли приклеить первого ребёнка к родителю (продолжение иллюстрации)
                if node['children'] and current_indent > 0:
                    first_child = node['children'][0]
                    parent_text = node['text'].strip()
                    child_text = first_child['text'].strip()
                    
                    # Не применяем для numbered translations (они уже обработаны)
                    parent_is_numbered = re.match(r'^\d+\.\s+', parent_text) is not None
                    
                    if not parent_is_numbered:
                        # Родитель должен содержать и латиницу и кириллицу (иллюстрация)
                        has_latin = any('a' <= c <= 'z' or 'A' <= c <= 'Z' for c in parent_text)
                        has_cyrillic = any('\u0400' <= c <= '\u04FF' for c in parent_text)
                        # Ребёнок начинается с кириллицы
                        starts_with_cyrillic = False
                        if child_text:
                            first_char = child_text.lstrip('_')[0] if child_text.lstrip('_') else ''
                            starts_with_cyrillic = first_char and '\u0400' <= first_char <= '\u04FF'
                        
                        if has_latin and has_cyrillic and starts_with_cyrillic:
                            # Склеиваем родителя с первым ребёнком
                            node['text'] = node['text'].rstrip() + ' ' + first_child['text'].lstrip()
                            # Переносим children ребёнка к родителю и удаляем первого ребёнка
                            node['children'] = first_child['children'] + node['children'][1:]
                
                result.append(node)

            target_node = result[-1]

            if next_italic_state and target_node['children']:
                while target_node['children']:
                    child_candidate = target_node['children'][0]
                    if should_merge_child_with_parent(target_node, child_candidate, next_italic_state):
                        joiner = '' if target_node['text'].endswith('\n') else ' '
                        base_text = target_node['text'] if joiner == '' else target_node['text'].rstrip()
                        trimmed_child = child_candidate['text'].lstrip()
                        if trimmed_child and base_text.rstrip() and base_text.rstrip()[-1] in '.?!' and trimmed_child[0].isupper():
                            joiner = '\n'
                            base_text = base_text.rstrip()
                        target_node['text'] = base_text + joiner + trimmed_child
                        child_underscores = count_unescaped_underscores(child_candidate['text'])
                        if child_underscores % 2 == 1:
                            next_italic_state = not next_italic_state
                        target_node['children'] = child_candidate['children'] + target_node['children'][1:]
                    else:
                        break

            if is_note_start:
                note_context_active = True
            elif is_structural_line:
                note_context_active = False

            italic_state_open = next_italic_state

        return result

    return stitch_recursive(tree, italic_open=italic_open)

def is_italic_block_open(text: str) -> bool:
    """Проверяет, открыт ли курсивный блок в тексте"""
    return '_' in text

def is_italic_block_closed(text: str) -> bool:
    """Проверяет, закрыт ли курсивный блок в тексте"""
    if text.endswith('_'):
        return True
    underscore_count = text.count('_')
    return underscore_count % 2 == 0


def count_unescaped_underscores(text: str) -> int:
    """Подсчёт подчёркиваний, не экранированных обратной косой"""
    count = 0
    escaped = False
    for char in text:
        if escaped:
            escaped = False
            continue
        if char == '\\':
            escaped = True
        elif char == '_':
            count += 1
    return count


def merge_punctuation_with_italic(content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Присоединение завершающих знаков препинания к курсивному блоку"""
    if not content:
        return content

    merged: List[Dict[str, Any]] = []
    for segment in content:
        if (
            merged and
            segment.get('type') == 'text' and
            segment.get('style') == 'regular' and
            segment.get('text') and
            all(ch in ',;:.!?—' for ch in segment['text']) and
            merged[-1].get('type') == 'text' and
            merged[-1].get('style') == 'italic'
        ):
            merged[-1]['text'] += segment['text']
        else:
            merged.append(segment)

    return merged


def absorb_parentheses_into_italic(content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Перенос круглых скобок к соседнему курсивному сегменту"""
    i = 0
    while i < len(content):
        segment = content[i]
        if segment.get('type') != 'text' or segment.get('style') != 'italic':
            i += 1
            continue

        # Перенос скобок слева
        if i > 0:
            prev = content[i - 1]
            if prev.get('type') == 'text':
                text = prev.get('text', '')
                idx_open = text.rfind('(')
                if idx_open != -1 and text[idx_open:].strip() == '(':
                    transfer = text[idx_open:]
                    remaining = text[:idx_open]
                    if remaining:
                        prev['text'] = remaining
                    else:
                        content.pop(i - 1)
                        i -= 1
                    segment['text'] = transfer + segment['text']
                    continue

                idx_close = text.rfind(')')
                if idx_close != -1 and text[idx_close:].strip() == ')':
                    transfer = text[idx_close:]
                    remaining = text[:idx_close]
                    if remaining:
                        prev['text'] = remaining
                    else:
                        content.pop(i - 1)
                        i -= 1
                    segment['text'] = transfer + segment['text']
                    continue

        # Перенос скобок справа
        if i + 1 < len(content):
            nxt = content[i + 1]
            if nxt.get('type') == 'text':
                text = nxt.get('text', '')
                stripped = text.lstrip()
                if stripped.startswith(')'):
                    leading_spaces = text[:len(text) - len(stripped)]
                    close_idx = stripped.find(')')
                    transfer = leading_spaces + stripped[:close_idx + 1]
                    segment['text'] += transfer
                    remainder = stripped[close_idx + 1:]
                    if remainder:
                        nxt['text'] = remainder
                    else:
                        content.pop(i + 1)
                    continue

        i += 1

    return content


def merge_consecutive_text_segments(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    for item in segments:
        if (
            item.get('type') == 'text'
            and merged
            and merged[-1].get('type') == 'text'
            and merged[-1].get('style') == item.get('style')
        ):
            next_text = item.get('text', '')
            if next_text:
                prev_text = merged[-1].get('text', '')
                if prev_text and not prev_text[-1].isspace() and next_text and next_text[0] not in ',.;:)]?!»':
                    merged[-1]['text'] += ' '
                merged[-1]['text'] += next_text
        else:
            merged.append(item)
    return merged


def split_translation_segments(segments: List[Dict[str, Any]], *, allow_italic_in_translation: bool = False) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Выделение частей перевода, пояснений и отраслевых помет"""
    translation_parts: List[Dict[str, Any]] = []
    explanation_parts: List[Dict[str, Any]] = []
    labels: List[Dict[str, Any]] = []

    for segment in segments:
        text_val = segment.get('text', '')
        seg_type = segment.get('type')

        if seg_type == 'note':
            note_text = segment.get('text', '').strip('_')
            if note_text:
                explanation_parts.append({
                    'type': 'text',
                    'style': 'italic',
                    'text': f'({note_text})'
                })
            continue

        if seg_type == 'divider':
            translation_parts.append({'type': 'divider', 'text': text_val})
            continue

        if segment.get('style') == 'italic':
            stripped = text_val.strip()
            if stripped.startswith('(') and stripped.endswith(')'):
                explanation_parts.append({'type': 'text', 'style': 'italic', 'text': stripped})
                continue
            if stripped in {',', ';', ':', '.', '!', '?'}:
                translation_parts.append({'type': 'divider', 'text': stripped})
                continue

            core = stripped.rstrip('.')
            if stripped and core and len(core) <= 6 and ' ' not in core:
                if any(ch in '()[]{}' for ch in stripped):
                    translation_parts.append({'type': 'text', 'style': 'italic', 'text': stripped})
                else:
                    label_entry = {'type': 'label', 'text': stripped}
                    labels.append(label_entry)
                    translation_parts.append(label_entry)
                    register_label(stripped)
                continue

            if allow_italic_in_translation and stripped:
                translation_parts.append({'type': 'text', 'style': 'italic', 'text': stripped})
            elif stripped:
                explanation_parts.append({'type': 'text', 'style': 'italic', 'text': stripped})
            continue

        if seg_type == 'text':
            cleaned_text = text_val.strip()
            if cleaned_text:
                translation_parts.append({'type': 'text', 'style': segment.get('style', 'regular'), 'text': cleaned_text})
            continue

        translation_parts.append(segment)

    return translation_parts, explanation_parts, labels


def categorize_divider(divider: str) -> str:
    if divider == ',':
        return 'near_divider'
    if divider == ';':
        return 'far_divider'
    if divider in ('.', '!', '?'):
        return 'sentence_divider'
    if divider == ':':
        return 'phrase_divider'
    return 'divider'


def extract_sentence_ending(parts: List[Dict[str, Any]]) -> str:
    if not parts:
        return ''
    last = parts[-1]
    text = last.get('text', '').strip()
    if not text or any(ch not in '.!?' for ch in text):
        return ''
    if last.get('type') in ('divider', 'text'):
        parts.pop()
        return text
    return ''


def parse_headword_remainder(text: str, *, is_morpheme: bool = False) -> List[Dict[str, Any]]:
    stripped = text.strip()
    if not is_morpheme:
        numbered_match = re.match(r'^(\d+)\.\s*(.*)', stripped)
        if numbered_match:
            number = int(numbered_match.group(1))
            remainder_text = numbered_match.group(2)
            remainder_nodes = parse_headword_remainder(remainder_text, is_morpheme=False)
            if remainder_nodes:
                remainder_nodes[0]['number'] = number
            return remainder_nodes

    sentence_ending = ''
    while stripped and stripped[-1] in '.?!' and (len(stripped) == 1 or stripped[-2] != '\\'):
        sentence_ending = stripped[-1] + sentence_ending
        stripped = stripped[:-1].rstrip()

    if not stripped:
        return [{'type': 'sentence_divider', 'text': sentence_ending}] if sentence_ending else []

    segments = parse_rich_text(stripped, preserve_punctuation=True)
    segments = merge_punctuation_with_italic(segments)
    segments = absorb_parentheses_into_italic(segments)

    if is_morpheme:
        explanation_content: List[Dict[str, Any]] = []
        for segment in segments:
            seg_type = segment.get('type')
            if seg_type == 'note':
                explanation_content.append({
                    'type': 'text',
                    'style': 'italic',
                    'text': f"({segment.get('text', '').strip('_')})"
                })
            elif seg_type == 'divider':
                explanation_content.append({
                    'type': 'text',
                    'style': 'regular',
                    'text': segment.get('text', '')
                })
            else:
                text_value = segment.get('text', '')
                style_value = segment.get('style', 'regular')
                if text_value.strip() in {',', ';', ':', '.', '!', '?'}:
                    style_value = 'regular'
                explanation_content.append({
                    'type': 'text',
                    'style': style_value,
                    'text': text_value
                })
        explanation_content = merge_consecutive_text_segments(explanation_content)
        nodes = [{'type': 'explanation', 'content': explanation_content}]
        if sentence_ending:
            nodes.append({'type': 'sentence_divider', 'text': sentence_ending})
        return nodes

    nodes: List[Dict[str, Any]] = []
    current_translation: Optional[Dict[str, Any]] = None
    current_explanation: Optional[Dict[str, Any]] = None
    reference_targets: List[str] = []
    reference_mode: Optional[str] = None
    pending_reference_label: Optional[str] = None

    def ensure_translation() -> Dict[str, Any]:
        nonlocal current_translation
        if current_translation is None:
            current_translation = {'type': 'translation', 'content': []}
            nodes.append(current_translation)
        return current_translation

    def close_translation():
        nonlocal current_translation
        if current_translation and not current_translation['content']:
            nodes.remove(current_translation)
        current_translation = None

    def ensure_explanation() -> Dict[str, Any]:
        nonlocal current_explanation
        if current_explanation is None:
            current_explanation = {'type': 'explanation', 'content': []}
            nodes.append(current_explanation)
        return current_explanation

    def close_explanation():
        nonlocal current_explanation
        if current_explanation and not current_explanation['content']:
            nodes.remove(current_explanation)
        current_explanation = None

    def flush_reference():
        nonlocal reference_targets, reference_mode, pending_reference_label
        if reference_targets:
            reference_node: Dict[str, Any] = {
                'type': 'reference',
                'mode': reference_mode or 'link',
                'targets': reference_targets[:]
            }
            if pending_reference_label:
                reference_node['text'] = pending_reference_label
            nodes.append(reference_node)
            reference_targets = []
            reference_mode = None
            pending_reference_label = None

    for segment in segments:
        seg_type = segment.get('type')
        text_val = segment.get('text', '')

        if seg_type == 'note':
            close_translation()
            close_explanation()
            note_text = text_val.strip('_').strip()
            if note_text:
                if not note_text.startswith('('):
                    note_text = f'({note_text})'
                nodes.append({
                    'type': 'note',
                    'content': [{
                        'type': 'text',
                        'style': 'italic',
                        'text': note_text
                    }]
                })
            continue

        if seg_type == 'link':
            close_explanation()
            reference_targets.append(text_val)
            continue

        if seg_type == 'divider':
            divider_text = text_val
            if not divider_text:
                continue
            if divider_text in '.!?;':
                sentence_ending = divider_text
                flush_reference()
                close_translation()
                close_explanation()
            else:
                if current_translation is None:
                    continue
                ensure_translation()['content'].append({'type': 'text', 'style': 'regular', 'text': divider_text})
            continue

        if segment.get('style') == 'italic':
            stripped = text_val.strip()
            if stripped.startswith('(') and stripped.endswith(')'):
                close_translation()
                close_explanation()
                nodes.append({
                    'type': 'note',
                    'content': [{
                        'type': 'text',
                        'style': 'italic',
                        'text': stripped
                    }]
                })
                continue
            if stripped in {'см.', 'см', 'см.'}:
                flush_reference()
                close_translation()
                close_explanation()
                reference_mode = 'see'
                pending_reference_label = stripped
                continue
            if stripped in {'ср.', 'ср'}:
                flush_reference()
                close_translation()
                close_explanation()
                reference_mode = 'compare'
                pending_reference_label = stripped
                continue
            
            # Стилистические пометы не должны попадать в перевод
            stylistic_markers = {'прям', 'прям.', 'перен', 'перен.', 'букв', 'букв.', 'устар', 'устар.', 'разг', 'разг.', 'поэт', 'поэт.'}
            candidate = stripped.rstrip('.')
            if candidate.lower() in stylistic_markers:
                # Стилистические пометы идут в explanation
                explanation = ensure_explanation()
                explanation['content'].append({'type': 'text', 'style': 'italic', 'text': stripped})
                continue
            
            if stripped and candidate and len(candidate) <= 6 and ' ' not in candidate:
                translation = ensure_translation()
                if any(ch in '()[]{}' for ch in stripped):
                    translation['content'].append({'type': 'text', 'style': 'italic', 'text': stripped})
                else:
                    translation['content'].append({'type': 'label', 'text': stripped})
                    register_label(stripped)
                continue

            explanation = ensure_explanation()
            explanation['content'].append({'type': 'text', 'style': 'italic', 'text': stripped})
            continue

        # regular text
        flush_reference()
        close_explanation()
        text_clean = text_val.strip()
        if not text_clean:
            continue

        if text_clean.startswith(',') and (current_translation is None or not current_translation['content']):
            text_clean = text_clean.lstrip(',').strip()
            if not text_clean:
                continue

        if text_clean.startswith(':') and not current_translation and not current_explanation:
            flush_reference()
            close_translation()
            close_explanation()
            after_colon = text_clean[1:].strip()
            if after_colon:
                # Текст после двоеточия - это пример, нужно разделить на EO и RU
                illustration_data = parse_illustration(after_colon)
                illustration_node = {'type': 'illustration'}
                illustration_node.update(illustration_data)
                nodes.append(illustration_node)
            continue

        synonym_targets: List[str] = []

        def extract_synonyms(text: str) -> str:
            def repl(match):
                target = match.group(1).strip()
                if target:
                    synonym_targets.append(target)
                return ''
            return re.sub(r'\(\s*=\s*([^)]*)\)', repl, text)

        text_clean = extract_synonyms(text_clean)

        link_targets = re.findall(r'<([^>]+)>', text_clean)
        if link_targets:
            reference_targets.extend([t.strip() for t in link_targets if t.strip()])
        text_clean = re.sub(r'<[^>]+>', '', text_clean)
        if reference_mode is None:
            reference_mode = 'link'

        text_clean = text_clean.strip()

        punctuation_only = text_clean.replace(' ', '')
        if punctuation_only and all(ch in ',.;:()' for ch in punctuation_only):
            translation = ensure_translation()
            for ch in punctuation_only:
                if ch in ',.;:':
                    translation['content'].append({
                        'type': 'divider',
                        'text': ch,
                        'kind': categorize_divider(ch)
                    })
                else:
                    translation['content'].append({'type': 'text', 'style': 'regular', 'text': ch})
            if synonym_targets:
                nodes.append({'type': 'reference', 'mode': 'synonym', 'targets': synonym_targets})
            continue

        if text_clean.startswith('='):
            reference_mode = 'synonym'
            pending_reference_label = '='
            text_clean = text_clean[1:].lstrip()

        if text_clean.endswith(';'):
            text_clean = text_clean[:-1].rstrip()
        if not text_clean:
            flush_reference()
            if synonym_targets:
                nodes.append({'type': 'reference', 'mode': 'synonym', 'targets': synonym_targets})
            continue

        if reference_mode in {'see', 'compare'}:
            reference_targets.append(text_clean)
            flush_reference()
            if synonym_targets:
                nodes.append({'type': 'reference', 'mode': 'synonym', 'targets': synonym_targets})
            continue

        translation = ensure_translation()
        translation['content'].append({'type': 'text', 'style': 'regular', 'text': text_clean})
        if synonym_targets:
            nodes.append({'type': 'reference', 'mode': 'synonym', 'targets': synonym_targets})
        continue

    flush_reference()
    close_translation()
    close_explanation()

    expanded_nodes: List[Dict[str, Any]] = []
    for node in nodes:
        if node.get('type') == 'explanation' and len(node.get('content', [])) == 1:
            item = node['content'][0]
            text_val = item.get('text', '')
            if item.get('style') == 'italic' and ';' in text_val:
                parts = [part.replace('_', '').strip() for part in text_val.split(';') if part.strip('_ ').strip()]
                for idx, part in enumerate(parts):
                    expanded_nodes.append({'type': 'explanation', 'content': [{'type': 'text', 'style': 'italic', 'text': part}]})
                    if idx < len(parts) - 1:
                        expanded_nodes.append({'type': 'sentence_divider', 'text': ';'})
                continue
        expanded_nodes.append(node)

    nodes = expanded_nodes

    filtered_nodes = []
    for node in nodes:
        if node.get('type') == 'translation':
            meaningful = any(
                (item.get('type') == 'text' and item.get('text', '').strip() not in {',', ';', ':', ''})
                or item.get('type') == 'label'
                for item in node.get('content', [])
            )
            if not meaningful:
                continue
        filtered_nodes.append(node)
    nodes = filtered_nodes

    if sentence_ending:
        nodes.append({'type': 'sentence_divider', 'text': sentence_ending})

    return nodes


def should_merge_child_with_parent(parent_node: Dict[str, Any], child_node: Dict[str, Any], italic_state_open: bool) -> bool:
    """Определяет, должен ли дочерний узел слиться с родительским курсивным блоком"""
    if not italic_state_open:
        return False

    if parent_node.get('note_context'):
        return False

    text = child_node['text'].strip()
    if not text:
        return True

    if text.startswith('@') or text.startswith('['):
        return False

    if re.match(r'^\d+\.', text):
        return False

    if child_node.get('children') and text.endswith(':'):
        return True

    if child_node.get('children'):
        return False

    return True

# --- СЕМАНТИЧЕСКИЙ АНАЛИЗ ---

def parse_headword(text: str) -> Tuple[Dict, str]:
    """Парсинг заголовка статьи"""
    headword = {
        'raw_form': '',
        'lemmas': [],
        'official_mark': None,
        'homonym': None
    }

    match = re.match(r'^\s*\[([^\]]+)\]', text)
    if not match:
        return headword, text

    content = match.group(1)
    headword['raw_form'] = match.group(0)
    remaining = text[match.end():]

    official_match = re.match(r'\s*\*(\d*)', remaining)
    if official_match:
        number = official_match.group(1)
        headword['official_mark'] = f"OA{number}" if number else "UV"
        remaining = remaining[official_match.end():]

    homonym_suffix: Optional[str] = None
    homonym_match = re.search(r'\b([IVXLCDM]+)$', content)
    if homonym_match:
        homonym_suffix = homonym_match.group(1)
        headword['homonym'] = homonym_suffix
        content = re.sub(rf"\s*\b{homonym_suffix}\b$", "", content).rstrip()

    parts = [p.strip() for p in content.split(',')]
    for part in parts:
        cleaned_part = part
        if homonym_suffix and re.search(rf"\b{homonym_suffix}$", cleaned_part):
            cleaned_part = re.sub(rf"\s*\b{homonym_suffix}\b$", "", cleaned_part).rstrip()
        lemma = parse_wordform(cleaned_part)
        if lemma:
            headword['lemmas'].append(lemma)

    return headword, remaining.strip()

def parse_wordform(wordform: str) -> Optional[Dict]:
    """Парсинг отдельной словоформы"""
    base_form = re.sub(r'\([^)]+\)', '', wordform)
    base_form = re.sub(r'\|.*', '', base_form)
    base_form = base_form.replace('~', '').replace('/', '')

    if not base_form:
        return None

    return {
        'raw': wordform,
        'lemma': base_form
    }

def classify_node(node: Dict, in_note_context: bool = False) -> Dict:
    """Классификация и разбор узла"""
    text = node['text']
    indent = node['indent']
    result = {'type': 'unknown'}

    # Заголовок
    if text.startswith('[') and ']' in text:
        result['type'] = 'headword'
        headword_data, remaining = parse_headword(text)
        result.update(headword_data)
        if remaining:
            is_morpheme = any(
                lemma.get('lemma', '').startswith('-') or lemma.get('lemma', '').endswith('-')
                for lemma in headword_data.get('lemmas', [])
            )
            tail_nodes = parse_headword_remainder(remaining, is_morpheme=is_morpheme)
            if tail_nodes:
                result['children'] = tail_nodes
        return result

    if (
        node.get('italic_open_before')
        and not node.get('note_context')
        and not in_note_context
        and not text.startswith('@')
        and not text.startswith('[')
        and not text.startswith('_')
        and not re.match(r'^\d+\.', text)
    ):
        result['type'] = 'explanation'
        parsed_content = parse_rich_text(text, preserve_punctuation=True, italic_open=True)
        parsed_content = merge_punctuation_with_italic(parsed_content)
        parsed_content = absorb_parentheses_into_italic(parsed_content)
        result['content'] = parsed_content
        return result

    # Нумерованное определение
    num_match = re.match(r'^(\d+)\.\s*(.*)', text)
    if num_match:
        parsed_nodes = parse_headword_remainder(text, is_morpheme=False)
        if not parsed_nodes:
            return {'number': int(num_match.group(1)), 'type': 'translation', 'content': []}
        primary_node = parsed_nodes[0]
        extra_nodes: List[Dict[str, Any]] = []
        for extra in parsed_nodes[1:]:
            extra_type = extra.get('type')
            if extra_type in {'explanation', 'note', 'illustration'}:
                primary_node.setdefault('children', []).append(extra)
            elif extra_type == 'sentence_divider':
                primary_node['sentence_ending'] = extra.get('text')
            else:
                extra_nodes.append(extra)
        if extra_nodes:
            primary_node['extra_nodes'] = extra_nodes
        return primary_node

    # ПРИОРИТЕТ: Если мы находимся в контексте примечания ИЛИ текст содержит "_прим."
    if in_note_context or '_прим.' in text:
        if not in_note_context and '_прим.' not in text:
            pass
        elif text.startswith('[') or re.match(r'^\d+\.', text) or text.startswith('@'):
            pass
        else:
            if text.startswith('_'):
                result['type'] = 'note'
                result['content'] = parse_rich_text(text, preserve_punctuation=True)
                return result

            if indent > 0:
                result['type'] = 'illustration'
                result.update(parse_illustration(text, preserve_punctuation=True))
                return result

            result['type'] = 'note'
            result['content'] = parse_rich_text(text, preserve_punctuation=True)
            return result

    # Вложенное пояснение с примерами после двоеточия
    if indent > 0 and '_:' in text:
        prefix, remainder = text.split(':', 1)
        explanation_text = (prefix + ':').strip()
        remainder = remainder.strip()

        if explanation_text:
            parsed_explanation = parse_rich_text(explanation_text, preserve_punctuation=True)
            parsed_explanation = merge_punctuation_with_italic(parsed_explanation)
            parsed_explanation = absorb_parentheses_into_italic(parsed_explanation)
            result['type'] = 'explanation'
            result['content'] = parsed_explanation

            if remainder:
                examples = [ex.strip() for ex in remainder.split(';') if ex.strip()]
                children = []
                for i, example in enumerate(examples):
                    punctuation = ''
                    if example and example[-1] in '.!?':
                        punctuation = example[-1]
                        example = example[:-1].strip()

                    example_text = example
                    if i < len(examples) - 1:
                        example_text = example_text + ';'
                    elif punctuation:
                        example_text = example_text + punctuation

                    illustration = parse_illustration(example_text.strip(), preserve_punctuation=True)
                    illustration['type'] = 'illustration'
                    children.append(illustration)

                if children:
                    result['children'] = children

            return result

    # Толкование (курсивный текст)
    if text.startswith('_'):
        result['type'] = 'explanation'
        parsed_content = parse_rich_text(text, preserve_punctuation=True)
        parsed_content = merge_punctuation_with_italic(parsed_content)
        parsed_content = absorb_parentheses_into_italic(parsed_content)
        result['content'] = parsed_content
        return result

    stripped = text.strip()
    if indent > 0 and stripped.startswith('(') and '_' in stripped:
        cleaned = stripped.replace('_', '').strip()
        result['type'] = 'explanation'
        result['content'] = [{
            'type': 'text',
            'style': 'italic',
            'text': cleaned
        }]
        return result

    # Иллюстрация (пример) - если есть отступ
    if indent > 0:
        # Проверяем, является ли это примером (содержит ~ перед латинской буквой)
        stripped_text = text.strip()
        # Паттерн ~letter указывает на использование корня в примере
        is_example = stripped_text.startswith('~') or re.search(r'~[a-zA-Z]', stripped_text)
        if is_example:
            # Это иллюстрация (пример)
            result['type'] = 'illustration'
            # Собираем текст из всех дочерних узлов (для многострочных примеров)
            full_text = text
            if node.get('children'):
                child_texts = []
                # Проверяем, являются ли children отдельными примерами (начинаются с ~)
                children_are_examples = any(
                    child.get('text', '').strip().startswith('~')
                    for child in node['children']
                )
                
                if not children_are_examples:
                    # Склеиваем продолжение многострочного примера
                    for child in node['children']:
                        child_text = child.get('text', '').strip()
                        if child_text:
                            child_texts.append(child_text)
                    if child_texts:
                        full_text = full_text.rstrip() + ' ' + ' '.join(child_texts)
                        # Удаляем children, так как их текст уже включён в full_text
                        node['children'] = []
                # else: children остаются - они будут обработаны как отдельные illustrations
            
            result.update(parse_illustration(full_text))
            return result
        else:
            # Это translation с отступом (не пример)
            # Обрабатываем как обычный translation ниже
            pass

    # Определение по умолчанию
    result['type'] = 'translation'

    preserve = node.get('italic_open_before', False) or '_' in text

    definitions = split_definitions_by_semicolon(text)
    if len(definitions) > 1:
        result['translations'] = []
        for def_text in definitions:
            parsed_def = parse_rich_text(
                def_text,
                preserve_punctuation=preserve,
                italic_open=node.get('italic_open_before', False)
            )
            if preserve:
                parsed_def = merge_punctuation_with_italic(parsed_def)
                parsed_def = absorb_parentheses_into_italic(parsed_def)
            result['translations'].append(parsed_def)
    else:
        parsed_content = parse_rich_text(
            text,
            preserve_punctuation=preserve,
            italic_open=node.get('italic_open_before', False)
        )
        if preserve:
            parsed_content = merge_punctuation_with_italic(parsed_content)
            parsed_content = absorb_parentheses_into_italic(parsed_content)
        translation_parts, explanation_parts, label_segments = split_translation_segments(parsed_content)

        sentence_ending = extract_sentence_ending(translation_parts)
        if not sentence_ending and not translation_parts:
            sentence_ending = extract_sentence_ending(explanation_parts)

        result['content'] = merge_consecutive_text_segments(translation_parts)
        if explanation_parts:
            result.setdefault('children', []).append({
                'type': 'explanation',
                'content': explanation_parts
            })
        if sentence_ending:
            result['sentence_ending'] = sentence_ending
        if result['type'] == 'translation' and any(part.get('style') == 'italic' for part in translation_parts if part.get('type') == 'text'):
            result['type'] = 'explanation'

    if text.lstrip().startswith('@'):
        result['type'] = 'idiomatics'

    if text.startswith('_1-я буква') and ';' in text:
        parts = text.split(';')
        if len(parts) == 2:
            result['translations'] = [
                parse_rich_text(parts[0].strip(), preserve_punctuation=preserve, italic_open=node.get('italic_open_before', False)),
                parse_rich_text(parts[1].strip(), preserve_punctuation=preserve, italic_open=node.get('italic_open_before', False))
            ]
            if preserve:
                formatted_defs = []
                for def_part in result['translations']:
                    def_part = merge_punctuation_with_italic(def_part)
                    def_part = absorb_parentheses_into_italic(def_part)
                    formatted_defs.append(def_part)
                result['translations'] = formatted_defs
            result.pop('content', None)

    return result

def split_definitions_by_semicolon(text: str) -> List[str]:
    """Разделение определений по точке с запятой с учетом контекста"""
    if ';' not in text:
        return [text]

    definitions = []
    current_def = ""
    brace_level = 0
    paren_level = 0
    in_italic = False

    i = 0
    while i < len(text):
        char = text[i]

        if char == '_' and (i == 0 or text[i-1] != '\\'):
            in_italic = not in_italic
        elif char == '(' and not in_italic:
            paren_level += 1
        elif char == ')' and not in_italic:
            paren_level -= 1
        elif char == '{' and not in_italic:
            brace_level += 1
        elif char == '}' and not in_italic:
            brace_level -= 1
        elif char == ';' and brace_level == 0 and paren_level == 0 and not in_italic:
            if current_def.strip():
                definitions.append(current_def.strip())
            current_def = ""
            i += 1
            continue

        current_def += char
        i += 1

    if current_def.strip():
        definitions.append(current_def.strip())

    return definitions

def parse_rich_text(text: str, preserve_punctuation: bool = False, italic_open: bool = False) -> List[Dict]:
    """Парсинг текста с разметкой и divider'ами"""
    content = []

    if preserve_punctuation:
        # ДЛЯ ПРИМЕЧАНИЙ: сохраняем ВЕСЬ текст как единый блок БЕЗ ЛЮБОГО РАЗБИЕНИЯ
        # Знаки препинания, скобки, ссылки - ВСЁ остаётся в одном блоке текста
        # Только выделяем курсив между подчёркиваниями

        # СПЕЦИАЛЬНАЯ ОБРАБОТКА ДЛЯ ПРИМЕЧАНИЙ: правильно обрабатываем курсивные блоки
        if text.startswith('_'):
            # Если текст начинается с "_", считаем весь текст курсивным
            # Ищем последнее подчеркивание в тексте
            last_underscore_pos = text.rfind('_')
            if last_underscore_pos == len(text) - 1:
                # Если последнее "_" в конце текста, весь текст между "_" курсивный
                italic_text = text[1:-1]  # Убираем начальное и конечное "_"
                content.append({
                    'type': 'text',
                    'style': 'italic',
                    'text': italic_text
                })
                return content
            else:
                # Если есть текст после последнего "_", обрабатываем как обычно
                italic = False
                current_text = ""
                i = 0
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

        # Стандартная обработка для других случаев
        italic = italic_open
        current_text = ""
        i = 0
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

    # Стандартный парсинг с divider'ами
    parts = re.split(r'(_|<[^>]+>|\([^)]+\)|\{[^}]+\}|[,;:.!?])', text)

    italic = italic_open
    i = 0
    while i < len(parts):
        part = parts[i]
        if not part:
            i += 1
            continue

        if part == '_':
            italic = not italic
            i += 1
            continue

        if part.startswith('<') and part.endswith('>'):
            content.append({
                'type': 'link',
                'text': part[1:-1]
            })
        elif part.startswith('(') and part.endswith(')'):
            paren_content = part[1:-1]
            # Если содержимое начинается с граве, это не примечание, а часть текста (опциональное слово)
            starts_with_grave = paren_content.lstrip().startswith('`')
            
            if len(paren_content.strip()) <= 1 or starts_with_grave:
                # Это опциональная часть или короткая скобка - оставляем как текст
                if content and content[-1]['type'] == 'text':
                    content[-1]['text'] += part
                elif i + 1 < len(parts) and parts[i + 1] and not parts[i + 1].startswith(('<', '{', '_')) and parts[i + 1] not in [',', ';', ':', '.', '!', '?']:
                    parts[i + 1] = part + parts[i + 1]
                else:
                    content.append({
                        'type': 'text',
                        'style': 'regular',
                        'text': part
                    })
            else:
                # Это примечание
                content.append({
                    'type': 'note',
                    'text': paren_content
                })
        elif part.startswith('{') and part.endswith('}'):
            content.append({
                'type': 'pos',
                'text': part[1:-1]
            })
        elif part in [',', ';', ':', '.', '!', '?']:
            content.append({
                'type': 'divider',
                'text': part
            })
        else:
            content.append({
                'type': 'text',
                'style': 'italic' if italic else 'regular',
                'text': part
            })

        i += 1

    return content

def split_ru_segments(parts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Преобразование разбора русской части в сегменты с делителями"""
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
            if style == 'italic' and text in label_modes:
                mode = label_modes[text]
                label_segment: Dict[str, Any] = {'text': text, 'kind': 'reference', 'mode': mode}
                segments.append(label_segment)
                active_reference_mode = mode
                pending_label_segment = label_segment
                continue

            segments.append({'text': text, 'kind': 'term'})
            active_reference_mode = None
            pending_label_segment = None

        elif part_type == 'divider':
            divider = part.get('text')
            if divider:
                if pending_label_segment and divider == '.':
                    pending_label_segment['text'] += '.'
                    pending_label_segment = None
                    continue
                segments.append({'text': divider, 'kind': categorize_divider(divider)})
                if divider in '.!?':
                    active_reference_mode = None
                pending_label_segment = None

        elif part_type == 'link':
            target = part.get('text', '').strip()
            if target:
                segment: Dict[str, Any] = {'text': target, 'kind': 'link', 'target': target}
                if active_reference_mode:
                    segment['mode'] = active_reference_mode
                segments.append(segment)
            pending_label_segment = None

        elif part_type == 'note':
            note_text = part.get('text', '').strip()
            if note_text:
                segments.append({'text': note_text, 'kind': 'note'})
            pending_label_segment = None

    return _post_process_ru_segments(segments)


def _split_link_notation(raw: str) -> Tuple[str, Optional[str]]:
    if '@' not in raw:
        value = raw.strip()
        return value, None
    parts = [part.strip() for part in raw.split('@') if part.strip()]
    if len(parts) >= 3:
        parts = parts[1:]
    if not parts:
        return raw.strip(), None
    target = parts[0]
    display = '@'.join(parts[1:]).strip() if len(parts) > 1 else None
    return target, display or None


def _post_process_ru_segments(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Нормализация сегментов: преобразование отраслевых помет в label."""

    result: List[Dict[str, Any]] = []
    i = 0
    while i < len(segments):
        segment = segments[i]
        kind = segment.get('kind')
        text = segment.get('text', '')

        if kind == 'term':
            next_seg = segments[i + 1] if i + 1 < len(segments) else None
            # Текст вида "анат" + '.' → label
            if next_seg and next_seg.get('kind') == 'sentence_divider' and next_seg.get('text') == '.':
                if '`' in text or any(ch.isupper() for ch in text):
                    result.append(segment)
                    result.append(next_seg)
                    i += 2
                    continue
                label_text = text + '.'
                result.append({'text': label_text, 'kind': 'label'})
                register_label(label_text)
                i += 2
                continue

            # Текст, уже оканчивающийся на '.'
            if text.endswith('.') and text.strip('.').isalpha():
                if '`' in text or any(ch.isupper() for ch in text):
                    result.append(segment)
                    i += 1
                    continue
                result.append({'text': text, 'kind': 'label'})
                register_label(text)
                i += 1
                continue

        if kind == 'note':
            clean = text.strip().strip('_')
            if clean:
                if not clean.startswith('('):
                    clean = f'({clean})'
                segment['text'] = clean
                segment['style'] = 'italic'

        if kind == 'link':
            target_raw = segment.get('target') or text
            target, display = _split_link_notation(target_raw)
            segment['target'] = target
            if display:
                segment['text'] = display
            else:
                segment['text'] = segment.get('text', '') or target

        result.append(segment)
        i += 1

    return result


def parse_illustration(text: str, preserve_punctuation: bool = False) -> Dict:
    """Парсинг примера использования"""
    # Для текста, который начинается с '_', не пытаемся разделять на эсперанто и русский
    if text.startswith('_'):
        return {'content': parse_rich_text(text, preserve_punctuation)}

    parsed_content = parse_rich_text(text, preserve_punctuation)
    result = {'content': parsed_content}

    if '--' in text or ' — ' in text:
        return result

    cyrillic_pos = -1

    for i, char in enumerate(text):
        if '\u0400' <= char <= '\u04FF':
            if i > 0 and all(c in ' `\t' for c in text[max(0, i-5):i]):
                cyrillic_pos = i
                break

            pattern_match = re.search(r'\d+-[йго]\s+\w+', text)
            if pattern_match:
                pattern_match_start = pattern_match.start()
                if any('\u0400' <= c <= '\u04FF' for c in text[pattern_match_start:i + 1]):
                    cyrillic_pos = pattern_match.start()
                    break

            cyrillic_pos = i
            break

    if cyrillic_pos > 0:
        ru_start = cyrillic_pos
        while ru_start > 0 and text[ru_start - 1] in {'_', '`'}:
            ru_start -= 1
        eo_part = text[:ru_start].strip()
        ru_part = text[ru_start:].strip()

        if eo_part and not any('A' <= c <= 'Z' or 'a' <= c <= 'z' or '\u00C0' <= c <= '\u024F' for c in eo_part):
            ru_part = (eo_part + ru_part).strip()
            eo_part = ""

        if eo_part and ru_part and not eo_part.endswith('-'):
            result['eo'] = eo_part
            ru_parts = parse_rich_text(ru_part, preserve_punctuation=False)
            ru_segments = split_ru_segments(ru_parts)
            result['ru_segments'] = ru_segments if ru_segments else [{'text': ru_part, 'kind': 'term'}]
            divider_kinds = {seg['kind'] for seg in result['ru_segments'] if 'divider' in seg['kind']}
            if 'near_divider' in divider_kinds and 'far_divider' in divider_kinds:
                result['ru_requires_review'] = True
            result.pop('content', None)
    else:
        ru_part = text.strip()

    result.setdefault('meta', {})['ru_text'] = ru_part

    return result

def process_final_tree(tree: List[Dict], in_note_context: bool = False, note_base_indent: Optional[int] = None) -> List[Dict]:
    """Шаг 3: Семантический анализ финального дерева"""
    result: List[Dict] = []
    current_note_block: Optional[Dict[str, Any]] = None

    def append_processed(target_list: List[Dict], node: Dict[str, Any]):
        ending = node.pop('sentence_ending', None)
        if (
            node.get('type') == 'explanation'
            and target_list
            and target_list[-1].get('type') == 'explanation'
            and not node.get('number')
            and not target_list[-1].get('number')
        ):
            target_list[-1].setdefault('content', []).extend(node.get('content', []))
        else:
            target_list.append(node)
        if ending:
            target_list.append({'type': 'sentence_divider', 'text': ending})

    def normalize_explanation(node: Dict[str, Any]):
        if node.get('type') != 'explanation':
            return
        normalized = []
        for item in node.get('content', []):
            if item.get('type') == 'divider':
                normalized.append({'type': 'text', 'style': 'regular', 'text': item.get('text', '')})
            else:
                text = item.get('text', '')
                if text in {':', ';', ',', '.', '?', '!', ''}:
                    normalized.append({'type': 'text', 'style': 'regular', 'text': text})
                else:
                    normalized.append(item)
        node['content'] = merge_consecutive_text_segments(normalized)

    def append_note_child(content_list: List[Dict[str, Any]], child: Dict[str, Any]):
        ending = child.pop('sentence_ending', None)
        content_list.append(child)
        if ending:
            content_list.append({'type': 'sentence_divider', 'text': ending})

    def ensure_note_block(base_indent: int) -> Dict[str, Any]:
        nonlocal current_note_block, note_base_indent
        if current_note_block is None:
            current_note_block = {'type': 'note', 'content': [], 'children': []}
            note_base_indent = base_indent
        return current_note_block

    def flush_note_block():
        nonlocal current_note_block, note_base_indent
        if current_note_block and (current_note_block['content'] or current_note_block['children']):
            if not current_note_block['children']:
                current_note_block.pop('children')
            result.append(current_note_block)
        current_note_block = None
        note_base_indent = None

    note_context_active = in_note_context

    for node in tree:
        is_note_start = '_прим.' in node['text']
        current_indent = node['indent']
        is_structural_line = (
            node['text'].startswith('[') or
            re.match(r'^\d+\.', node['text']) or
            node['text'].startswith('@')
        )

        resets_due_to_indent = (
            current_note_block is not None and
            note_base_indent is not None and
            current_indent < note_base_indent
        )

        resets_due_to_structure = (
            current_note_block is not None and
            note_base_indent is not None and
            current_indent == note_base_indent and
            not node['text'].lstrip().startswith('_') and
            not current_indent > note_base_indent
        )

        if (note_context_active or current_note_block) and (resets_due_to_indent or resets_due_to_structure):
            flush_note_block()
            note_context_active = False

        current_node_in_note_context = note_context_active or is_note_start or current_note_block is not None

        processed_node = classify_node(node, current_node_in_note_context)
        extra_nodes = processed_node.pop('extra_nodes', []) if isinstance(processed_node, dict) else []
        for extra in extra_nodes:
            if extra.get('type') == 'explanation':
                normalize_explanation(extra)

        if processed_node['type'] == 'illustration' and not processed_node.get('eo'):
            contents = processed_node.get('content') or []
            if not contents and processed_node.get('text'):
                contents = [{'type': 'text', 'style': 'regular', 'text': processed_node.get('text')}]
            processed_node['content'] = contents

        if processed_node['type'] == 'explanation':
            normalize_explanation(processed_node)

        if processed_node['type'] == 'note':
            block = ensure_note_block(node['indent'])
            ending = processed_node.pop('sentence_ending', None)
            block['content'].extend(processed_node['content'])
            note_context_active = True
            if node['children']:
                processed_children = process_final_tree(node['children'], True, note_base_indent=node['indent'])
                for child in processed_children:
                    if child.get('type') == 'explanation':
                        child = {'type': 'illustration', 'content': child.get('content', [])}
                    if child.get('type') == 'note':
                        block['content'].extend(child.get('content', []))
                        for nested in child.get('children', []):
                            append_note_child(block['content'], nested)
                    else:
                        append_note_child(block['content'], child)
            if ending:
                block['content'].append({'type': 'sentence_divider', 'text': ending})
            continue

        if processed_node['type'] == 'illustration' and (note_context_active or current_note_block):
            block = ensure_note_block(note_base_indent if note_base_indent is not None else node['indent'])
            append_note_child(block['content'], processed_node)
            if node['children']:
                processed_node['children'] = process_final_tree(node['children'], True, note_base_indent=node['indent'])
            continue

        flush_note_block()
        existing_children = processed_node.get('children', [])
        if node['children']:
            new_children = process_final_tree(node['children'], current_node_in_note_context, note_base_indent=None)
            if existing_children:
                processed_node['children'] = existing_children + new_children
            else:
                processed_node['children'] = new_children
        elif existing_children:
            processed_node['children'] = existing_children

        if processed_node.get('type') == 'idiomatics':
            extra_fragments: List[Dict[str, Any]] = []
            kept_children: List[Dict[str, Any]] = []
            for child in processed_node.get('children', []) or []:
                if child.get('type') == 'explanation':
                    extra_fragments.extend(child.get('content', []))
                else:
                    kept_children.append(child)
            if extra_fragments:
                processed_node.setdefault('content', []).extend(extra_fragments)
            processed_node['children'] = kept_children

        append_processed(result, processed_node)

        for extra in extra_nodes:
            append_processed(result, extra)

    flush_note_block()

    return result

# --- ОСНОВНАЯ ФУНКЦИЯ ---

def parse_article(article_text: str) -> Dict:
    """Полный цикл парсинга статьи"""
    processed_text = preprocess_text(article_text)
    lines = processed_text.strip().split('\n')

    filtered_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r'^\d{4}-\d{2}-\d{2}', stripped) or re.match(r'^\w+ \w+$', stripped):
            continue
        filtered_lines.append(line)

    if not filtered_lines:
        return {'headword': None, 'body': []}

    headword_line = filtered_lines[0]
    body_lines = filtered_lines[1:]

    headword, remaining_text = parse_headword(headword_line)
    is_morpheme_headword = any(
        lemma.get('lemma', '').startswith('-') or lemma.get('lemma', '').endswith('-')
        for lemma in headword.get('lemmas', [])
    )

    head_remainder_nodes: List[Dict[str, Any]] = []
    initial_italic_state = False
    if remaining_text:
        initial_italic_state = count_unescaped_underscores(remaining_text) % 2 == 1
        # Проверяем, есть ли пронумерованное определение в остатке
        # Если да, добавляем его в body_lines, чтобы обработать через classify_node
        stripped_remainder = remaining_text.strip()
        numbered_match = re.match(r'^\*?\s*(\d+)\.\s+', stripped_remainder)
        if numbered_match and not is_morpheme_headword:
            # Пронумерованное определение - добавляем в начало body
            # Сохраняем отступ (если есть) для правильной обработки
            body_lines = [remaining_text] + body_lines
            # initial_italic_state остаётся, так как он влияет на первую body line
        else:
            # Обычный остаток - обрабатываем как раньше
            head_remainder_nodes = parse_headword_remainder(remaining_text, is_morpheme=is_morpheme_headword)

    raw_tree = build_raw_tree(body_lines)
    stitched_tree = stitch_multiline_italic_blocks(raw_tree, italic_open=initial_italic_state)
    final_body = head_remainder_nodes + process_final_tree(stitched_tree)
    merged_body: List[Dict[str, Any]] = []
    for node in final_body:
        if (
            merged_body
            and node.get('type') == 'explanation'
            and merged_body[-1].get('type') == 'explanation'
            and not node.get('number')
            and not merged_body[-1].get('number')
        ):
            target_node = merged_body[-1]
            target_node.setdefault('content', []).extend(node.get('content', []))
            if node.get('children'):
                target_children = target_node.setdefault('children', [])
                target_children.extend(node['children'])
            target_node['content'] = merge_consecutive_text_segments(target_node.get('content', []))
        else:
            merged_body.append(node)
    final_body = merged_body

    return {
        'headword': headword if headword['raw_form'] else None,
        'body': final_body
    }

def split_articles_by_empty_lines(content: str) -> List[str]:
    """Разделение файла на статьи по пустым строкам"""
    lines = content.split('\n')
    articles = []
    current_article = []

    skip_initial = True
    for line in lines:
        stripped = line.strip()

        if skip_initial:
            if stripped.startswith('$') or not stripped:
                continue
            else:
                skip_initial = False

        if not stripped:
            if current_article:
                articles.append('\n'.join(current_article))
                current_article = []
        else:
            current_article.append(line)

    if current_article:
        articles.append('\n'.join(current_article))

    return articles

def main():
    """Основная функция"""
    try:
        global KNOWN_SHORTENINGS, LOGGED_UNKNOWN_LABELS
        KNOWN_SHORTENINGS = load_shortenings()
        LOGGED_UNKNOWN_LABELS.clear()
        print(f"Загружено {len(KNOWN_SHORTENINGS)} сокращений")

        with open(INPUT_FILENAME, 'r', encoding='utf-8') as f:
            content = f.read()

        articles = split_articles_by_empty_lines(content)
        print(f"Найдено {len(articles)} потенциальных статей")

        parsed_articles = []
        for i, article_text in enumerate(articles):
            if article_text.strip():
                try:
                    parsed = parse_article(article_text)
                    if parsed['headword']:
                        parsed_articles.append(parsed)
                    else:
                        pass
                except Exception as e:
                    log_issue('parse_error', str(e), article_text[:200])
                    print(f"Ошибка парсинга статьи {i+1}: {e}", file=sys.stderr)
                    continue

        result = {
            "meta": {
                "parser_version": PARSER_VERSION,
                "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "articles_count": len(parsed_articles),
                "issues_count": len(parsing_issues)
            },
            "articles": parsed_articles
        }

        with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        save_log()

        print(f"Парсинг завершён. Обработано {len(parsed_articles)} статей.")
        print(f"Результат сохранён в {OUTPUT_FILENAME}")

    except FileNotFoundError:
        print(f"Файл {INPUT_FILENAME} не найден", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
    import time
    print("Парсер завершил работу. Ожидание 5 секунд перед выходом...")
    time.sleep(5)

def register_label(label_text: str):
    """Фиксирует встреченную отраслевую помету и проверяет её наличие в справочнике."""

    raw = label_text.strip()
    if raw.startswith('('):
        return
    normalized = raw.strip('.').lower()
    normalized = re.sub(r"[`'\s]", "", normalized)
    if not normalized or ' ' in normalized or len(normalized) > 7:
        return
    if normalized in KNOWN_SHORTENINGS or normalized in BUILTIN_LABELS:
        return
    if normalized in LOGGED_UNKNOWN_LABELS:
        return
    LOGGED_UNKNOWN_LABELS.add(normalized)
    log_issue('unknown_label', f'Неизвестная помета: {label_text}')
