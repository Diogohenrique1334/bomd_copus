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


def listar_jogos_resumo() -> list[JogoResumo]:
    """Lista os jogos (mais recentes primeiro) como DTOs prontos para seleção."""
    with SessionLocal() as session:
        jogos = session.scalars(
            select(Jogo)
            .options(joinedload(Jogo.adversario), joinedload(Jogo.campo))
            .order_by(Jogo.data.desc())
        ).all()
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
