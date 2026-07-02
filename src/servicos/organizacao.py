"""Pente-fino de cadastros: detecta e funde campos/adversários duplicados.

Muitos campos e adversários foram digitados à mão (histórico das planilhas),
então o mesmo lugar aparece escrito de formas diferentes ("São Paulo", "Sao
Paulo", "SPFC"). Aqui:

- `sugerir_duplicados_*` agrupa registros com nomes parecidos (ignorando acento,
  caixa e espaços; refina com similaridade de string) para o usuário revisar;
- `fundir_*` reatribui os jogos do(s) duplicado(s) para o registro escolhido como
  correto (destino) e apaga os duplicados, tudo em uma transação.

Só leitura/escrita de cadastro — nenhuma regra de avaliação aqui.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import List

from src.db import repositorio as repo
from src.db.engine import SessionLocal

# Acima deste grau de similaridade dois nomes são tratados como candidatos a
# duplicata (0..1). 0.85 pega variações de digitação sem juntar times distintos.
LIMIAR = 0.85


@dataclass
class ItemCadastro:
    """DTO leve de um campo/adversário para a UI de fusão (sem ORM vazando)."""
    id: int
    nome: str
    detalhe: str   # cidade (campo) ou bairro (adversário), só p/ exibir


def _normalizar(texto: str) -> str:
    """Minúsculas, sem acento e com espaços colapsados (chave de comparação)."""
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFKD", texto or "")
        if not unicodedata.combining(c)
    )
    return " ".join(sem_acento.lower().split())


def _agrupar_parecidos(itens: List[ItemCadastro]) -> List[List[ItemCadastro]]:
    """Agrupa itens cujos nomes normalizados são iguais ou muito parecidos.

    Devolve só os grupos com 2+ itens (candidatos a fusão), maiores primeiro.
    """
    normalizados = [(item, _normalizar(item.nome)) for item in itens]
    usados: set = set()
    grupos: List[List[ItemCadastro]] = []

    for i, (item_i, norm_i) in enumerate(normalizados):
        if i in usados:
            continue
        grupo = [item_i]
        usados.add(i)
        for j in range(i + 1, len(normalizados)):
            if j in usados:
                continue
            item_j, norm_j = normalizados[j]
            if norm_i == norm_j or SequenceMatcher(None, norm_i, norm_j).ratio() >= LIMIAR:
                grupo.append(item_j)
                usados.add(j)
        if len(grupo) > 1:
            grupos.append(grupo)

    grupos.sort(key=len, reverse=True)
    return grupos


# ------------------------------- Campos ------------------------------
def sugerir_duplicados_campos() -> List[List[ItemCadastro]]:
    with SessionLocal() as session:
        itens = [
            ItemCadastro(id=c.id, nome=c.nome, detalhe=c.cidade or "")
            for c in repo.listar_campos(session)
        ]
    return _agrupar_parecidos(itens)


def fundir_campos(destino_id: int, origem_ids: List[int]) -> int:
    """Move os jogos dos `origem_ids` para `destino_id` e apaga os origens.

    Retorna quantos registros foram fundidos (apagados).
    """
    origem_ids = [oid for oid in origem_ids if oid != destino_id]
    with SessionLocal() as session:
        for oid in origem_ids:
            repo.reatribuir_campo_jogos(session, oid, destino_id)
            repo.excluir_campo(session, oid)
        session.commit()
    return len(origem_ids)


# ---------------------------- Adversários ----------------------------
def sugerir_duplicados_adversarios() -> List[List[ItemCadastro]]:
    with SessionLocal() as session:
        itens = [
            ItemCadastro(id=a.id, nome=a.nome, detalhe=a.bairro or "")
            for a in repo.listar_adversarios(session)
        ]
    return _agrupar_parecidos(itens)


def fundir_adversarios(destino_id: int, origem_ids: List[int]) -> int:
    origem_ids = [oid for oid in origem_ids if oid != destino_id]
    with SessionLocal() as session:
        for oid in origem_ids:
            repo.reatribuir_adversario_jogos(session, oid, destino_id)
            repo.excluir_adversario(session, oid)
        session.commit()
    return len(origem_ids)
