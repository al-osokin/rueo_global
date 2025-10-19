from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Sequence

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.models import (
    Article,
    ArticleRu,
    FuzzyEntry,
    SearchEntry,
    SearchEntryRu,
    SearchStat,
)
from app.utils.esperanto import (
    cxapeligo,
    oh_sencxapeligo,
    sencxapeligo,
    urlsencxapeligo,
)

Language = str


@dataclass
class SearchRow:
    art_id: int
    vorto: Optional[str]
    priskribo: str
    komento: Optional[str]


class LinkResolver:
    def __init__(self, session: Session):
        self._session = session
        self._cache: dict[str, bool] = {}

    def exists(self, word: str) -> bool:
        if not word:
            return False
        word = word.strip()
        if not word:
            return False
        if word in self._cache:
            return self._cache[word]

        candidates = {word, sencxapeligo(word)}
        result = False
        for candidate in candidates:
            if result:
                break
            stmt = (
                select(SearchEntry.art_id)
                .where(SearchEntry.vorto == candidate)
                .limit(1)
            )
            entry = self._session.execute(stmt).scalar_one_or_none()
            if entry is not None:
                result = True
                break
            stmt_ru = (
                select(SearchEntryRu.art_id)
                .where(SearchEntryRu.vorto == candidate)
                .limit(1)
            )
            entry_ru = self._session.execute(stmt_ru).scalar_one_or_none()
            if entry_ru is not None:
                result = True
                break

        self._cache[word] = result
        return result


