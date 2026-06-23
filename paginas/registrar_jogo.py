"""Cadastro, edição e exclusão de jogo + gols. Área protegida.

Adversário, campo e atletas precisam estar previamente cadastrados.
A aba "Editar" altera as informações da partida e também os gols; permite excluir.
"""
from __future__ import annotations

from datetime import date

import streamlit as st

from src.auth.senha import exigir_senha
from src.servicos import cadastros
from src.servicos.jogos import (
    CORES_UNIFORME,
    GolInput,
    editar_jogo,
    excluir_jogo,
    listar_gols_do_jogo,
    listar_jogos_resumo,
    obter_jogo_detalhe,
    registrar_jogo,
)

FORMAS = ["Chute", "Perna Esquerda", "Perna Direita", "Cabeça", "Falta", "Pênalti", "Outro"]
LOCAIS = ["Dentro da área", "Fora da área", "Pênalti", "Olímpico"]
TEMPOS = ["1º Tempo", "2º Tempo"]
TIPOS = ["Amistoso", "Festival", "Campeonato"]

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
    st.warning("Antes de registrar um jogo, cadastre: " + ", ".join(faltando) + ".")
    st.stop()

# Autores/assistentes de gol incluem as entradas auxiliares (ex.: "Gol Contra"),
# que existem só para registrar gols — não aparecem em nada de atletas.
auxiliares = cadastros.listar_auxiliares()
opcoes_gol = atletas + auxiliares
nomes_atletas = {a.id: (a.apelido or a.nome) for a in opcoes_gol}
ids_gol = [a.id for a in opcoes_gol]

adv_nome = {a.id: a.nome for a in adversarios}
campo_label = {c.id: c.nome + (f" ({c.cidade})" if c.cidade else "") for c in campos}
adv_ids = [a.id for a in adversarios]
campo_ids = [c.id for c in campos]


def _idx(lista, valor, default=0):
    return lista.index(valor) if valor in lista else default


aba_novo, aba_editar = st.tabs(["➕ Novo jogo", "✏️ Editar / excluir jogo"])


# ------------------------------- Novo --------------------------------
with aba_novo:
    # Fora do form: o nº de gols precisa ser reativo p/ os blocos aparecerem
    # antes do submit (dentro de um form, mudar o número não re-renderiza).
    st.subheader("Placar")
    pc1, pc2 = st.columns(2)
    gols_bdc = pc1.number_input("Gols BDC", min_value=0, max_value=30, value=0,
                                step=1, key="novo_gbdc")
    gols_adv = pc2.number_input("Gols adversário", min_value=0, max_value=30, value=0,
                                step=1, key="novo_gadv")

    with st.form("form_jogo"):
        st.subheader("Dados da partida")
        c1, c2, c3 = st.columns(3)
        data_jogo = c1.date_input("Data do jogo", value=date.today(), format="DD/MM/YYYY")
        tipo = c2.selectbox("Tipo", TIPOS)
        cor = c3.selectbox("Cor do uniforme", CORES_UNIFORME)

        c4, c5, c6 = st.columns(3)
        adversario = c4.selectbox("Adversário", adversarios, format_func=lambda a: a.nome)
        campo = c5.selectbox(
            "Campo", campos,
            format_func=lambda c: c.nome + (f" ({c.cidade})" if c.cidade else ""),
        )
        casa = c6.checkbox("Jogo em casa?", value=False)

        st.subheader("Gols do BDC")
        st.caption("Um bloco por gol marcado pelo time (ajuste o 'Gols BDC' acima).")
        gols_inputs: list[GolInput] = []
        for i in range(int(gols_bdc)):
            st.markdown(f"**Gol {i + 1}**")
            g1, g2, g3 = st.columns(3)
            autor_id = g1.selectbox(
                "Autor", ids_gol, format_func=lambda i: nomes_atletas[i], key=f"novo_autor_{i}"
            )
            assist_id = g2.selectbox(
                "Assistência", [0] + ids_gol,
                format_func=lambda i: "— sem assistência —" if i == 0 else nomes_atletas[i],
                key=f"novo_assist_{i}",
            )
            posicao = g3.selectbox("Posição", cadastros.POSICOES, key=f"novo_pos_{i}")
            g4, g5, g6 = st.columns(3)
            forma = g4.selectbox("Forma", FORMAS, key=f"novo_forma_{i}")
            local = g5.selectbox("Local", LOCAIS, key=f"novo_local_{i}")
            tempo = g6.selectbox("Tempo", TEMPOS, key=f"novo_tempo_{i}")
            gols_inputs.append(GolInput(
                autor_id=autor_id, assistente_id=assist_id or None,
                posicao=posicao, forma=forma, local=local, tempo=tempo,
            ))

        enviado = st.form_submit_button("Salvar jogo", type="primary")

    if enviado:
        try:
            jogo_id = registrar_jogo(
                data_jogo=data_jogo, tipo=tipo, adversario_id=adversario.id,
                campo_id=campo.id, cor_uniforme=cor, gols_bdc=int(gols_bdc),
                gols_adversario=int(gols_adv), gols=gols_inputs, casa=casa,
            )
            st.success(f"Jogo #{jogo_id} salvo com {len(gols_inputs)} gol(s) registrado(s).")
        except Exception as e:  # noqa: BLE001 - exibe erro ao usuário
            st.error(f"Erro ao salvar: {e}")


