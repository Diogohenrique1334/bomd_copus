"""Coleta de notas dos jogadores (substitui o Google Forms). Área protegida."""
from __future__ import annotations

import streamlit as st

from src.auth.senha import exigir_senha
from src.servicos import avaliacoes, cadastros, escalacao_jogo
from src.servicos.jogos import listar_jogos_resumo

st.title("⭐ Avaliar jogadores")

if not exigir_senha():
    st.stop()

jogos = listar_jogos_resumo(limite=2)
if not jogos:
    st.warning("Cadastre um jogo antes de avaliar (página **Registrar jogo**).")
    st.stop()

votante = st.text_input("Quem está votando?")
jogo = st.selectbox(
    "Jogo (apenas os 2 mais recentes)",
    jogos,
    format_func=lambda j: j.rotulo(),
)

# Avalia só quem esteve na escalação (inicial+final) do jogo; sem escalação salva,
# cai para todos os atletas ativos.
ativos = cadastros.listar_atletas(apenas_ativos=True)
escalados = escalacao_jogo.atletas_do_jogo(jogo.id)
if escalados:
    jogadores = [a for a in ativos if a.id in escalados]
    st.caption(f"Notas de 0 a 10 (passo 0,5). {len(jogadores)} atletas da escalação deste jogo.")
else:
    jogadores = ativos
    st.caption("Notas de 0 a 10 (passo 0,5). Sem escalação salva — listando todos os "
               "atletas ativos. Desmarque quem não jogou.")

with st.form("form_avaliacoes"):
    notas: dict[int, float | None] = {}
    for jogador in jogadores:
        c_nome, c_jogou, c_nota = st.columns([3, 1, 3])
        c_nome.markdown(f"**{jogador.nome}**")
        jogou = c_jogou.checkbox("Jogou", value=True, key=f"jogou_{jogador.id}")
        nota = c_nota.slider(
            "Nota",
            min_value=0.0,
            max_value=10.0,
            step=0.5,
            value=7.0,
            key=f"nota_{jogador.id}",
            label_visibility="collapsed",
            disabled=not jogou,
        )
        notas[jogador.id] = nota if jogou else None

    enviado = st.form_submit_button("Enviar avaliações", type="primary")

if enviado:
    try:
        qtd = avaliacoes.registrar_avaliacoes(
            jogo_id=jogo.id, votante=votante, notas=notas
        )
        st.success(f"{qtd} avaliações registradas. Valeu, {votante.strip()}! 👏")
    except ValueError as e:
        st.error(str(e))
