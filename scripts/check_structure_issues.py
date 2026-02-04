#!/usr/bin/env python3
"""
Проверка структурных проблем в файлах словаря без импорта в БД.
Использует ту же логику, что и importer.py: _detect_structure_issues()
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

# Паттерны из importer.py
STRUCTURE_HEADER_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2} \d{1,2}:\d{2} [A-Za-z0-9_]+#?$")
STRUCTURE_WORD_PATTERN = re.compile(r"^\[[^\]]+\]")

# Файлы с ожидаемыми структурными особенностями (исключения из отчёта)
STRUCTURE_ISSUE_EXCEPTIONS = {
    "eo": ["w.txt"],  # w.txt содержит служебные строки \head\ и \p\ после заголовков
    "ru": [],
}


def _detect_structure_issues(lines: List[str]) -> List[Dict[str, Any]]:
    """
    Обнаруживает структурные проблемы в файле словаря.
    Возвращает список проблем с деталями.
    """
    issues: List[Dict[str, Any]] = []
    idx = 0
    current_headers: List[Dict[str, Any]] = []

    while idx < len(lines):
        stripped = lines[idx].strip()

        if not stripped:
            current_headers = []
            idx += 1
            continue

        if STRUCTURE_HEADER_PATTERN.match(stripped):
            header_block: List[Dict[str, Any]] = []
            while idx < len(lines) and STRUCTURE_HEADER_PATTERN.match(lines[idx].strip()):
                header_block.append({"line": idx + 1, "header": lines[idx].strip()})
                idx += 1

            current_headers = header_block

            if idx >= len(lines):
                issues.append(
                    {
                        "type": "header_without_word",
                        "headers": header_block,
                        "message": "файл заканчивается сразу после блока заголовков",
                    }
                )
                break

            next_stripped = lines[idx].strip()
            if not next_stripped or not STRUCTURE_WORD_PATTERN.match(next_stripped):
                issues.append(
                    {
                        "type": "header_without_word",
                        "headers": header_block,
                        "next_line": next_stripped,
                    }
                )
            continue

        if STRUCTURE_WORD_PATTERN.match(stripped) and not current_headers:
            issues.append(
                {
                    "type": "word_without_header",
                    "line": idx + 1,
                    "word": stripped,
                    "context": lines[max(0, idx - 3) : idx + 2],
                }
            )

        idx += 1

    return issues


def check_language_files(data_dir: Path, lang: str) -> Dict[str, Any]:
    """
    Проверяет все файлы языка на структурные проблемы.
    """
    lang_dir_name = "VortaroER-daily" if lang == "eo" else "VortaroRE-daily"
    lang_dir = data_dir / lang_dir_name

    if not lang_dir.exists():
        print(f"⚠️  Директория не найдена: {lang_dir}", file=sys.stderr)
        return {}

    files = sorted(
        file_path
        for file_path in lang_dir.iterdir()
        if file_path.is_file() and file_path.suffix.lower() == ".txt"
    )

    results: Dict[str, List[Dict[str, Any]]] = {}
    total_issues = 0
    exceptions = STRUCTURE_ISSUE_EXCEPTIONS.get(lang, [])

    for file_path in files:
        try:
            # Читаем в CP1251 для эсперанто/русских словарей
            raw = file_path.read_bytes()
            text = raw.decode("cp1251")
            lines = text.splitlines()

            issues = _detect_structure_issues(lines)

            if issues:
                # Пропускаем файлы в списке исключений
                if file_path.name not in exceptions:
                    rel_path = f"{lang_dir_name}/{file_path.name}"
                    results[rel_path] = issues
                    total_issues += len(issues)
                else:
                    print(f"ℹ️  Исключённый файл {file_path.name}: {len(issues)} пропущено", file=sys.stderr)
        except Exception as e:
            print(f"⚠️  Ошибка чтения {file_path.name}: {e}", file=sys.stderr)

    return {
        "lang": lang,
        "total_issues": total_issues,
        "files_with_issues": len(results),
        "issues": results,
    }


def format_report(result: Dict[str, Any], verbose: bool = False) -> str:
    """
    Форматирует отчёт в человекочитаемый вид.
    """
    lang_name = "Эсперанто" if result["lang"] == "eo" else "Русский"
    lines = [
        f"\n📋 Отчёт по структурным проблемам ({lang_name})",
        "=" * 50,
        f"Всего проблем: {result['total_issues']}",
        f"Файлов с проблемами: {result['files_with_issues']}",
    ]

    if verbose:
        for file_path, issues in result["issues"].items():
            lines.append(f"\n📄 {file_path} ({len(issues)} проблем):")
            for issue in issues:
                if issue["type"] == "header_without_word":
                    headers = ", ".join(h["header"] for h in issue.get("headers", []))
                    lines.append(f"  ❌ Заголовки без слова: {headers}")
                    if "next_line" in issue:
                        lines.append(f"     Следующая строка: {issue['next_line']}")
                elif issue["type"] == "word_without_header":
                    lines.append(f"  ❌ Слово без заголовков на строке {issue['line']}: {issue['word']}")
                    if issue.get("context"):
                        ctx = "\n       ".join(issue["context"])
                        lines.append(f"     Контекст:\n       {ctx}")

    return "\n".join(lines)


def format_for_tracking_summary(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Форматирует результат в формат совместимый с tracking-summary.json.
    """
    structure_issues = {}

    if result.get("total_issues", 0) > 0:
        files_with_issues = result.get("files_with_issues", 0)
        issues = result.get("issues", {})

        structure_issues = {
            "total": result["total_issues"],
            "files_with_issues": files_with_issues,
            "files": {k: len(v) for k, v in issues.items()},
        }

        # Добавляем детализацию для реальных проблем
        details = []
        for file_path, issue_list in issues.items():
            for issue in issue_list:
                if issue.get("type") == "word_without_header":
                    details.append({
                        "file": file_path,
                        "line": issue.get("line"),
                        "type": issue.get("type"),
                        "word": issue.get("word"),
                        "context": " ".join(issue.get("context", [])[-3:]) if issue.get("context") else "",
                    })
                elif issue.get("type") == "header_without_word" and issue.get("next_line"):
                    headers = ", ".join(h.get("header", "") for h in issue.get("headers", []))
                    details.append({
                        "file": file_path,
                        "type": issue.get("type"),
                        "headers": headers,
                        "next_line": issue.get("next_line"),
                    })

        if details:
            structure_issues["details"] = details

    return structure_issues


