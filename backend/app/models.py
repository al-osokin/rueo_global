from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


article_status_enum = Enum(
    "j",
    "n",
    name="lasta_status_enum",
    native_enum=False,
    create_constraint=True,
)


class Article(Base):
    __tablename__ = "artikoloj"

    art_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    priskribo: Mapped[str] = mapped_column(Text, nullable=False)
    lasta: Mapped[str] = mapped_column(article_status_enum, nullable=False, default="j")
    uz_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tempo: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    komento: Mapped[Optional[str]] = mapped_column(String(2048))


class ArticleRu(Base):
    __tablename__ = "artikoloj_ru"

    art_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    priskribo: Mapped[str] = mapped_column(Text, nullable=False)
    lasta: Mapped[str] = mapped_column(article_status_enum, nullable=False, default="j")
    uz_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tempo: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    komento: Mapped[Optional[str]] = mapped_column(String(2048))


class SearchEntry(Base):
    __tablename__ = "sercxo"
    __table_args__ = (Index("ix_sercxo_vorto", "vorto"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    art_id: Mapped[Optional[int]] = mapped_column(Integer)
    vorto: Mapped[Optional[str]] = mapped_column(String(255))
    priskribo: Mapped[Optional[str]] = mapped_column(Text)


class SearchEntryRu(Base):
    __tablename__ = "sercxo_ru"
    __table_args__ = (Index("ix_sercxo_ru_vorto", "vorto"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    art_id: Mapped[Optional[int]] = mapped_column(Integer)
    vorto: Mapped[Optional[str]] = mapped_column(String(255))
    priskribo: Mapped[Optional[str]] = mapped_column(Text)


class FuzzyEntry(Base):
    __tablename__ = "neklaraj"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    neklara_vorto: Mapped[str] = mapped_column(String(255), nullable=False)
    klara_vorto: Mapped[str] = mapped_column(String(255), nullable=False)


class SearchStat(Base):
    __tablename__ = "statistiko"
    __table_args__ = (
        Index("ix_statistiko_dato", "dato"),
        Index("ix_statistiko_hip", "hip"),
        Index("ix_statistiko_vorto", "vorto"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vorto: Mapped[Optional[str]] = mapped_column(String(255))
    dato: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False))
    hip: Mapped[Optional[str]] = mapped_column(String(45))


class ArticleFileState(Base):
    __tablename__ = "article_file_states"
    __table_args__ = (UniqueConstraint("lang", "file_path", name="uq_article_file_state"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lang: Mapped[str] = mapped_column(String(4), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False))
    last_modified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False))

    articles: Mapped[list["ArticleState"]] = relationship(
        "ArticleState",
        back_populates="file_state",
        cascade="all, delete-orphan",
    )


class ArticleState(Base):
    __tablename__ = "article_states"
    __table_args__ = (
        UniqueConstraint(
            "file_state_id",
            "canonical_key",
            "canonical_occurrence",
            name="uq_article_state",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_state_id: Mapped[int] = mapped_column(ForeignKey("article_file_states.id"), nullable=False)
    article_index: Mapped[int] = mapped_column(Integer, nullable=False)
    canonical_key: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_occurrence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    last_header_line: Mapped[Optional[str]] = mapped_column(String(255))
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False))

    file_state: Mapped[ArticleFileState] = relationship("ArticleFileState", back_populates="articles")


class ArticleChangeLog(Base):
    __tablename__ = "article_change_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_state_id: Mapped[int] = mapped_column(ForeignKey("article_file_states.id"), nullable=False)
    canonical_key: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_occurrence: Mapped[int] = mapped_column(Integer, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())
    old_checksum: Mapped[Optional[str]] = mapped_column(String(128))
    new_checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    old_header_line: Mapped[Optional[str]] = mapped_column(String(255))
    new_header_line: Mapped[Optional[str]] = mapped_column(String(255))
    action: Mapped[Optional[str]] = mapped_column(String(128))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    file_state: Mapped[ArticleFileState] = relationship("ArticleFileState")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("username", name="uq_users_username"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(150), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, server_default=func.now()
    )


class ArticleParseState(Base):
    __tablename__ = "article_parse_state"
    __table_args__ = (UniqueConstraint("lang", "art_id", name="uq_article_parse_state"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lang: Mapped[str] = mapped_column(String(4), nullable=False)
    art_id: Mapped[int] = mapped_column(Integer, nullable=False)
    parsing_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    template: Mapped[Optional[str]] = mapped_column(String(128))
    headword: Mapped[Optional[str]] = mapped_column(String(512))
    example_count: Mapped[Optional[int]] = mapped_column(Integer)
    first_example_eo: Mapped[Optional[str]] = mapped_column(Text)
    first_example_ru: Mapped[Optional[str]] = mapped_column(Text)
    parsed_payload: Mapped[Optional[dict]] = mapped_column(JSON)
    resolved_translations: Mapped[Optional[dict]] = mapped_column(JSON)
    has_notes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False))
    parsed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ArticleParseNote(Base):
    __tablename__ = "article_parse_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lang: Mapped[str] = mapped_column(String(4), nullable=False)
    art_id: Mapped[int] = mapped_column(Integer, nullable=False)
    author: Mapped[Optional[str]] = mapped_column(String(128))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_article_parse_notes_lang_art", "lang", "art_id"),
    )
