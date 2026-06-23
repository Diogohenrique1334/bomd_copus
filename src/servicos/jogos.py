"""Regras de negócio para cadastro de jogos e gols.

Adversário, campo e atletas (autor/assistente) precisam estar previamente
cadastrados — aqui só referenciamos seus ids.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from src.db import repositorio as repo
from src.db.engine import SessionLocal
from src.db.models import Gol, Jogo

CORES_UNIFORME = [
    "Branco", "Preto", "Vermelho", "Azul", "Verde",
    "Amarelo", "Laranja", "Roxo", "Cinza", "Rosa",
]


@dataclass
class GolInput:
    """Dados de um gol informados na tela de registro (ids já cadastrados)."""
    autor_id: int
    assistente_id: Optional[int] = None
    posicao: Optional[str] = None
    forma: Optional[str] = None
    local: Optional[str] = None
    tempo: Optional[str] = None


@dataclass
class GolDetalhe:
    """Gol já gravado, materializado para pré-preencher a edição."""
    autor_id: int
    assistente_id: Optional[int]
    posicao: Optional[str]
    forma: Optional[str]
    local: Optional[str]
    tempo: Optional[str]


@dataclass
class JogoDetalhe:
    """DTO completo de um jogo p/ a tela de edição (campos editáveis + FKs)."""
    id: int
    data: date
    tipo: Optional[str]
    adversario_id: Optional[int]
    campo_id: Optional[int]
    cor_uniforme: Optional[str]
    casa: Optional[bool]
    gols_bdc: int
    gols_adversario: int


@dataclass
class JogoResumo:
    """DTO leve de um jogo, com nomes já materializados para uso na UI.

    Evita vazar entidades ORM para o Streamlit (que dispararia lazy load fora
    da sessão).
    """
    id: int
    data: date
    tipo: Optional[str]
    adversario: Optional[str]
    campo: Optional[str]

    def rotulo(self) -> str:
        return f"{self.data:%d/%m/%Y} — {self.adversario or 'sem adversário'} ({self.tipo or '—'})"


def listar_jogos_resumo(limite: Optional[int] = None) -> list[JogoResumo]:
    """Lista os jogos (mais recentes primeiro) como DTOs prontos para seleção.

    `limite`: se informado, devolve apenas os N jogos mais recentes.
    """
    with SessionLocal() as session:
        stmt = (
            select(Jogo)
            .options(joinedload(Jogo.adversario), joinedload(Jogo.campo))
            .order_by(Jogo.data.desc())
        )
        if limite is not None:
            stmt = stmt.limit(limite)
        jogos = session.scalars(stmt).all()
        return [
            JogoResumo(
                id=j.id,
                data=j.data,
                tipo=j.tipo,
                adversario=j.adversario.nome if j.adversario else None,
                campo=j.campo.nome if j.campo else None,
            )
            for j in jogos
        ]


def obter_jogo_detalhe(jogo_id: int) -> Optional[JogoDetalhe]:
    """Carrega um jogo como DTO completo p/ edição (None se não existir)."""
    with SessionLocal() as session:
        j = repo.obter_jogo(session, jogo_id)
        if not j:
            return None
        return JogoDetalhe(
            id=j.id, data=j.data, tipo=j.tipo,
            adversario_id=j.adversario_id, campo_id=j.campo_id,
            cor_uniforme=j.cor_uniforme, casa=j.casa,
            gols_bdc=j.gols_bdc, gols_adversario=j.gols_adversario,
        )


def listar_gols_do_jogo(jogo_id: int) -> list[GolDetalhe]:
    """Gols já gravados de um jogo, em ordem, p/ pré-preencher a edição."""
    with SessionLocal() as session:
        return [
            GolDetalhe(
                autor_id=g.jogador_id,
                assistente_id=g.assistente_id,
                posicao=g.posicao,
                forma=g.forma,
                local=g.local,
                tempo=g.tempo,
            )
            for g in repo.listar_gols(session, jogo_id)
        ]


def excluir_jogo(jogo_id: int) -> None:
    """Exclui um jogo e, em cascata, seus gols, avaliações e escalações."""
    with SessionLocal() as session:
        repo.excluir_jogo(session, jogo_id)
        session.commit()


def editar_jogo(
    jogo_id: int,
    *,
    data_jogo: date,
    tipo: Optional[str],
    adversario_id: Optional[int],
    campo_id: Optional[int],
    cor_uniforme: Optional[str],
    casa: Optional[bool],
    gols_bdc: int,
    gols_adversario: int,
    gols: Optional[list[GolInput]] = None,
) -> None:
    """Atualiza as informações de um jogo.

    Se `gols` for informado, **reescreve** os gols do jogo (apaga os antigos e
    grava os novos). Se for None, mantém os gols existentes.
    """
    with SessionLocal() as session:
        jogo = repo.obter_jogo(session, jogo_id)
        if not jogo:
            raise ValueError("Jogo não encontrado.")
        if repo.existe_jogo_na_data(session, data_jogo, excluir_id=jogo_id):
            raise ValueError(f"Já existe outro jogo em {data_jogo:%d/%m/%Y}.")
        jogo.data = data_jogo
        jogo.tipo = tipo
        jogo.adversario_id = adversario_id
        jogo.campo_id = campo_id
        jogo.cor_uniforme = cor_uniforme
        jogo.casa = casa
        jogo.gols_bdc = gols_bdc
        jogo.gols_adversario = gols_adversario

        if gols is not None:
            repo.remover_gols(session, jogo_id)
            for ordem, g in enumerate(gols, start=1):
                repo.adicionar_gol(
                    session,
                    Gol(
                        jogo_id=jogo_id,
                        jogador_id=g.autor_id,
                        assistente_id=g.assistente_id,
                        ordem=ordem,
                        posicao=g.posicao,
                        forma=g.forma,
                        local=g.local,
                        tempo=g.tempo,
                    ),
                )

        session.commit()


def registrar_jogo(
    *,
    data_jogo: date,
    tipo: Optional[str],
    adversario_id: Optional[int],
    campo_id: Optional[int],
    cor_uniforme: Optional[str],
    gols_bdc: int,
    gols_adversario: int,
    gols: list[GolInput],
    casa: Optional[bool] = None,
) -> int:
    """Cria um jogo e seus gols em uma única transação. Retorna o id do jogo."""
    with SessionLocal() as session:
        if repo.existe_jogo_na_data(session, data_jogo):
            raise ValueError(
                f"Já existe um jogo cadastrado em {data_jogo:%d/%m/%Y}. "
                "Não é permitido cadastrar dois jogos no mesmo dia."
            )
        jogo = repo.criar_jogo(
            session,
            data_jogo=data_jogo,
            tipo=tipo,
            adversario_id=adversario_id,
            campo_id=campo_id,
            cor_uniforme=cor_uniforme,
            gols_bdc=gols_bdc,
            gols_adversario=gols_adversario,
            casa=casa,
        )

        for ordem, g in enumerate(gols, start=1):
            repo.adicionar_gol(
                session,
                Gol(
                    jogo_id=jogo.id,
                    jogador_id=g.autor_id,
                    assistente_id=g.assistente_id,
                    ordem=ordem,
                    posicao=g.posicao,
                    forma=g.forma,
                    local=g.local,
                    tempo=g.tempo,
                ),
            )

        session.commit()
        return jogo.id