def main():
    parser = argparse.ArgumentParser(
        description="Проверка структурных проблем в файлах словаря без импорта"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path.home() / "rueo_master" / "backend" / "data" / "src",
        help="Директория с файлами словаря (default: ~/rueo_master/backend/data/src)",
    )
    parser.add_argument(
        "--lang",
        choices=["eo", "ru", "all"],
        default="all",
        help="Язык для проверки (default: all)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Вывод в формате JSON",
    )
    parser.add_argument(
        "--tracking-format",
        action="store_true",
        help="Вывод в формате tracking-summary.json (совместимо с importer.py)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Подробный вывод",
    )

    args = parser.parse_args()
    data_dir = args.data_dir.expanduser().resolve()

    if not data_dir.exists():
        print(f"❌ Директория не найдена: {data_dir}", file=sys.stderr)
        sys.exit(1)

    languages = ["eo", "ru"] if args.lang == "all" else [args.lang]
    results = {}

    for lang in languages:
        result = check_language_files(data_dir, lang)
        results[lang] = result

    if args.tracking_format:
        # Формат для обновления tracking-summary.json
        tracking_data = {}
        for lang, result in results.items():
            tracking_data[lang] = {"structure_issues": format_for_tracking_summary(result)}
        print(json.dumps(tracking_data, ensure_ascii=False, indent=2))
    elif args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for lang, result in results.items():
            if result.get("total_issues", 0) > 0:
                print(format_report(result, verbose=args.verbose))
            else:
                lang_name = "Эсперанто" if lang == "eo" else "Русский"
                print(f"✅ {lang_name}: структурных проблем не найдено")


if __name__ == "__main__":
    main()
