from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, Index, Integer, String, Text, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

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
    komento: Mapped[str | None] = mapped_column(String(2048))


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
    komento: Mapped[str | None] = mapped_column(String(2048))


class SearchEntry(Base):
    __tablename__ = "sercxo"
    __table_args__ = (Index("ix_sercxo_vorto", "vorto"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    art_id: Mapped[int | None] = mapped_column(Integer)
    vorto: Mapped[str | None] = mapped_column(String(255))
    priskribo: Mapped[str | None] = mapped_column(Text)


class SearchEntryRu(Base):
    __tablename__ = "sercxo_ru"
    __table_args__ = (Index("ix_sercxo_ru_vorto", "vorto"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    art_id: Mapped[int | None] = mapped_column(Integer)
    vorto: Mapped[str | None] = mapped_column(String(255))
    priskribo: Mapped[str | None] = mapped_column(Text)


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
    vorto: Mapped[str | None] = mapped_column(String(255))
    dato: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    hip: Mapped[str | None] = mapped_column(String(45))


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("username", name="uq_users_username"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(150), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, server_default=func.now()
    )
