"""Seção de UI reutilizável para mesclar cadastros duplicados.

Usada pelas páginas de Campos e Adversários. Recebe as funções de serviço
(`sugerir` e `fundir`) e desenha os grupos de candidatos, deixando o usuário
escolher o registro correto (destino) e fundir os demais nele. UI apenas — toda
a regra vive em `src/servicos/organizacao.py`.
"""
from __future__ import annotations

from typing import Callable, List

import streamlit as st

from src.servicos.organizacao import ItemCadastro


def secao_mesclar(
    *,
    entidade: str,
    sugerir: Callable[[], List[List[ItemCadastro]]],
    fundir: Callable[[int, List[int]], int],
) -> None:
    st.caption(
        "Grupos de nomes parecidos (ignorando acento, caixa e espaços). Escolha o "
        "registro **correto** de cada grupo; os outros serão fundidos nele — os "
        "jogos são realocados e os duplicados apagados."
    )

    grupos = sugerir()
    if not grupos:
        st.success("Nenhum duplicado óbvio encontrado. 🎉")
        return

    for gi, grupo in enumerate(grupos):
        rotulos = {
            item.id: f"{item.nome}" + (f" · {item.detalhe}" if item.detalhe else "")
            for item in grupo
        }
        with st.container(border=True):
            st.markdown(f"**Grupo {gi + 1}** — {len(grupo)} registros parecidos")
            destino_id = st.radio(
                "Manter (destino):",
                options=[item.id for item in grupo],
                format_func=lambda i: rotulos[i],
                key=f"merge_{entidade}_{gi}",
            )
            origem_ids = [item.id for item in grupo if item.id != destino_id]
            if st.button(
                f"🧹 Fundir {len(origem_ids)} no destino",
                key=f"btn_merge_{entidade}_{gi}",
                type="primary",
            ):
                qtd = fundir(destino_id, origem_ids)
                st.success(f"{qtd} registro(s) fundido(s) em «{rotulos[destino_id]}».")
                st.rerun()
