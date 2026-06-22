"""Acesso a dados (CRUD puro), sem regra de negócio.

Cada função recebe uma Session aberta pela camada de serviço, executa a
operação e devolve entidades/escalares. Commits ficam a cargo do serviço.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import (
    Adversario,
    Avaliacao,
    Campo,
    Escalacao,
    Gol,
    Jogador,
    Jogo,
)


# ----------------------------- Jogadores -----------------------------
def listar_jogadores(session: Session, apenas_ativos: bool = True) -> list[Jogador]:
    stmt = select(Jogador).order_by(Jogador.nome)
    if apenas_ativos:
        stmt = stmt.where(Jogador.ativo.is_(True))
    return list(session.scalars(stmt))


def obter_jogador(session: Session, jogador_id: int) -> Optional[Jogador]:
    return session.get(Jogador, jogador_id)


def obter_jogador_por_nome(session: Session, nome: str) -> Optional[Jogador]:
    return session.scalar(select(Jogador).where(Jogador.nome == nome))


def criar_jogador(
    session: Session,
    nome: str,
    apelido: Optional[str] = None,
    rg: Optional[str] = None,
    celular: Optional[str] = None,
    posicao: Optional[str] = None,
    data_nascimento: Optional[date] = None,
) -> Jogador:
    jogador = Jogador(
        nome=nome, apelido=apelido, rg=rg, celular=celular, posicao=posicao,
        data_nascimento=data_nascimento,
    )
    session.add(jogador)
    session.flush()
    return jogador


# ---------------------------- Adversários ----------------------------
def listar_adversarios(session: Session) -> list[Adversario]:
    return list(session.scalars(select(Adversario).order_by(Adversario.nome)))


def obter_adversario(session: Session, adversario_id: int) -> Optional[Adversario]:
    return session.get(Adversario, adversario_id)


def obter_adversario_por_nome(session: Session, nome: str) -> Optional[Adversario]:
    return session.scalar(select(Adversario).where(Adversario.nome == nome))


def criar_adversario(
    session: Session, nome: str, bairro: Optional[str] = None
) -> Adversario:
    adversario = Adversario(nome=nome, bairro=bairro)
    session.add(adversario)
    session.flush()
    return adversario


# ------------------------------- Campos ------------------------------
def listar_campos(session: Session) -> list[Campo]:
    return list(session.scalars(select(Campo).order_by(Campo.nome)))


def obter_campo(session: Session, campo_id: int) -> Optional[Campo]:
    return session.get(Campo, campo_id)


def obter_campo_por_nome(session: Session, nome: str, cidade: Optional[str] = None) -> Optional[Campo]:
    stmt = select(Campo).where(Campo.nome == nome)
    if cidade is not None:
        stmt = stmt.where(Campo.cidade == cidade)
    return session.scalar(stmt)


def criar_campo(session: Session, nome: str, cidade: Optional[str] = None) -> Campo:
    campo = Campo(nome=nome, cidade=cidade)
    session.add(campo)
    session.flush()
    return campo


# ------------------------------- Jogos -------------------------------
def listar_jogos(session: Session) -> list[Jogo]:
    return list(session.scalars(select(Jogo).order_by(Jogo.data.desc())))


def criar_jogo(
    session: Session,
    data_jogo: date,
    tipo: Optional[str],
    adversario_id: Optional[int],
    campo_id: Optional[int],
    cor_uniforme: Optional[str],
    gols_bdc: int,
    gols_adversario: int,
    casa: Optional[bool] = None,
) -> Jogo:
    jogo = Jogo(
        data=data_jogo,
        tipo=tipo,
        adversario_id=adversario_id,
        campo_id=campo_id,
        cor_uniforme=cor_uniforme,
        gols_bdc=gols_bdc,
        gols_adversario=gols_adversario,
        casa=casa,
    )
    session.add(jogo)
    session.flush()
    return jogo


# ----------------------------- Avaliações ----------------------------
def adicionar_avaliacao(session: Session, avaliacao: Avaliacao) -> None:
    session.add(avaliacao)


# ------------------------------- Gols --------------------------------
def adicionar_gol(session: Session, gol: Gol) -> None:
    session.add(gol)


# ----------------------------- Escalações ----------------------------
def listar_escalacao(
    session: Session, jogo_id: int, momento: str
) -> list[Escalacao]:
    return list(
        session.scalars(
            select(Escalacao)
            .where(Escalacao.jogo_id == jogo_id, Escalacao.momento == momento)
            .order_by(Escalacao.ordem)
        )
    )


def remover_escalacao(session: Session, jogo_id: int, momento: str) -> None:
    """Apaga todas as linhas da escalação de um (jogo, momento)."""
    for esc in listar_escalacao(session, jogo_id, momento):
        session.delete(esc)
    session.flush()


def adicionar_escalacao_slot(session: Session, escalacao: Escalacao) -> None:
    session.add(escalacao)
