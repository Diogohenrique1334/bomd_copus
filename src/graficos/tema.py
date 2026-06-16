"""Tema visual do dashboard BDC (dourado/preto).

Mesma linguagem dos cards do portfólio (fundo escuro, cards com borda, headings
com barra lateral, KPI boxes, hover com elevação), adaptada à identidade do time:
dourado #D4AF37 sobre preto. Mantém UI separada dos gráficos: aqui só CSS +
helpers de markup; os dicts de ECharts continuam em `echarts_bdc.py`.
"""
from __future__ import annotations

from typing import List, Tuple

import streamlit as st

COR_BDC = "#D4AF37"
COR_BDC_CLARO = "#E8CC6A"

_CSS = """
<style>
/* ===== BDC DASHBOARD ===== */
.block-container { max-width: 1280px; padding-top: 1.6rem; }

/* Título principal */
.bdc-hero {
    display: flex; align-items: center; gap: 14px;
    border-bottom: 2px solid rgba(212,175,55,0.25);
    padding: 2px 4px 14px 4px; margin-bottom: 8px;
    overflow: visible;
}
.bdc-hero .bola { font-size: 2.1rem; line-height: 1; }
.bdc-hero .txt { font-size: 1.9rem; font-weight: 800; color: #f0f0f0;
                 line-height: 1.2; white-space: nowrap; overflow: visible;
                 padding-left: 2px; }
.bdc-hero .txt span { color: #D4AF37; }

/* Heading de seção (barra lateral dourada) */
.bdc-sec {
    font-size: 1.15rem; font-weight: 700; color: #f0f0f0;
    padding-left: 12px; border-left: 4px solid #D4AF37;
    margin: 6px 0 14px; line-height: 1.3;
}

/* Linha de KPIs */
.bdc-kpi-row {
    display: grid; gap: 12px; margin: 4px 0 8px;
    grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
}
.bdc-kpi {
    background: #15151f; border: 1px solid #2a2a3e; border-radius: 12px;
    padding: 16px 12px; text-align: center; transition: all 0.2s ease;
}
.bdc-kpi:hover {
    border-color: #D4AF37; transform: translateY(-3px);
    box-shadow: 0 10px 26px rgba(212,175,55,0.12);
}
.bdc-kpi .val { font-size: 1.7rem; font-weight: 800; color: #D4AF37; line-height: 1; }
.bdc-kpi .lbl { color: #8b8b9e; font-size: 0.74rem; margin-top: 6px;
                font-weight: 600; text-transform: uppercase; letter-spacing: 0.3px; }
.bdc-kpi.destaque .val { color: #4CAF50; }

/* Título de cada gráfico */
.bdc-card-title {
    font-size: 0.92rem; font-weight: 700; color: #d8d8e0;
    margin: 2px 0 2px;
}
.bdc-card-sub { color: #6b6b7e; font-size: 0.76rem; margin-bottom: 4px; }

/* Barra de filtros */
[data-testid="stExpander"] {
    border: 1px solid #2a2a3e; border-radius: 12px; background: #15151f;
}

/* Segmented control mais destacado */
[data-testid="stSegmentedControl"] { margin-bottom: 6px; }

footer { visibility: hidden; }
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def hero(titulo: str = "BDC", subtitulo: str = "Painel de Análise") -> None:
    st.markdown(
        f'<div class="bdc-hero"><span class="bola">⚽</span>'
        f'<span class="txt"><span>{titulo}</span> · {subtitulo}</span></div>',
        unsafe_allow_html=True,
    )


def secao(texto: str) -> None:
    """Heading de seção com barra lateral dourada."""
    st.markdown(f'<div class="bdc-sec">{texto}</div>', unsafe_allow_html=True)


def card_titulo(titulo: str, sub: str = "") -> None:
    """Título de um gráfico (e subtítulo opcional)."""
    html = f'<div class="bdc-card-title">{titulo}</div>'
    if sub:
        html += f'<div class="bdc-card-sub">{sub}</div>'
    st.markdown(html, unsafe_allow_html=True)


def kpis(itens: List[Tuple[str, object]], destaque: int = -1) -> None:
    """Linha de KPIs estilizados.

    ``itens`` = lista de (label, valor). ``destaque`` = índice a pintar de verde
    (ex.: aproveitamento). Use -1 para nenhum.
    """
    blocos = []
    for i, (lbl, val) in enumerate(itens):
        classe = "bdc-kpi destaque" if i == destaque else "bdc-kpi"
        blocos.append(
            f'<div class="{classe}"><div class="val">{val}</div>'
            f'<div class="lbl">{lbl}</div></div>'
        )
    st.markdown(f'<div class="bdc-kpi-row">{"".join(blocos)}</div>',
                unsafe_allow_html=True)