# ------------------------------ Editar -------------------------------
with aba_editar:
    jogos = listar_jogos_resumo()
    if not jogos:
        st.info("Nenhum jogo cadastrado ainda.")
        st.stop()

    alvo = st.selectbox(
        "Jogo a editar", jogos, format_func=lambda j: j.rotulo(), key="edit_jogo_sel"
    )
    det = obter_jogo_detalhe(alvo.id)
    gols_existentes = listar_gols_do_jogo(alvo.id)

    # Guard de contexto: ao trocar de jogo, semeia o estado dos widgets.
    ctx = f"editjogo:{alvo.id}"
    if st.session_state.get("edit_ctx") != ctx:
        st.session_state["edit_ctx"] = ctx
        for k in [k for k in st.session_state if k.startswith("ej_")]:
            del st.session_state[k]
        st.session_state["ej_data"] = det.data
        st.session_state["ej_tipo"] = det.tipo if det.tipo in TIPOS else TIPOS[0]
        st.session_state["ej_cor"] = (
            det.cor_uniforme if det.cor_uniforme in CORES_UNIFORME else CORES_UNIFORME[0]
        )
        st.session_state["ej_adv"] = det.adversario_id if det.adversario_id in adv_ids else adv_ids[0]
        st.session_state["ej_campo"] = det.campo_id if det.campo_id in campo_ids else campo_ids[0]
        st.session_state["ej_casa"] = bool(det.casa)
        st.session_state["ej_gols_adv"] = int(det.gols_adversario)
        st.session_state["ej_ngols"] = len(gols_existentes) or int(det.gols_bdc)
        for i, g in enumerate(gols_existentes):
            st.session_state[f"ej_autor_{i}"] = g.autor_id if g.autor_id in ids_gol else ids_gol[0]
            st.session_state[f"ej_assist_{i}"] = g.assistente_id if g.assistente_id in ids_gol else 0
            st.session_state[f"ej_pos_{i}"] = g.posicao if g.posicao in cadastros.POSICOES else cadastros.POSICOES[0]
            st.session_state[f"ej_forma_{i}"] = g.forma if g.forma in FORMAS else FORMAS[0]
            st.session_state[f"ej_local_{i}"] = g.local if g.local in LOCAIS else LOCAIS[0]
            st.session_state[f"ej_tempo_{i}"] = g.tempo if g.tempo in TEMPOS else TEMPOS[0]

    st.subheader("Placar")
    pe1, pe2 = st.columns(2)
    e_gols_bdc = pe1.number_input("Gols BDC (nº de gols a detalhar)", min_value=0,
                                  max_value=30, step=1, key="ej_ngols")
    e_gols_adv = pe2.number_input("Gols adversário", min_value=0, max_value=30,
                                  step=1, key="ej_gols_adv")

    st.subheader("Dados da partida")
    e1, e2, e3 = st.columns(3)
    e_data = e1.date_input("Data do jogo", format="DD/MM/YYYY",
                           min_value=date(2015, 1, 1), max_value=date(2100, 12, 31),
                           key="ej_data")
    e_tipo = e2.selectbox("Tipo", TIPOS, key="ej_tipo")
    e_cor = e3.selectbox("Cor do uniforme", CORES_UNIFORME, key="ej_cor")
    e4, e5, e6 = st.columns(3)
    e_adv = e4.selectbox("Adversário", adv_ids, format_func=lambda i: adv_nome[i], key="ej_adv")
    e_campo = e5.selectbox("Campo", campo_ids, format_func=lambda i: campo_label[i], key="ej_campo")
    e_casa = e6.checkbox("Jogo em casa?", key="ej_casa")

    st.subheader("Gols do BDC")
    st.caption("Edite os gols (ajuste o 'Gols BDC' acima p/ mudar a quantidade).")
    e_gols: list[GolInput] = []
    for i in range(int(e_gols_bdc)):
        st.markdown(f"**Gol {i + 1}**")
        eg1, eg2, eg3 = st.columns(3)
        autor_id = eg1.selectbox(
            "Autor", ids_gol, format_func=lambda i: nomes_atletas[i], key=f"ej_autor_{i}"
        )
        assist_id = eg2.selectbox(
            "Assistência", [0] + ids_gol,
            format_func=lambda i: "— sem assistência —" if i == 0 else nomes_atletas[i],
            key=f"ej_assist_{i}",
        )
        posicao = eg3.selectbox("Posição", cadastros.POSICOES, key=f"ej_pos_{i}")
        eg4, eg5, eg6 = st.columns(3)
        forma = eg4.selectbox("Forma", FORMAS, key=f"ej_forma_{i}")
        local = eg5.selectbox("Local", LOCAIS, key=f"ej_local_{i}")
        tempo = eg6.selectbox("Tempo", TEMPOS, key=f"ej_tempo_{i}")
        e_gols.append(GolInput(
            autor_id=autor_id, assistente_id=assist_id or None,
            posicao=posicao, forma=forma, local=local, tempo=tempo,
        ))

    if st.button("💾 Salvar alterações", type="primary", key="ej_salvar"):
        try:
            editar_jogo(
                alvo.id, data_jogo=e_data, tipo=e_tipo, adversario_id=e_adv,
                campo_id=e_campo, cor_uniforme=e_cor, casa=e_casa,
                gols_bdc=int(e_gols_bdc), gols_adversario=int(e_gols_adv), gols=e_gols,
            )
            st.success("Jogo atualizado!")
            st.session_state.pop("edit_ctx", None)  # recarrega do banco
            st.rerun()
        except ValueError as e:
            st.error(str(e))

    # ── Excluir (zona de perigo) ──────────────────────────────────────────────
    st.divider()
    st.markdown("##### ⚠️ Excluir jogo")
    st.caption("Remove o jogo e, em cascata, seus gols, avaliações e escalações. "
               "Não dá pra desfazer.")
    confirma = st.checkbox("Confirmo a exclusão deste jogo.", key="ej_confirma_del")
    if st.button("🗑️ Excluir jogo", disabled=not confirma, key="ej_excluir"):
        excluir_jogo(alvo.id)
        st.session_state.pop("edit_ctx", None)
        st.session_state.pop("ej_confirma_del", None)
        st.success(f"Jogo excluído: {alvo.rotulo()}.")
        st.rerun()
