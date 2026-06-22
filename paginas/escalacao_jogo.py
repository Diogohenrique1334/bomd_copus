"""Registrar a escalação de um jogo pelo campinho. Área protegida.

O usuário escolhe o esquema tático e atribui um atleta a cada posição (slot +
dropdown); o campo serve de preview ao vivo. Cada jogo guarda dois momentos:
os **11 iniciais** e os **11 que terminaram** jogando.

Distinta da "Escalação Ideal" do dashboard (sugestão heurística, só leitura):
aqui é entrada de dados (persiste na tabela `escalacoes`).
"""
from __future__ import annotations

import streamlit as st

from src.auth.senha import exigir_senha
from src.graficos import echarts_bdc as g
from src.graficos import tema
from src.servicos import cadastros, escalacao_jogo
from src.servicos.escalacao import FORMACOES
from src.servicos.jogos import listar_jogos_resumo

st.title("📋 Escalação do jogo")

if not exigir_senha():
    st.stop()

tema.inject_css()

jogos = listar_jogos_resumo()
if not jogos:
    st.warning("Cadastre um jogo antes de escalar (página **Registrar jogo**).")
    st.stop()

atletas = cadastros.listar_atletas(apenas_ativos=True)
if not atletas:
    st.warning("Cadastre atletas antes de escalar (página **Atletas**).")
    st.stop()

apelido_por_id = {a.id: (a.apelido or a.nome) for a in atletas}
opcoes_atleta = [0] + [a.id for a in atletas]  # 0 = slot vazio


def _fmt_atleta(atleta_id: int) -> str:
    return "— escolher —" if atleta_id == 0 else apelido_por_id.get(atleta_id, "?")


# ── Cabeçalho: jogo · momento · esquema ──────────────────────────────────────
jogo = st.selectbox("Jogo", jogos, format_func=lambda j: j.rotulo(), key="esc_jogo")

momento_label = st.segmented_control(
    "Momento",
    list(escalacao_jogo.MOMENTOS.values()),
    default=escalacao_jogo.MOMENTOS["inicial"],
    key="esc_momento",
)
# rótulo exibido -> chave técnica (inicial/final)
momento = next(
    chave for chave, label in escalacao_jogo.MOMENTOS.items()
    if label == momento_label
)

# ── Guard de contexto: ao trocar de jogo/momento, recarrega o que está salvo ──
ctx = f"{jogo.id}:{momento}"
if st.session_state.get("esc_ctx") != ctx:
    st.session_state["esc_ctx"] = ctx
    salvo = escalacao_jogo.obter(jogo.id, momento)
    formacao_inicial = (salvo or {}).get("formacao") or list(FORMACOES)[0]
    seed = (salvo or {}).get("atribuicoes", {})

    st.session_state["esc_formacao"] = formacao_inicial
    # limpa slots antigos e semeia os do esquema carregado
    for chave in [k for k in st.session_state if k.startswith("esc_slot_")]:
        del st.session_state[chave]
    for slot_key, _ in escalacao_jogo.slots_da_formacao(formacao_inicial):
        st.session_state[f"esc_slot_{slot_key}"] = seed.get(slot_key, 0)

formacao = st.selectbox("Esquema tático", list(FORMACOES), key="esc_formacao")
slots = escalacao_jogo.slots_da_formacao(formacao)

# ── Slots agrupados por linha (ataque em cima) ───────────────────────────────
tema.secao(f"Escalação — {momento_label}")

linhas: dict[int, list] = {}
for slot_key, s in slots:
    linhas.setdefault(s["y"], []).append((slot_key, s))

atribuicoes: dict[str, int | None] = {}
for y in sorted(linhas, reverse=True):  # y alto = ataque, primeiro
    fila = sorted(linhas[y], key=lambda item: item[1]["x"])
    cols = st.columns(len(fila))
    for col, (slot_key, s) in zip(cols, fila):
        widget_key = f"esc_slot_{slot_key}"
        if widget_key not in st.session_state:
            st.session_state[widget_key] = 0
        sel = col.selectbox(
            escalacao_jogo.rotulo_posicao(slot_key),
            opcoes_atleta,
            format_func=_fmt_atleta,
            key=widget_key,
        )
        atribuicoes[slot_key] = sel or None

# ── Validação de duplicados ──────────────────────────────────────────────────
escolhidos = [aid for aid in atribuicoes.values() if aid]
duplicados = {aid for aid in escolhidos if escolhidos.count(aid) > 1}
preenchidos = len(escolhidos)

st.divider()

# ── Preview no campo + salvar ────────────────────────────────────────────────
col_campo, col_acao = st.columns([3, 2])

with col_campo:
    pontos = [
        {"nome": apelido_por_id[sel], "x": s["x"], "y": s["y"]}
        for slot_key, s in slots
        if (sel := atribuicoes.get(slot_key))
    ]
    g.campo_escalacao(pontos, key="esc_campo_preview")

with col_acao:
    tema.kpis([
        ("Escalados", f"{preenchidos}/11"),
        ("Duplicados", len(duplicados)),
    ], destaque=0 if preenchidos == 11 and not duplicados else -1)

    if duplicados:
        nomes = ", ".join(apelido_por_id[aid] for aid in duplicados)
        st.warning(f"Atleta em mais de uma posição: **{nomes}**. Ajuste antes de salvar.")

    if st.button("💾 Salvar escalação", type="primary", disabled=bool(duplicados)):
        qtd = escalacao_jogo.salvar(jogo.id, momento, formacao, atribuicoes)
        st.success(
            f"Escalação salva — {qtd} jogadores ({momento_label}) "
            f"em {jogo.rotulo()}."
        )
