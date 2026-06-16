"""Dashboard BDC — 3 seções: Jogos · Avaliações · Gols.

Renderização condicional (st.segmented_control) em vez de st.tabs: os gráficos
ECharts (canvas) renderizam em branco quando criados dentro de uma aba inativa
(display:none → largura 0). Renderizando só a seção selecionada, todo gráfico
nasce num container visível.

Os gráficos vêm da biblioteca Baltazar via o adaptador `echarts_bdc` (paleta
dourada do BDC). Cada seção tem sua própria barra de filtros (ano/mês/tipo e, em
Avaliações/Gols, posição); o estado vira um `Filtros` injetado nas funções de stats.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd
import streamlit as st

from src.graficos import echarts_bdc as g
from src.graficos import tema
from src.servicos import escalacao
from src.servicos import filtros as flt
from src.servicos import stats
from src.servicos.filtros import Filtros

tema.inject_css()
tema.hero("BDC", "Painel de Análise")


# ═══════════════════════════════════════════════════════════════════════════════
# Barra de filtros (reutilizável por seção)
# ═══════════════════════════════════════════════════════════════════════════════
def barra_filtros(prefixo: str, com_posicao: bool = False) -> Filtros:
    """Renderiza os seletores e devolve o `Filtros` correspondente."""
    anos = flt.anos_disponiveis()
    tipos = flt.tipos_disponiveis()

    with st.expander("🔎 Filtros", expanded=False):
        cols = st.columns(4 if com_posicao else 3)

        ano_label = cols[0].selectbox("Ano", ["Todos"] + [str(a) for a in anos],
                                      key=f"{prefixo}_ano")
        ano_val: Optional[int] = None if ano_label == "Todos" else int(ano_label)

        meses_nums = flt.meses_disponiveis(ano_val)
        mes_opcoes = ["Todos"] + [flt.MESES_PT[m] for m in meses_nums]
        mes_label = cols[1].selectbox("Mês", mes_opcoes, key=f"{prefixo}_mes")
        mes_val: Optional[int] = None
        if mes_label != "Todos":
            mes_val = next(m for m, nome in flt.MESES_PT.items() if nome == mes_label)

        tipo_label = cols[2].selectbox("Tipo de jogo", ["Todos"] + tipos,
                                       key=f"{prefixo}_tipo")
        tipo_val = None if tipo_label == "Todos" else tipo_label

        pos_val = None
        if com_posicao:
            pos_label = cols[3].selectbox("Posição", ["Todas"] + flt.posicoes_disponiveis(),
                                          key=f"{prefixo}_pos")
            pos_val = None if pos_label == "Todas" else pos_label

    f = Filtros(ano=ano_val, mes=mes_val, tipo=tipo_val, posicao=pos_val)

    # Resumo dos filtros ativos
    ativos = []
    if ano_val:  ativos.append(f"Ano: **{ano_val}**")
    if mes_val:  ativos.append(f"Mês: **{flt.MESES_PT[mes_val]}**")
    if tipo_val: ativos.append(f"Tipo: **{tipo_val}**")
    if pos_val:  ativos.append(f"Posição: **{pos_val}**")
    if ativos:
        st.caption("Filtros ativos — " + " · ".join(ativos))

    return f


def _aviso_sem_dados() -> None:
    st.warning("Nenhum jogo para os filtros selecionados. Ajuste o ano/mês/tipo.")


# ═══════════════════════════════════════════════════════════════════════════════
# SEÇÃO — JOGOS
# ═══════════════════════════════════════════════════════════════════════════════
def render_jogos() -> None:
    f = barra_filtros("j", com_posicao=False)
    res = stats.resumo_completo(f)
    if not res or not res.get("jogos"):
        _aviso_sem_dados()
        return

    # ── KPIs ──────────────────────────────────────────────────────────────────
    tema.secao("Resumo da Temporada")
    tema.kpis([
        ("Jogos",       int(res["jogos"])),
        ("Vitórias",    int(res["vitorias"])),
        ("Empates",     int(res["empates"])),
        ("Derrotas",    int(res["derrotas"])),
        ("Gols Pró",    int(res["gols_pro"])),
        ("Mediana",     res["mediana_gols_pro"]),
        ("Desvio",      res["desv_gols_pro"]),
        ("Gols Contra", int(res["gols_contra"])),
        ("Aproveit.",   f"{res['aproveitamento_pct']}%"),
    ], destaque=8)

    st.divider()

    # ── Gauge + Casa VS Fora + Visão Geral ────────────────────────────────────
    col_g1, col_g2, col_g3 = st.columns([1, 1, 2])

    with col_g1:
        tema.card_titulo("% Aproveitamento dos Pontos")
        g.gauge_aproveitamento(float(res["aproveitamento_pct"]), key="j_gauge")

    with col_g2:
        tema.card_titulo("Aproveitamento Casa × Fora")
        df_cf = stats.aproveitamento_casa_fora(f)
        if df_cf.empty:
            st.caption("Sem dados de casa/fora para o filtro.")
        else:
            for _, row in df_cf.iterrows():
                st.metric(row["local"], f"{row['aproveitamento_pct']}%",
                          help=f"{int(row['jogos'])} jogos")

    with col_g3:
        tema.card_titulo("Visão Geral dos Jogos")
        df_vg = stats.visao_geral_casa_fora(f)
        if df_vg.empty:
            g.donut(
                ["Vitórias", "Empates", "Derrotas"],
                [int(res["vitorias"]), int(res["empates"]), int(res["derrotas"])],
                [g.COR_VITORIA, g.COR_EMPATE, g.COR_DERROTA],
                key="j_donut_geral",
            )
        else:
            pivot = (
                df_vg.pivot(index="resultado", columns="local", values="jogos")
                .fillna(0).reset_index()
            )
            serie_cols = {c: c for c in pivot.columns if c != "resultado"}
            g.barras_agrupadas(pivot, "resultado", serie_cols, key="j_barras_casa_fora")

    st.divider()

    # ── Artilharia + Média jogadores por campo ────────────────────────────────
    col_a, col_b = st.columns(2)

    with col_a:
        tema.card_titulo("Artilharia (Destaques)")
        df_art = stats.artilharia(f)
        if not df_art.empty:
            g.barras_verticais(df_art.head(15), "jogador", "gols", key="j_artilharia")
        else:
            st.caption("Sem gols registrados para o filtro.")

    with col_b:
        tema.card_titulo("Média de Jogadores Disponíveis por Campo")
        df_mj = stats.media_jogadores_por_campo(f)
        if not df_mj.empty:
            g.barras_verticais(df_mj, "campo", "media_jogadores", key="j_media_jogadores")
        else:
            st.caption("Sem dados de presença por campo para o filtro.")

    st.divider()

    # ── Status dos últimos 20 jogos ───────────────────────────────────────────
    tema.card_titulo("Status dos Últimos 20 Jogos")
    df_ult = stats.ultimos_jogos(20, f)
    if not df_ult.empty:
        g.status_jogos(df_ult, key="j_status")

    st.divider()

    # ── % Aproveitamento por mês ──────────────────────────────────────────────
    tema.card_titulo("% de Aproveitamento por Mês")
    df_mes = stats.aproveitamento_por_mes(f)
    if not df_mes.empty:
        g.linha_com_rotulos(df_mes, "mes", "aproveitamento_pct",
                            sufixo="%", min_y=0, max_y=100, key="j_aproveit_mes")


# ═══════════════════════════════════════════════════════════════════════════════
# SEÇÃO — AVALIAÇÕES
# ═══════════════════════════════════════════════════════════════════════════════
def render_avaliacoes() -> None:
    f = barra_filtros("a", com_posicao=True)
    res = stats.resumo_completo(f)
    if not res or not res.get("jogos"):
        _aviso_sem_dados()
        return
    res_a = stats.resumo_avaliacoes(f)

    # ── KPIs ──────────────────────────────────────────────────────────────────
    tema.secao("Resumo das Avaliações")
    tema.kpis([
        ("Jogos",          int(res["jogos"])),
        ("Vitórias",       int(res["vitorias"])),
        ("Empates",        int(res["empates"])),
        ("Derrotas",       int(res["derrotas"])),
        ("Votos / jogo",   res_a.get("media_votos_jogo", "—")),
        ("Desvio votos",   res_a.get("desv_votos_jogo", "—")),
        ("Nota média",     res_a.get("media_nota_atletas", "—")),
    ], destaque=6)

    st.divider()

    # ── Nota por resultado | por tipo | por posição ───────────────────────────
    b1, b2, b3 = st.columns(3)

    with b1:
        tema.card_titulo("Nota Média por Resultado")
        df_res = stats.nota_media_por_resultado(f)
        if not df_res.empty:
            g.barras_resultado_h(df_res, "resultado", "nota_media",
                                 min_eixo=5, max_eixo=8, key="a_nota_resultado")

    with b2:
        tema.card_titulo("Nota Média por Tipo de Jogo")
        df_tipo = stats.nota_media_por_tipo(f)
        if not df_tipo.empty:
            g.barras_horizontais(df_tipo, "tipo", "nota_media", key="a_nota_tipo",
                                 tamanho="200px")

    with b3:
        tema.card_titulo("Nota Média por Posição")
        df_pos = stats.nota_media_por_posicao(f)
        if not df_pos.empty:
            g.barras_verticais(df_pos, "posicao", "nota_media", key="a_nota_posicao",
                               tamanho="200px")
        else:
            df_pos = None
            st.caption("Sem atletas com posição para o filtro.")

    st.divider()

    # ── Desvio por posição | Nota por campo ───────────────────────────────────
    c1, c2 = st.columns(2)

    with c1:
        tema.card_titulo("Desvio Padrão por Posição", "consistência das notas")
        if df_pos is not None and not df_pos.empty:
            g.barras_verticais(df_pos, "posicao", "desvio", cor=g.COR_ESCURO,
                               key="a_desvio_posicao", tamanho="220px")
        else:
            st.caption("Sem atletas com posição para o filtro.")

    with c2:
        tema.card_titulo("Nota Média por Campo")
        df_campo_aval = stats.nota_media_por_campo(f)
        if not df_campo_aval.empty:
            g.barras_verticais(df_campo_aval, "campo", "nota_media",
                               key="a_nota_campo", tamanho="220px")
        else:
            st.caption("Sem notas por campo para o filtro.")

    st.divider()

    # ── Nota por partida (barras coloridas) ───────────────────────────────────
    tema.card_titulo("Nota Média por Partida")
    df_part = stats.nota_media_por_partida(f)
    if not df_part.empty:
        df_part["label"] = (
            df_part["adversario"].str[:8] + " " + df_part["data"].astype(str).str[5:]
        )
        g.barras_coloridas_resultado(df_part, "label", "nota_media", "resultado",
                                     key="a_nota_partida")

    st.divider()

    # ── Ranking de notas + Nota por mês ───────────────────────────────────────
    d1, d2 = st.columns([2, 1])
    df_rank = stats.ranking_notas(f)

    with d1:
        tema.card_titulo("Nota Média por Jogador")
        if not df_rank.empty:
            g.barras_verticais(df_rank, "jogador", "nota_media", key="a_ranking",
                               tamanho="280px")
        else:
            st.caption("Sem avaliações para o filtro.")

    with d2:
        tema.card_titulo("Nota Média por Mês")
        df_nmes = stats.nota_media_por_mes(f)
        if not df_nmes.empty:
            g.linha_com_rotulos(df_nmes, "mes", "nota_media", min_y=5, max_y=8,
                                key="a_nota_mes", tamanho="280px")

    st.divider()

    # ── Melhor em campo (vezes como melhor nota do jogo) ──────────────────────
    tema.card_titulo("Melhor em Campo", "vezes como maior nota do jogo")
    df_melhor = stats.ranking_melhor_em_campo(f)
    if not df_melhor.empty:
        g.barras_horizontais(df_melhor.head(15), "jogador", "vezes",
                             key="a_melhor_campo", tamanho="320px")
    else:
        st.caption("Sem dados para o filtro.")

    st.divider()

    # ── Evolução individual ───────────────────────────────────────────────────
    tema.card_titulo("Evolução Individual")
    if not df_rank.empty:
        jogador_sel = st.selectbox("Jogador", df_rank["jogador"].tolist(),
                                   key="sel_jogador_aval")
        df_evo = stats.evolucao_jogador(jogador_sel, f)
        if not df_evo.empty:
            g.linha_temporal(df_evo, "data", "nota_media", jogador_sel, key="a_evolucao")


# ═══════════════════════════════════════════════════════════════════════════════
# SEÇÃO — GOLS
# ═══════════════════════════════════════════════════════════════════════════════
def render_gols() -> None:
    f = barra_filtros("g", com_posicao=True)
    res = stats.resumo_completo(f)
    if not res or not res.get("jogos"):
        _aviso_sem_dados()
        return
    res_g = stats.resumo_gols(f)

    # ── KPIs ──────────────────────────────────────────────────────────────────
    tema.secao("Resumo de Gols")
    tema.kpis([
        ("Jogos",        int(res["jogos"])),
        ("Atletas",      int(res_g.get("atletas", 0) or 0)),
        ("Gols",         int(res_g.get("total_gols", 0) or 0)),
        ("Méd. gols",    res_g.get("media_gols", "—")),
        ("Desvio",       res_g.get("desv_gols", "—")),
        ("Assistências", int(res_g.get("total_assists", 0) or 0)),
        ("Méd. assist.", res_g.get("media_assists", "—")),
    ], destaque=2)

    st.divider()

    # ── Donut assist | Casa/Fora | Por tipo | Por resultado ───────────────────
    e1, e2, e3, e4 = st.columns(4)

    with e1:
        tema.card_titulo("Status do Gol")
        df_assist = stats.status_assistencias(f)
        if not df_assist.empty:
            g.donut(df_assist["status"].tolist(), df_assist["qtd"].tolist(),
                    [g.COR_ESCURO, g.COR_BDC], key="g_status_assist")

    with e2:
        tema.card_titulo("Média Gols Casa × Fora")
        df_gcf = stats.media_gols_casa_fora(f)
        if df_gcf.empty:
            st.caption("Sem dados casa/fora.")
        else:
            g.barras_horizontais(df_gcf, "local", "media_gols", key="g_gols_casa_fora",
                                 tamanho="240px")

    with e3:
        tema.card_titulo("Média Gols por Tipo")
        df_gtipo = stats.media_gols_por_tipo(f)
        if not df_gtipo.empty:
            g.barras_horizontais(df_gtipo, "tipo", "media_gols", key="g_gols_tipo",
                                 tamanho="240px")

    with e4:
        tema.card_titulo("Média Gols por Resultado")
        df_gres = stats.media_gols_por_resultado(f)
        if not df_gres.empty:
            g.barras_resultado_h(df_gres, "resultado", "media_gols",
                                 key="g_gols_resultado", tamanho="240px")

    st.divider()

    # ── Participações por posição + detalhado ─────────────────────────────────
    f1, f2 = st.columns(2)
    df_pp = stats.participacoes_por_posicao(f)

    with f1:
        tema.card_titulo("Participações em Gols por Posição")
        if not df_pp.empty:
            g.barras_verticais(df_pp, "posicao", "total", key="g_participacoes",
                               tamanho="260px")
        else:
            st.caption("Sem participações para o filtro.")

    with f2:
        tema.card_titulo("Gols × Assistências por Posição")
        if not df_pp.empty:
            g.barras_agrupadas(df_pp, "posicao",
                               {"Gols feitos": "gols", "Assistências": "assists"},
                               key="g_gols_assists_pos", tamanho="260px")

    st.divider()

    # ── Artilharia completa ───────────────────────────────────────────────────
    tema.card_titulo("Gols por Atleta")
    df_art_g = stats.artilharia(f)
    if not df_art_g.empty:
        g.barras_verticais(df_art_g, "jogador", "gols", key="g_artilharia",
                           tamanho="280px")
    else:
        st.caption("Sem gols para o filtro.")

    st.divider()

    # ── Gols/Assists por tempo | Forma | Local ────────────────────────────────
    h1, h2, h3, h4 = st.columns(4)

    with h1:
        tema.card_titulo("Gols por Tempo")
        df_gt = stats.gols_por_tempo(f)
        if not df_gt.empty:
            g.donut(df_gt["tempo"].tolist(), df_gt["gols"].tolist(),
                    key="g_gols_tempo", tamanho="220px")

    with h2:
        tema.card_titulo("Assists por Tempo")
        df_at = stats.assists_por_tempo(f)
        if not df_at.empty:
            g.donut(df_at["tempo"].tolist(), df_at["assists"].tolist(),
                    key="g_assists_tempo", tamanho="220px")

    with h3:
        tema.card_titulo("Forma do Gol")
        df_fg = stats.forma_gol(f)
        if not df_fg.empty:
            g.barras_horizontais(df_fg, "forma", "gols", key="g_forma_gol",
                                 tamanho="220px")

    with h4:
        tema.card_titulo("Local do Gol")
        df_lg = stats.local_gol(f)
        if not df_lg.empty:
            g.barras_horizontais(df_lg, "local", "gols", key="g_local_gol",
                                 tamanho="220px")

    st.divider()

    # ── Total de gols por mês ─────────────────────────────────────────────────
    tema.card_titulo("Total de Gols por Mês")
    df_gmes = stats.media_gols_por_mes(f)
    if not df_gmes.empty:
        g.linha_com_rotulos(df_gmes, "mes", "total_gols", min_y=0, key="g_gols_mes")


# ═══════════════════════════════════════════════════════════════════════════════
# SEÇÃO — ESCALAÇÃO (forma recente, sem filtros)
# ═══════════════════════════════════════════════════════════════════════════════
def render_escalacao() -> None:
    tema.secao("Escalação Ideal")

    f = barra_filtros("esc", com_posicao=False)
    df_notas = stats.notas_por_jogo_jogador(f)
    if df_notas.empty:
        st.info("Sem avaliações para os filtros selecionados.")
        return

    # ── Controles ─────────────────────────────────────────────────────────────
    c1, c2 = st.columns(2)
    formacao_nome = c1.selectbox("Formação", list(escalacao.FORMACOES), key="esc_form")
    criterio = c2.selectbox("Critério de seleção", list(escalacao.CRITERIOS), key="esc_crit")

    df_rank = escalacao.ranquear(df_notas, criterio)
    todos = df_rank["jogador"].tolist()
    disponiveis = st.multiselect(
        "Atletas disponíveis (remova quem não vai jogar)",
        options=todos, default=todos, key="esc_disp",
    )
    df_uso = df_rank[df_rank["jogador"].isin(disponiveis)]
    if df_uso.empty:
        st.warning("Selecione ao menos alguns atletas disponíveis.")
        return

    titulares, reservas = escalacao.montar_escalacao(
        df_uso, escalacao.FORMACOES[formacao_nome]
    )

    st.caption(f"**{criterio}** · esquema **{formacao_nome}** · "
               "⚠️ = atleta escalado fora da posição")

    improv = sum(1 for t in titulares if t["improvisado"] and t["jogador"])
    tema.kpis([
        ("Atletas no XI", sum(1 for t in titulares if t["jogador"])),
        ("Improvisados", improv),
        ("No banco", len(reservas)),
    ], destaque=0)

    st.divider()

    col_campo, col_lista = st.columns([3, 2])

    with col_campo:
        jogadores_campo = [
            {"nome": (t["jogador"] or t["slot"]), "nota": t["exib"],
             "x": t["x"], "y": t["y"]}
            for t in titulares
        ]
        g.campo_escalacao(jogadores_campo, key="esc_campo")

    with col_lista:
        tema.card_titulo("Time titular")
        df_tit = pd.DataFrame([
            {"Pos": t["slot"], "Jogador": t["jogador"] or "—",
             "Indicador": t["exib"], "Jogos": t["jogos"],
             "": "⚠️" if t["improvisado"] and t["jogador"] else ""}
            for t in titulares
        ])
        st.dataframe(df_tit, hide_index=True, use_container_width=True)

        if reservas:
            tema.card_titulo("Banco")
            df_res = pd.DataFrame(reservas).rename(columns={
                "jogador": "Jogador", "posicao": "Posição",
                "exib": "Indicador", "jogos": "Jogos",
            })
            st.dataframe(df_res.head(10), hide_index=True, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Seletor de seção (renderização condicional — só a selecionada entra no DOM)
# ═══════════════════════════════════════════════════════════════════════════════
if not stats.resumo_completo().get("jogos"):
    st.info("Ainda não há jogos registrados.")
else:
    secao = st.segmented_control(
        "Seção",
        ["⚽ Jogos", "⭐ Avaliações", "🥅 Gols", "📋 Escalação"],
        default="⚽ Jogos",
        label_visibility="collapsed",
    )

    if secao == "⭐ Avaliações":
        render_avaliacoes()
    elif secao == "🥅 Gols":
        render_gols()
    elif secao == "📋 Escalação":
        render_escalacao()
    else:  # default / "⚽ Jogos"
        render_jogos()
