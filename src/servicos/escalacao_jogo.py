"""Registro manual da escalação de um jogo (11 iniciais e 11 finais).

Diferente de `escalacao.py` (sugestão heurística, somente leitura para o
dashboard): aqui o usuário escolhe o esquema e atribui um atleta a cada posição,
e os dois momentos do jogo são persistidos no formato longo (1 linha por slot na
tabela `escalacoes`).
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from src.db import repositorio as repo
from src.db.engine import SessionLocal
from src.db.models import Escalacao
from src.servicos.escalacao import FORMACOES

# momento técnico -> rótulo exibido na UI
MOMENTOS: Dict[str, str] = {"inicial": "11 Iniciais", "final": "11 Finais"}


def slots_da_formacao(formacao: str) -> List[Tuple[str, dict]]:
    """Lista de (slot_key único, slot_dict com x/y/ordem) para a formação.

    O rótulo da posição (GOL/ZAG/ATA...) repete dentro de uma formação, mas o
    slot precisa ser único por (jogo, momento) — então posições repetidas recebem
    sufixo numérico (ZAG1, ZAG2...). A geração é determinística, então o
    pré-carregamento da escalação salva casa com as chaves recriadas aqui.
    """
    total: Dict[str, int] = {}
    for s in FORMACOES[formacao]:
        total[s["slot"]] = total.get(s["slot"], 0) + 1

    contagem: Dict[str, int] = {}
    saida: List[Tuple[str, dict]] = []
    for ordem, s in enumerate(FORMACOES[formacao], start=1):
        label = s["slot"]
        if total[label] > 1:
            contagem[label] = contagem.get(label, 0) + 1
            key = f"{label}{contagem[label]}"
        else:
            key = label
        saida.append((key, {**s, "ordem": ordem}))
    return saida


def rotulo_posicao(slot_key: str) -> str:
    """Remove o sufixo numérico do slot_key para exibir só a posição (ZAG2 -> ZAG)."""
    return slot_key.rstrip("0123456789")


def salvar(
    jogo_id: int,
    momento: str,
    formacao: str,
    atribuicoes: Dict[str, Optional[int]],
) -> int:
    """Substitui a escalação de (jogo, momento). Retorna o nº de slots gravados.

    `atribuicoes`: {slot_key: jogador_id|None}. Slots vazios são ignorados.
    """
    if momento not in MOMENTOS:
        raise ValueError("Momento inválido.")
    if formacao not in FORMACOES:
        raise ValueError("Formação inválida.")

    slots = slots_da_formacao(formacao)
    with SessionLocal() as session:
        repo.remover_escalacao(session, jogo_id, momento)
        gravados = 0
        for slot_key, s in slots:
            jogador_id = atribuicoes.get(slot_key)
            if not jogador_id:
                continue
            repo.adicionar_escalacao_slot(
                session,
                Escalacao(
                    jogo_id=jogo_id,
                    momento=momento,
                    formacao=formacao,
                    slot=slot_key,
                    jogador_id=jogador_id,
                    x=s["x"],
                    y=s["y"],
                    ordem=s["ordem"],
                ),
            )
            gravados += 1
        session.commit()
        return gravados


def atletas_do_jogo(jogo_id: int) -> set:
    """IDs dos atletas que estiveram em alguma escalação (inicial ou final) do jogo."""
    with SessionLocal() as session:
        return set(repo.jogadores_escalados(session, jogo_id))


def definir_capitao(jogo_id: int, jogador_id: Optional[int]) -> None:
    """Define (ou limpa, com None) o capitão do jogo."""
    with SessionLocal() as session:
        repo.definir_capitao(session, jogo_id, jogador_id)
        session.commit()


def obter_capitao(jogo_id: int) -> Optional[int]:
    """ID do capitão do jogo (None se não definido)."""
    with SessionLocal() as session:
        jogo = repo.obter_jogo(session, jogo_id)
        return jogo.capitao_id if jogo else None


def obter(jogo_id: int, momento: str) -> Optional[dict]:
    """Escalação salva de (jogo, momento).

    Retorna {"formacao": str, "atribuicoes": {slot_key: jogador_id}} ou None.
    """
    with SessionLocal() as session:
        linhas = repo.listar_escalacao(session, jogo_id, momento)
        if not linhas:
            return None
        return {
            "formacao": linhas[0].formacao,
            "atribuicoes": {linha.slot: linha.jogador_id for linha in linhas},
        }