class SearchService:
    def __init__(self, session: Session):
        self.session = session
        self._link_resolver = LinkResolver(session)

    def search(self, query: str, client_ip: Optional[str] = None) -> dict:
        prepared = oh_sencxapeligo(query or "").strip()
        prepared = prepared.replace("_", " ")
        if not prepared:
            return {"count": 0, "html": "", "fuzzy_html": ""}

        search_term = sencxapeligo(prepared)
        language = self._detect_language(search_term)

        rows = self._search_rows(search_term, language)
        fuzzy_html = self._build_fuzzy_html(search_term)

        if rows:
            html = self._render_rows(rows, fuzzy_html)
            count = len(rows)
        else:
            message = "Подходящей словарной статьи не найдено."
            html = f"{fuzzy_html}{message}"
            count = 0

        self._log_search(search_term, client_ip)
        return {"count": count, "html": html, "fuzzy_html": fuzzy_html}

    def suggest(self, term: str) -> List[dict]:
        prepared = oh_sencxapeligo(term or "").strip()
        if not prepared:
            return []
        target = sencxapeligo(prepared)
        language = self._detect_language(target)

        search_model = SearchEntry if language == "eo" else SearchEntryRu

        variants = {target}
        if target:
            variants.update(
                {
                    target.lower(),
                    target.upper(),
                    target.capitalize(),
                    target.title(),
                }
            )

        prefixes = {variant for variant in variants if variant}
        if not prefixes:
            return []

        patterns: set[str] = set()
        for variant in prefixes:
            patterns.add(variant)
            patterns.add(f"-{variant}")
            patterns.add(f"<<{variant}")

        like_conditions = [
            search_model.vorto.like(f"{pattern}%") for pattern in patterns
        ]

        stmt = (
            select(search_model.vorto, search_model.art_id, search_model.id)
            .where(
                or_(*like_conditions)
            )
            .order_by(search_model.id.asc())
        ).limit(60)

        rows = self.session.execute(stmt).all()
        seen = set()
        suggestions = []
        for vorto, art_id, _ in rows:
            if not vorto or vorto in seen:
                continue
            seen.add(vorto)
            suggestions.append(
                {
                    "id": art_id,
                    "label": cxapeligo(vorto),
                    "value": cxapeligo(vorto),
                }
            )
            if len(suggestions) >= 30:
                break
        return suggestions

    def _detect_language(self, query: str) -> Language:
        tmp = query.replace("-", "")
        if re.match(r"^[a-zA-Z]", tmp):
            return "eo"
        return "ru"

    def _search_rows(self, query: str, language: Language) -> List[SearchRow]:
        article_model = Article if language == "eo" else ArticleRu
        search_model = SearchEntry if language == "eo" else SearchEntryRu
        variants = self._generate_variants(query, language)
        grouped = []

        if variants:
            lower_variants = [variant.lower() for variant in variants]
            priority_case = case(
                {variant: idx for idx, variant in enumerate(lower_variants)},
                value=func.lower(search_model.vorto),
                else_=len(variants),
            )
            stmt_variants = (
                select(
                    article_model.art_id,
                    search_model.vorto,
                    article_model.priskribo,
                    article_model.komento,
                    search_model.id,
                )
                .join(search_model, article_model.art_id == search_model.art_id)
                .where(func.lower(search_model.vorto).in_(lower_variants))
                .order_by(priority_case.asc(), search_model.id.asc())
            )
            grouped = self._group_by_article(self.session.execute(stmt_variants).all())

        if grouped:
            return grouped

        pattern = f"^[<]{{0,2}}{query}"
        stmt_regex = (
            select(
                article_model.art_id,
                search_model.vorto,
                article_model.priskribo,
                article_model.komento,
                search_model.id,
            )
            .join(search_model, article_model.art_id == search_model.art_id)
            .where(search_model.vorto.op("~")(pattern))
            .order_by(article_model.art_id.asc(), search_model.id.asc())
        )

        rows = self.session.execute(stmt_regex.limit(100)).all()
        grouped = self._group_by_article(rows)

        if grouped:
            return grouped

        stmt_like = (
            select(
                article_model.art_id,
                search_model.vorto,
                article_model.priskribo,
                article_model.komento,
                search_model.id,
            )
            .join(search_model, article_model.art_id == search_model.art_id)
            .where(search_model.vorto.like(f"{query} I%"))
            .order_by(article_model.art_id.asc(), search_model.id.asc())
        )
        rows = self.session.execute(stmt_like.limit(50)).all()
        grouped = self._group_by_article(rows)
        return grouped

    def _generate_variants(self, query: str, language: Language) -> List[str]:
        base = query.strip()
        if not base:
            return []

        variants: List[str] = []

        def add_variant(value: str) -> None:
            normalized = value.strip()
            if normalized and normalized not in variants:
                variants.append(normalized)

        add_variant(base)

        roman_suffixes = ["I", "II", "III", "IV", "V"]
        for suffix in roman_suffixes:
            add_variant(f"{base} {suffix}")

        if not base.startswith("-"):
            add_variant(f"-{base}")
            for suffix in roman_suffixes:
                add_variant(f"-{base} {suffix}")

        if not base.endswith("-"):
            add_variant(f"{base}-")

        if not base.startswith("<<"):
            add_variant(f"<<{base}>>")
            add_variant(f"<<{base}")

        if not base.startswith('"'):
            add_variant(f'"{base}"')

        add_variant(base.lower())
        add_variant(base.upper())

        return variants

    def _group_by_article(self, rows: Sequence[Sequence]) -> List[SearchRow]:
        seen = set()
        result: List[SearchRow] = []
        for art_id, vorto, priskribo, komento, _ in rows:
            if art_id in seen:
                continue
            seen.add(art_id)
            if not priskribo:
                continue
            result.append(
                SearchRow(
                    art_id=art_id,
                    vorto=vorto,
                    priskribo=priskribo,
                    komento=komento,
                )
            )
        return result

    def _build_fuzzy_html(self, query: str) -> str:
        stmt = select(FuzzyEntry.klara_vorto).where(FuzzyEntry.neklara_vorto == query)
        words = [row[0] for row in self.session.execute(stmt).all() if row[0]]
        if not words:
            return ""

        prefix = "Похожее слово: " if len(words) == 1 else "Похожие слова: "
        parts = []
        for word in words:
            href = f"/sercxo/{urlsencxapeligo(word)}"
            parts.append(f'<a href="{href}">{cxapeligo(word)}</a>')
        return prefix + " ".join(parts) + "<br>"

    def _render_rows(self, rows: Sequence[SearchRow], fuzzy_html: str) -> str:
        parts: List[str] = []
        for row in rows:
            formatted = format_article(row.priskribo, self._link_resolver)
            block = [formatted, "<br><br>"]
            if fuzzy_html:
                block.append(fuzzy_html)
            ltext = ""
            if row.vorto:
                permalink = urlsencxapeligo(row.vorto)
                label = cxapeligo(row.vorto)
                ltext = (
                    '<br>Постоянная ссылка: '
                    f'<a href="/sercxo/{permalink}">{label}</a>'
                )

            komento = row.komento or ""
            if "#" in komento:
                ltext = "<br><strong>Статья неполная</strong>" + ltext

            dates = re.findall(r"(\d{4}-\d{2}-\d{2})", komento)
            if dates:
                block.append(f'<br><div class="kom">Редакция: {dates[-1]}{ltext}</div>')
            block.append("<br>")
            parts.append("".join(block))
        return "".join(parts)

    def _log_search(self, term: str, client_ip: Optional[str]) -> None:
        hashed_ip = hashlib.md5(client_ip.encode("utf-8")).hexdigest() if client_ip else None
        stat = SearchStat(vorto=term[:255], dato=datetime.utcnow(), hip=hashed_ip)
        self.session.add(stat)


