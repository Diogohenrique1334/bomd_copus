"""Modelos ORM (SQLAlchemy 2.0) do BDC App — formato normalizado (longo).

Tabelas:
    jogadores   — elenco do time (com cadastro completo: apelido, rg, celular...).
    adversarios — times adversários (nome + bairro).
    campos      — locais de jogo (nome + cidade).
    jogos       — cada partida disputada (referencia adversário e campo cadastrados).
    avaliacoes  — uma nota por (votante, jogo, jogador).
    gols        — cada gol marcado pelo BDC, com seus detalhes.

Observação: os type hints usam typing.Optional/List (em vez de ``X | None``)
porque o SQLAlchemy resolve as anotações em runtime e o projeto roda em
Python 3.9, onde o operador ``|`` de união ainda não existe.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Jogador(Base):
    __tablename__ = "jogadores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    apelido: Mapped[Optional[str]] = mapped_column(String(60))
    rg: Mapped[Optional[str]] = mapped_column(String(20))
    celular: Mapped[Optional[str]] = mapped_column(String(20))
    posicao: Mapped[Optional[str]] = mapped_column(String(40))
    data_nascimento: Mapped[Optional[date]] = mapped_column(Date)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    avaliacoes: Mapped[List["Avaliacao"]] = relationship(back_populates="jogador")
    gols: Mapped[List["Gol"]] = relationship(
        back_populates="autor", foreign_keys="Gol.jogador_id"
    )


class Adversario(Base):
    __tablename__ = "adversarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    bairro: Mapped[Optional[str]] = mapped_column(String(80))

    jogos: Mapped[List["Jogo"]] = relationship(back_populates="adversario")


class Campo(Base):
    __tablename__ = "campos"
    __table_args__ = (UniqueConstraint("nome", "cidade", name="uq_campo_nome_cidade"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(80), nullable=False)
    cidade: Mapped[Optional[str]] = mapped_column(String(80))

    jogos: Mapped[List["Jogo"]] = relationship(back_populates="campo")


class Jogo(Base):
    __tablename__ = "jogos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    data: Mapped[date] = mapped_column(Date, nullable=False)
    tipo: Mapped[Optional[str]] = mapped_column(String(30))   # Amistoso/Festival/Campeonato
    adversario_id: Mapped[Optional[int]] = mapped_column(ForeignKey("adversarios.id"))
    campo_id: Mapped[Optional[int]] = mapped_column(ForeignKey("campos.id"))
    cor_uniforme: Mapped[Optional[str]] = mapped_column(String(40))
    casa: Mapped[Optional[bool]] = mapped_column(Boolean)   # True=jogo em casa, False=fora
    gols_bdc: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    gols_adversario: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    adversario: Mapped[Optional["Adversario"]] = relationship(back_populates="jogos")
    campo: Mapped[Optional["Campo"]] = relationship(back_populates="jogos")
    avaliacoes: Mapped[List["Avaliacao"]] = relationship(
        back_populates="jogo", cascade="all, delete-orphan"
    )
    gols: Mapped[List["Gol"]] = relationship(
        back_populates="jogo", cascade="all, delete-orphan"
    )
    escalacoes: Mapped[List["Escalacao"]] = relationship(
        back_populates="jogo", cascade="all, delete-orphan"
    )


class Avaliacao(Base):
    __tablename__ = "avaliacoes"
    __table_args__ = (
        UniqueConstraint("jogo_id", "jogador_id", "votante", name="uq_voto_unico"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    jogo_id: Mapped[int] = mapped_column(ForeignKey("jogos.id"), nullable=False)
    jogador_id: Mapped[int] = mapped_column(ForeignKey("jogadores.id"), nullable=False)
    votante: Mapped[str] = mapped_column(String(80), nullable=False)
    nota: Mapped[Optional[float]] = mapped_column(Float)   # 5.0–10.0; None quando jogou=False
    jogou: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    jogo: Mapped["Jogo"] = relationship(back_populates="avaliacoes")
    jogador: Mapped["Jogador"] = relationship(back_populates="avaliacoes")


class Gol(Base):
    __tablename__ = "gols"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    jogo_id: Mapped[int] = mapped_column(ForeignKey("jogos.id"), nullable=False)
    jogador_id: Mapped[int] = mapped_column(ForeignKey("jogadores.id"), nullable=False)
    assistente_id: Mapped[Optional[int]] = mapped_column(ForeignKey("jogadores.id"))
    ordem: Mapped[Optional[int]] = mapped_column(Integer)        # 1º, 2º... gol da partida
    posicao: Mapped[Optional[str]] = mapped_column(String(40))   # posição em que jogava
    forma: Mapped[Optional[str]] = mapped_column(String(40))     # chute, cabeça, falta, pênalti...
    local: Mapped[Optional[str]] = mapped_column(String(40))     # dentro/fora da área, pênalti, olímpico
    tempo: Mapped[Optional[str]] = mapped_column(String(10))     # 1º / 2º

    jogo: Mapped["Jogo"] = relationship(back_populates="gols")
    autor: Mapped["Jogador"] = relationship(
        back_populates="gols", foreign_keys=[jogador_id]
    )
    assistente: Mapped[Optional["Jogador"]] = relationship(foreign_keys=[assistente_id])


class Escalacao(Base):
    """Um slot da escalação de um jogo (formato longo: 1 linha por posição).

    `momento` distingue os dois registros do mesmo jogo: 'inicial' (os 11 que
    começaram) e 'final' (os 11 que terminaram). Reenviar uma escalação para o
    mesmo (jogo, momento) substitui as linhas anteriores.
    """
    __tablename__ = "escalacoes"
    __table_args__ = (
        UniqueConstraint("jogo_id", "momento", "slot", name="uq_escalacao_slot"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    jogo_id: Mapped[int] = mapped_column(ForeignKey("jogos.id"), nullable=False)
    momento: Mapped[str] = mapped_column(String(10), nullable=False)  # inicial / final
    formacao: Mapped[Optional[str]] = mapped_column(String(20))       # ex.: 4-3-3
    slot: Mapped[str] = mapped_column(String(10), nullable=False)     # GOL, ZAG, ATA...
    jogador_id: Mapped[int] = mapped_column(ForeignKey("jogadores.id"), nullable=False)
    x: Mapped[Optional[int]] = mapped_column(Integer)
    y: Mapped[Optional[int]] = mapped_column(Integer)
    ordem: Mapped[Optional[int]] = mapped_column(Integer)

    jogo: Mapped["Jogo"] = relationship(back_populates="escalacoes")
    jogador: Mapped["Jogador"] = relationship()
