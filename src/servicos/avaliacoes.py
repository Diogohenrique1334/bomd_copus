"""Regras de negócio para coleta de avaliações (notas dos jogadores)."""
from __future__ import annotations

from src.db import repositorio as repo
from src.db.engine import SessionLocal
from src.db.models import Avaliacao, AvaliacaoAdversario

NOTA_MINIMA = 0.0
NOTA_MAXIMA = 10.0


def registrar_avaliacoes(
    *,
    jogo_id: int,
    votante: str,
    notas: dict[int, float | None],
    nota_adversario: float | None = None,
) -> int:
    """Grava as notas de um votante para um jogo (formato longo: 1 linha/jogador).

    ``notas`` mapeia ``jogador_id -> nota`` (use ``None`` para "não jogou").
    ``nota_adversario`` (opcional) é a nota que o votante dá ao time adversário
    naquele jogo — gravada em ``avaliacoes_adversario``.
    Substitui votos anteriores do mesmo votante no mesmo jogo (idempotente),
    respeitando as constraints únicas (jogo, jogador, votante) e (jogo, votante).
    Retorna a quantidade de avaliações de jogadores gravadas.
    """
    votante = votante.strip()
    if not votante:
        raise ValueError("Informe quem está votando.")
    if nota_adversario is not None:
        _validar_nota(nota_adversario)

    with SessionLocal() as session:
        # Remove votos anteriores deste votante neste jogo para permitir reenvio.
        session.query(Avaliacao).filter(
            Avaliacao.jogo_id == jogo_id, Avaliacao.votante == votante
        ).delete(synchronize_session=False)
        session.query(AvaliacaoAdversario).filter(
            AvaliacaoAdversario.jogo_id == jogo_id,
            AvaliacaoAdversario.votante == votante,
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

        if nota_adversario is not None:
            session.add(AvaliacaoAdversario(
                jogo_id=jogo_id, votante=votante, nota=nota_adversario,
            ))

        session.commit()
        return gravadas


def _validar_nota(nota: float) -> None:
    if not (NOTA_MINIMA <= nota <= NOTA_MAXIMA):
        raise ValueError(f"Nota {nota} fora do intervalo {NOTA_MINIMA}–{NOTA_MAXIMA}.")
