"""Cadastro de jogo + gols (substitui a planilha de controle). Área protegida.

Adversário, campo e atletas precisam estar previamente cadastrados.
"""
from __future__ import annotations

from datetime import date

import streamlit as st

from src.auth.senha import exigir_senha
from src.servicos import cadastros
from src.servicos.jogos import CORES_UNIFORME, GolInput, registrar_jogo

FORMAS = ["Chute", "Perna Esquerda", "Perda Direita", "Cabeça", "Falta", "Pênalti", "Outro"]
LOCAIS = ["Dentro da área", "Fora da área", "Pênalti", "Olímpico"]
TEMPOS = ["1º Tempo", "2º Tempo"]

st.title("⚽ Registrar jogo")

if not exigir_senha():
    st.stop()

adversarios = cadastros.listar_adversarios()
campos = cadastros.listar_campos()
atletas = cadastros.listar_atletas(apenas_ativos=True)

faltando = []
if not adversarios:
    faltando.append("**Adversários**")
if not campos:
    faltando.append("**Campos**")
if not atletas:
    faltando.append("**Atletas**")
if faltando:
    st.warning(
        "Antes de registrar um jogo, cadastre: " + ", ".join(faltando) + "."
    )
    st.stop()

atleta_por_id = {a.id: a for a in atletas}
nomes_atletas = {a.id: (a.apelido or a.nome) for a in atletas}

with st.form("form_jogo"):
    st.subheader("Dados da partida")
    c1, c2, c3 = st.columns(3)
    data_jogo = c1.date_input("Data do jogo", value=date.today(), format="DD/MM/YYYY")
    tipo = c2.selectbox("Tipo", ["Amistoso", "Festival", "Campeonato"])
    cor = c3.selectbox("Cor do uniforme", CORES_UNIFORME)

    c4, c5, c6 = st.columns(3)
    adversario = c4.selectbox("Adversário", adversarios, format_func=lambda a: a.nome)
    campo = c5.selectbox(
        "Campo",
        campos,
        format_func=lambda c: f"{c.nome}" + (f" ({c.cidade})" if c.cidade else ""),
    )
    casa = c6.checkbox("Jogo em casa?", value=False)

    c7, c8 = st.columns(2)
    gols_bdc = c7.number_input("Gols BDC", min_value=0, max_value=30, value=0, step=1)
    gols_adv = c8.number_input("Gols adversário", min_value=0, max_value=30, value=0, step=1)

    st.subheader("Gols do BDC")
    st.caption("Um bloco por gol marcado pelo time.")
    qtd_blocos = int(gols_bdc)

    gols_inputs: list[GolInput] = []
    for i in range(qtd_blocos):
        st.markdown(f"**Gol {i + 1}**")
        g1, g2, g3 = st.columns(3)
        autor_id = g1.selectbox(
            "Autor", atletas, format_func=lambda a: nomes_atletas[a.id], key=f"autor_{i}"
        ).id
        assist = g2.selectbox(
            "Assistência",
            [None] + atletas,
            format_func=lambda a: "— sem assistência —" if a is None else nomes_atletas[a.id],
            key=f"assist_{i}",
        )
        posicao = g3.selectbox("Posição", cadastros.POSICOES, key=f"pos_{i}")
        g4, g5, g6 = st.columns(3)
        forma = g4.selectbox("Forma", FORMAS, key=f"forma_{i}")
        local = g5.selectbox("Local", LOCAIS, key=f"local_{i}")
        tempo = g6.selectbox("Tempo", TEMPOS, key=f"tempo_{i}")
        gols_inputs.append(
            GolInput(
                autor_id=autor_id,
                assistente_id=assist.id if assist else None,
                posicao=posicao,
                forma=forma,
                local=local,
                tempo=tempo,
            )
        )

    enviado = st.form_submit_button("Salvar jogo", type="primary")

if enviado:
    try:
        jogo_id = registrar_jogo(
            data_jogo=data_jogo,
            tipo=tipo,
            adversario_id=adversario.id,
            campo_id=campo.id,
            cor_uniforme=cor,
            gols_bdc=int(gols_bdc),
            gols_adversario=int(gols_adv),
            gols=gols_inputs,
            casa=casa,
        )
        st.success(f"Jogo #{jogo_id} salvo com {len(gols_inputs)} gol(s) registrado(s).")
    except Exception as e:  # noqa: BLE001 - exibe erro ao usuário
        st.error(f"Erro ao salvar: {e}")
