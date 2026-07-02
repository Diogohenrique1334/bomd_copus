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
def listar_jogadores(
    session: Session, apenas_ativos: bool = True, apenas_atletas: bool = True
) -> list[Jogador]:
    stmt = select(Jogador).order_by(Jogador.nome)
    if apenas_ativos:
        stmt = stmt.where(Jogador.ativo.is_(True))
    if apenas_atletas:
        stmt = stmt.where(Jogador.eh_atleta.is_(True))
    return list(session.scalars(stmt))


def listar_auxiliares(session: Session) -> list[Jogador]:
    """Entradas não-atleta (ex.: 'Gol Contra'), usadas só p/ registrar gols."""
    return list(
        session.scalars(
            select(Jogador)
            .where(Jogador.eh_atleta.is_(False))
            .order_by(Jogador.nome)
        )
    )


def listar_votantes(session: Session) -> list[Jogador]:
    """Atletas aptos a votar nas avaliações: Diretores e Capitães.

    Inclui inativos de propósito (um diretor/capitão afastado ainda vota) e
    exclui as entradas auxiliares (eh_atleta=False).
    """
    return list(
        session.scalars(
            select(Jogador)
            .where(
                Jogador.eh_atleta.is_(True),
                Jogador.papel.in_(("Diretor", "Capitao")),
            )
            .order_by(Jogador.nome)
        )
    )


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
    papel: str = "Comum",
    foto: Optional[bytes] = None,
) -> Jogador:
    jogador = Jogador(
        nome=nome, apelido=apelido, rg=rg, celular=celular, posicao=posicao,
        data_nascimento=data_nascimento, papel=papel, foto=foto,
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


def criar_campo(
    session: Session,
    nome: str,
    cidade: Optional[str] = None,
    nota_qualidade: Optional[float] = None,
    nota_distancia: Optional[float] = None,
) -> Campo:
    campo = Campo(
        nome=nome, cidade=cidade,
        nota_qualidade=nota_qualidade, nota_distancia=nota_distancia,
    )
    session.add(campo)
    session.flush()
    return campo


def reatribuir_campo_jogos(session: Session, de_id: int, para_id: int) -> None:
    """Move todos os jogos do campo `de_id` para `para_id` (usado na fusão)."""
    for jogo in session.scalars(select(Jogo).where(Jogo.campo_id == de_id)):
        jogo.campo_id = para_id
    session.flush()


def excluir_campo(session: Session, campo_id: int) -> None:
    campo = session.get(Campo, campo_id)
    if campo:
        session.delete(campo)


def reatribuir_adversario_jogos(session: Session, de_id: int, para_id: int) -> None:
    """Move todos os jogos do adversário `de_id` para `para_id` (fusão)."""
    for jogo in session.scalars(select(Jogo).where(Jogo.adversario_id == de_id)):
        jogo.adversario_id = para_id
    session.flush()


def excluir_adversario(session: Session, adversario_id: int) -> None:
    adv = session.get(Adversario, adversario_id)
    if adv:
        session.delete(adv)


# ------------------------------- Jogos -------------------------------
def listar_jogos(session: Session) -> list[Jogo]:
    return list(session.scalars(select(Jogo).order_by(Jogo.data.desc())))


def obter_jogo(session: Session, jogo_id: int) -> Optional[Jogo]:
    return session.get(Jogo, jogo_id)


def definir_capitao(session: Session, jogo_id: int, jogador_id: Optional[int]) -> None:
    """Define (ou limpa, com None) o capitão de um jogo."""
    jogo = session.get(Jogo, jogo_id)
    if jogo:
        jogo.capitao_id = jogador_id


def existe_jogo_na_data(
    session: Session, data_jogo: date, excluir_id: Optional[int] = None
) -> bool:
    """True se já há jogo nessa data (ignorando `excluir_id`, útil na edição)."""
    stmt = select(Jogo.id).where(Jogo.data == data_jogo)
    if excluir_id is not None:
        stmt = stmt.where(Jogo.id != excluir_id)
    return session.scalar(stmt) is not None


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


def listar_gols(session: Session, jogo_id: int) -> list[Gol]:
    return list(
        session.scalars(
            select(Gol).where(Gol.jogo_id == jogo_id).order_by(Gol.ordem)
        )
    )


def remover_gols(session: Session, jogo_id: int) -> None:
    """Apaga todos os gols de um jogo (usado ao reescrever os gols na edição)."""
    for gol in listar_gols(session, jogo_id):
        session.delete(gol)
    session.flush()


def excluir_jogo(session: Session, jogo_id: int) -> None:
    """Remove o jogo; o cascade apaga gols, avaliações e escalações."""
    jogo = session.get(Jogo, jogo_id)
    if jogo:
        session.delete(jogo)


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


def jogadores_escalados(session: Session, jogo_id: int) -> list[int]:
    """IDs distintos de atletas escalados no jogo (qualquer momento)."""
    return list(
        session.scalars(
            select(Escalacao.jogador_id)
            .where(Escalacao.jogo_id == jogo_id)
            .distinct()
        )
    )
