"""Camada de filtros do dashboard.

Centraliza:
- o dataclass `Filtros` (estado escolhido na UI);
- a montagem da cláusula SQL injetável nas queries de `stats.py`;
- helpers de leitura que populam os seletores (anos, tipos, posições).

Mantém `stats.py` agnóstico de UI: cada função de stats só recebe um `Filtros`
e injeta `filtros.clausula_jogos(alias)` no WHERE da sua query.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy import text

from src.db.engine import get_engine

MESES_PT: Dict[int, str] = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}


@dataclass
class Filtros:
    """Estado dos filtros escolhidos na UI.

    `None` em qualquer campo significa "todos" (sem restrição).
    Os campos `ano/mes/tipo` atuam sobre a tabela `jogos`; `posicao` atua sobre
    `jogadores` e só é aplicado nas seções de Avaliações e Gols.
    """

    ano: Optional[int] = None
    mes: Optional[int] = None
    tipo: Optional[str] = None
    posicao: Optional[str] = None

    # ── Cláusulas SQL ─────────────────────────────────────────────────────────
    def clausula_jogos(self, alias: str = "jogos", incluir_mes: bool = True) -> Tuple[str, dict]:
        """Condições sobre a tabela de jogos (`alias` = como ela aparece na query).

        Retorna ``(sql, params)`` onde `sql` começa com ``" AND ..."`` (ou vazio),
        pronto para ser concatenado depois de um ``WHERE`` já existente.
        """
        cond: List[str] = []
        params: dict = {}
        if self.ano is not None:
            cond.append(f"EXTRACT(YEAR FROM {alias}.data) = :f_ano")
            params["f_ano"] = self.ano
        if self.mes is not None and incluir_mes:
            cond.append(f"EXTRACT(MONTH FROM {alias}.data) = :f_mes")
            params["f_mes"] = self.mes
        if self.tipo:
            cond.append(f"{alias}.tipo = :f_tipo")
            params["f_tipo"] = self.tipo
        sql = "" if not cond else " AND " + " AND ".join(cond)
        return sql, params

    def clausula_posicao(self, alias: str = "p") -> Tuple[str, dict]:
        """Condição sobre a posição do jogador (`alias` = tabela jogadores)."""
        if not self.posicao:
            return "", {}
        return f" AND {alias}.posicao = :f_posicao", {"f_posicao": self.posicao}


FILTROS_VAZIO = Filtros()


# ── Helpers de leitura para popular os seletores ─────────────────────────────

def _ler(query: str) -> pd.DataFrame:
    with get_engine().connect() as conn:
        return pd.read_sql(text(query), conn)


def anos_disponiveis() -> List[int]:
    """Anos com jogos registrados, do mais recente para o mais antigo."""
    df = _ler("SELECT DISTINCT EXTRACT(YEAR FROM data)::int AS ano FROM jogos ORDER BY ano DESC")
    return df["ano"].tolist()


def tipos_disponiveis() -> List[str]:
    """Tipos de jogo distintos (Amistoso, Festival, Campeonato...)."""
    df = _ler("SELECT DISTINCT tipo FROM jogos WHERE tipo IS NOT NULL ORDER BY tipo")
    return df["tipo"].tolist()


def posicoes_disponiveis() -> List[str]:
    """Posições distintas cadastradas nos jogadores."""
    df = _ler("SELECT DISTINCT posicao FROM jogadores WHERE posicao IS NOT NULL ORDER BY posicao")
    return df["posicao"].tolist()


def meses_disponiveis(ano: Optional[int] = None) -> List[int]:
    """Números dos meses com jogos (opcionalmente restritos a um ano)."""
    filtro = f"WHERE EXTRACT(YEAR FROM data) = {int(ano)}" if ano else ""
    df = _ler(
        f"SELECT DISTINCT EXTRACT(MONTH FROM data)::int AS mes FROM jogos {filtro} ORDER BY mes"
    )
    return df["mes"].tolist()
