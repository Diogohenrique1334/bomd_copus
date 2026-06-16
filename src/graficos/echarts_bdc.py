"""Adaptador de gráficos do BDC sobre a biblioteca Baltazar.

A montagem das opções ECharts vive no Baltazar
(`baltazar.graficos.graficos_streamlit.graficos`). Aqui ficam apenas:
- a paleta do BDC (dourado/preto + cores de resultado);
- wrappers finos que chamam o Baltazar já passando a cor dourada e o `key`,
  e que **renderizam** (não retornam dict).

Assim a página chama, por exemplo, ``g.barras_verticais(df, "x", "y", key="...")``
sem precisar envolver em ``st_echarts``.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

from baltazar.graficos.graficos_streamlit import graficos as bz

# ── Paleta BDC ───────────────────────────────────────────────────────────────
COR_BDC = "#D4AF37"        # dourado
COR_ESCURO = "#1a1a1a"     # preto
COR_VITORIA = "#4CAF50"
COR_EMPATE = "#9E9E9E"
COR_DERROTA = "#F44336"
COR_TEXTO = "#333333"
COR_EIXO = "#c8c8d0"       # cinza claro p/ eixos e legenda no tema dark

_CORES_RESULTADO = {
    "Vitória": COR_VITORIA,
    "Empate": COR_EMPATE,
    "Derrota": COR_DERROTA,
}

# Cores das séries em barras agrupadas (ex.: V/E/D por casa/fora)
_CORES_AGRUPADAS = [COR_BDC, COR_ESCURO, COR_EMPATE, COR_VITORIA]


# ── Wrappers (delegam ao Baltazar com a identidade do BDC) ───────────────────

def barras_horizontais(df, col_categoria, col_valor, cor: str = COR_BDC,
                       key: Optional[str] = None, tamanho: str = "300px"):
    return bz.barras_horizontais(df, col_categoria, col_valor, cor=cor,
                                 key=key, tamanho=tamanho, cor_eixos=COR_EIXO)


def barras_verticais(df, col_categoria, col_valor, cor: str = COR_BDC,
                     rotular: bool = True, key: Optional[str] = None,
                     tamanho: str = "300px"):
    return bz.barras_verticais(df, col_categoria, col_valor, cor=cor,
                               rotular=rotular, key=key, tamanho=tamanho,
                               cor_eixos=COR_EIXO)


def barras_coloridas_resultado(df, col_x, col_valor, col_resultado,
                               key: Optional[str] = None, tamanho: str = "280px"):
    """Barras verticais coloridas por resultado (V=verde, E=cinza, D=vermelho)."""
    return bz.barras_coloridas(
        df, col_categoria=col_x, col_valor=col_valor, col_cor=col_resultado,
        cores_por_categoria=_CORES_RESULTADO, cor_padrao=COR_BDC,
        horizontal=False, key=key, tamanho=tamanho, cor_eixos=COR_EIXO,
    )


def barras_resultado_h(df, col_resultado, col_valor, min_eixo=None, max_eixo=None,
                       key: Optional[str] = None, tamanho: str = "200px"):
    """Barras horizontais coloridas por resultado (eixo Y = resultado)."""
    return bz.barras_coloridas(
        df, col_categoria=col_resultado, col_valor=col_valor,
        cores_por_categoria=_CORES_RESULTADO, cor_padrao=COR_BDC,
        horizontal=True, min_eixo=min_eixo, max_eixo=max_eixo,
        key=key, tamanho=tamanho, cor_eixos=COR_EIXO,
    )


def barras_agrupadas(df, col_x, series: dict, key: Optional[str] = None,
                     tamanho: str = "220px"):
    return bz.barras_agrupadas(df, col_x, series, cores=_CORES_AGRUPADAS,
                               key=key, tamanho=tamanho,
                               cor_eixos=COR_EIXO, cor_legenda=COR_EIXO)


def linha_temporal(df, col_x, col_y, nome: str = "", cor: str = COR_BDC,
                   min_y=5, max_y=10, key: Optional[str] = None,
                   tamanho: str = "250px"):
    return bz.linha_temporal(df, col_x, col_y, nome=nome, cor=cor,
                             min_y=min_y, max_y=max_y, key=key, tamanho=tamanho,
                             cor_eixos=COR_EIXO)


def linha_com_rotulos(df, col_x, col_y, sufixo: str = "", cor: str = COR_BDC,
                      min_y=None, max_y=None, key: Optional[str] = None,
                      tamanho: str = "250px"):
    return bz.linha_com_rotulos(df, col_x, col_y, sufixo=sufixo, cor=cor,
                                min_y=min_y, max_y=max_y, key=key, tamanho=tamanho,
                                cor_eixos=COR_EIXO)


def status_jogos(df, key: Optional[str] = None, tamanho: str = "260px"):
    """Barras dos jogos: altura = saldo de gols, cor por resultado, rótulo adv+data.

    Saldo = gols BDC − gols adversário (vitória sobe, derrota desce, empate = 0).
    """
    df = df.copy()
    df["_saldo"] = df["gols_bdc"].astype(int) - df["gols_adversario"].astype(int)
    df["_saldo_lbl"] = df["_saldo"].apply(lambda s: f"+{s}" if s > 0 else str(s))
    df["_rotulo"] = [
        f"{str(row['adversario'])[:8]}\n{pd.to_datetime(row['data']).strftime('%d/%m')}"
        for _, row in df.iterrows()
    ]
    return bz.barras_status(
        df, col_valor="_saldo", col_cor="resultado", col_rotulo_x="_rotulo",
        cores_por_categoria=_CORES_RESULTADO, cor_padrao=COR_BDC,
        altura_minima=None, col_rotulo_valor="_saldo_lbl",
        key=key, tamanho=tamanho, cor_eixos=COR_EIXO, cor_legenda=COR_EIXO,
    )


def donut(labels, values, cores=None, key: Optional[str] = None,
          tamanho: str = "240px"):
    cores = cores or [COR_BDC, COR_ESCURO, COR_EMPATE, COR_VITORIA, COR_DERROTA]
    return bz.donut(labels, values, cores=cores, key=key, tamanho=tamanho,
                    cor_legenda=COR_EIXO)


def gauge_aproveitamento(pct, key: Optional[str] = None, tamanho: str = "220px"):
    """Gauge semicircular de aproveitamento; cor muda conforme a faixa."""
    cor_faixa = COR_VITORIA if pct >= 60 else (COR_BDC if pct >= 40 else COR_DERROTA)
    return bz.gauge_progresso(pct, cor=cor_faixa, key=key, tamanho=tamanho)


def campo_escalacao(jogadores, key: Optional[str] = None, tamanho: str = "560px"):
    """Campo de futebol do BDC: gramado escuro + marcadores dourados."""
    return bz.campo_futebol(jogadores, cor_campo="#14532d", cor_marcador=COR_BDC,
                            cor_texto="#ffffff", key=key, tamanho=tamanho)