def format_article(text: str, resolver: LinkResolver) -> str:
    if not text:
        return ""
    source = text.replace("\r\n", "\n")
    source = source.replace("|", "||")
    source = re.sub(r"^(\@)", "&#9674;", source, flags=re.MULTILINE)
    source = re.sub(r"<<(.*?)>>", r"&laquo;\1&raquo;", source, flags=re.IGNORECASE | re.DOTALL)

    def create_link1(match: re.Match[str]) -> str:
        body = match.group(1)
        if body.startswith("~"):
            return (
                '<span style="color: blue;" '
                f'title="Слово в текущей статье: {body}">{body}</span>'
            )
        pieces = body.split(".")
        vvorto = re.sub(r"[()`]", "", pieces[0])
        if resolver.exists(vvorto):
            href = f"/sercxo/{urlsencxapeligo(vvorto)}"
            label = body.replace(".", "&nbsp;")
            return f'<a href="{href}">{label}</a>'
        return (
            '<span style="color: blue;" '
            f'title="Ссылка на слово {body}">{body}</span>'
        )

    def create_link2(match: re.Match[str]) -> str:
        word = match.group(1)
        label = match.group(2)
        if resolver.exists(word):
            href = f"/sercxo/{urlsencxapeligo(word)}"
            return f'<a href="{href}">{label}</a>'
        return (
            '<span style="color: blue;" '
            f'title="Ссылка на слово {word}">{label}</span>'
        )

    def create_link3(match: re.Match[str]) -> str:
        dictionary = match.group(1)
        article = match.group(2)
        label = match.group(3)
        return (
            '<span style="color: blue;" '
            f'title="Ссылка на статью {article} из словаря сокращений {dictionary}">{label}</span>'
        )

    def em_trim(match: re.Match[str]) -> str:
        content = match.group(1)
        content = re.sub(r"[\r\n\t]+", " ", content)
        content = re.sub(r"<[^>]+>", "", content)
        return f"<em>{content.strip()}</em>"

    source = re.sub(r"<([^>@]+)>", create_link1, source)
    source = re.sub(r"<([^>@]+)@([^>@]+)>", create_link2, source)
    source = re.sub(r"<([^>@]+)@([^>@]+)@([^>@]+)>", create_link3, source)

    source = re.sub(
        r"(\[[^]]+\]) \*(\d+) ",
        r'<span style="color: green; font-style: bold;">&#9733;<sup>\2</sup></span>\1 ',
        source,
        flags=re.IGNORECASE,
    )
    source = re.sub(
        r"(\[[^]]+\]) \* ",
        r'<span style="color: green; font-style: bold;">&#9733;</span>\1 ',
        source,
        flags=re.IGNORECASE,
    )
    source = source.replace("_гп._", "_геогр._")
    source = re.sub(r"\[(.*?)\]", r"<strong>\1</strong>", source, flags=re.DOTALL)
    source = re.sub(r"([^\.\n]\s+)(\d+\.)", r"\1\r\n\t<strong>\2</strong>", source)
    source = re.sub(r"_(.*?)_", em_trim, source, flags=re.DOTALL)
    source = re.sub(r"{{\w*}}", "", source, flags=re.IGNORECASE)
    source = re.sub(
        r"{(.*?)}",
        r'<span style="color: green; font-style: italic;">\1</span>',
        source,
        flags=re.DOTALL,
    )
    source = re.sub(r"^!!!.*", "", source, flags=re.MULTILINE)
    source = re.sub(r"`(.{1})", r"\1&#x301;", source, flags=re.UNICODE)
    source = source.replace(" -- ", "&nbsp;&mdash; ")
    source = source.replace(",,", ";")
    source = source.replace("&crt;", "&circ;")
    source = source.replace("&percent;", "%")
    source = re.sub(r"\\sub\\(.+?)\\\/sub\\", r"<sub>\1</sub>", source, flags=re.IGNORECASE | re.DOTALL)
    source = source.replace("\t", "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;")

    source = cxapeligo(source)

    def sencxapeligo_anchor(match: re.Match[str]) -> str:
        href = match.group(1)
        label = match.group(2)
        href = sencxapeligo(href)
        label = cxapeligo(label)
        return f'<a href="{href}">{label}</a>'

    source = re.sub(
        r'<a href="([^"]*?)">(.*?)</a>',
        sencxapeligo_anchor,
        source,
        flags=re.IGNORECASE | re.DOTALL,
    )
    source = source.replace("\r\n", "\n")
    source = source.replace("\n", "<br>")
    return source
    def _generate_variants(self, query: str, language: Language) -> List[str]:
        base = query.strip()
        if not base:
            return []

        variants: list[str] = []

        def add_variant(value: str) -> None:
            normalized = value.strip()
            if normalized and normalized not in variants:
                variants.append(normalized)

        add_variant(base)

        # Roman numeral variants for common cases
        roman_suffixes = ["I", "II", "III", "IV", "V"]
        for suffix in roman_suffixes:
            add_variant(f"{base} {suffix}")

        if not base.startswith("-"):
            add_variant(f"-{base}")
            for suffix in roman_suffixes:
                add_variant(f"-{base} {suffix}")

        if not base.endswith("-"):
            add_variant(f"{base}-")

        if not base.startswith("<<"):
            add_variant(f"<<{base}>>")
            add_variant(f"<<{base}")

        if not base.startswith('"'):
            add_variant(f'"{base}"')

        # Include lowercase/uppercase direct variants
        add_variant(base.lower())
        add_variant(base.upper())

        return variants
