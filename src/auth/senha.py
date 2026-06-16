"""Gate de senha única do time para áreas de escrita (avaliar / registrar jogo).

A senha vem de TEAM_PASSWORD (.env) ou de st.secrets["TEAM_PASSWORD"].
O estado de liberação fica em st.session_state, válido por sessão do navegador.
"""
from __future__ import annotations

import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

_CHAVE_SESSAO = "_time_liberado"


def _senha_configurada() -> str | None:
    try:
        if "TEAM_PASSWORD" in st.secrets:
            return str(st.secrets["TEAM_PASSWORD"])
    except Exception:
        pass
    return os.getenv("TEAM_PASSWORD")


def exigir_senha() -> bool:
    """Renderiza o gate; retorna True somente quando a senha já foi validada.

    Use no topo de páginas protegidas::

        if not exigir_senha():
            st.stop()
    """
    if st.session_state.get(_CHAVE_SESSAO):
        return True

    esperada = _senha_configurada()
    if not esperada:
        st.error("TEAM_PASSWORD não configurada. Defina no .env ou em secrets.toml.")
        return False

    st.info("🔒 Área restrita ao time. Informe a senha para continuar.")
    senha = st.text_input("Senha do time", type="password")
    if st.button("Entrar"):
        if senha == esperada:
            st.session_state[_CHAVE_SESSAO] = True
            st.rerun()
        else:
            st.error("Senha incorreta.")
    return False
