"""Regras de negócio para coleta de avaliações (notas dos jogadores)."""
from __future__ import annotations

from src.db import repositorio as repo
from src.db.engine import SessionLocal
from src.db.models import Avaliacao

NOTA_MINIMA = 5.0
NOTA_MAXIMA = 10.0


def registrar_avaliacoes(
    *,
    jogo_id: int,
    votante: str,
    notas: dict[int, float | None],
) -> int:
    """Grava as notas de um votante para um jogo (formato longo: 1 linha/jogador).

    ``notas`` mapeia ``jogador_id -> nota`` (use ``None`` para "não jogou").
    Substitui votos anteriores do mesmo votante no mesmo jogo (idempotente),
    respeitando a constraint única (jogo, jogador, votante).
    Retorna a quantidade de avaliações gravadas.
    """
    votante = votante.strip()
    if not votante:
        raise ValueError("Informe quem está votando.")

    with SessionLocal() as session:
        # Remove votos anteriores deste votante neste jogo para permitir reenvio.
        session.query(Avaliacao).filter(
            Avaliacao.jogo_id == jogo_id, Avaliacao.votante == votante
        ).delete(synchronize_session=False)

        gravadas = 0
        for jogador_id, nota in notas.items():
            jogou = nota is not None
            if jogou:
                _validar_nota(nota)
            repo.adicionar_avaliacao(
                session,
                Avaliacao(
                    jogo_id=jogo_id,
                    jogador_id=jogador_id,
                    votante=votante,
                    nota=nota if jogou else None,
                    jogou=jogou,
                ),
            )
            gravadas += 1

        session.commit()
        return gravadas


def _validar_nota(nota: float) -> None:
    if not (NOTA_MINIMA <= nota <= NOTA_MAXIMA):
        raise ValueError(f"Nota {nota} fora do intervalo {NOTA_MINIMA}–{NOTA_MAXIMA}.")
