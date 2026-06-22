"""Cadastro e edição de atletas. Área protegida."""
from __future__ import annotations

from datetime import date

import streamlit as st

from src.auth.senha import exigir_senha
from src.servicos import cadastros

st.title("👥 Atletas")

if not exigir_senha():
    st.stop()

_NASC_MIN = date(1940, 1, 1)


def _idade(nascimento: date | None) -> str:
    """Idade em anos a partir da data de nascimento (string vazia se ausente)."""
    if not nascimento:
        return ""
    hoje = date.today()
    anos = hoje.year - nascimento.year - (
        (hoje.month, hoje.day) < (nascimento.month, nascimento.day)
    )
    return str(anos)

aba_novo, aba_editar = st.tabs(["➕ Novo atleta", "✏️ Editar / listar"])

# ------------------------------- Novo --------------------------------
with aba_novo:
    with st.form("novo_atleta", clear_on_submit=True):
        nome = st.text_input("Nome *")
        c1, c2 = st.columns(2)
        apelido = c1.text_input("Apelido")
        posicao = c2.selectbox("Posição", [""] + cadastros.POSICOES)
        c3, c4 = st.columns(2)
        rg = c3.text_input("RG")
        celular = c4.text_input("Celular")
        nascimento = st.date_input(
            "Data de nascimento", value=None,
            min_value=_NASC_MIN, max_value=date.today(), format="DD/MM/YYYY",
        )
        if st.form_submit_button("Cadastrar atleta", type="primary"):
            try:
                cadastros.criar_atleta(
                    nome=nome,
                    apelido=apelido or None,
                    rg=rg or None,
                    celular=celular or None,
                    posicao=posicao or None,
                    data_nascimento=nascimento,
                )
                st.success(f"Atleta '{nome.strip()}' cadastrado!")
            except ValueError as e:
                st.error(str(e))

# ----------------------------- Editar --------------------------------
with aba_editar:
    atletas = cadastros.listar_atletas(apenas_ativos=False)
    if not atletas:
        st.info("Nenhum atleta cadastrado ainda.")
        st.stop()

    st.dataframe(
        [
            {
                "Nome": a.nome,
                "Apelido": a.apelido or "",
                "Posição": a.posicao or "",
                "Idade": _idade(a.data_nascimento),
                "Celular": a.celular or "",
                "Ativo": "Sim" if a.ativo else "Não",
            }
            for a in atletas
        ],
        use_container_width=True,
        hide_index=True,
    )

    alvo = st.selectbox(
        "Editar atleta", atletas, format_func=lambda a: a.nome, key="edit_atleta"
    )
    with st.form("editar_atleta"):
        nome = st.text_input("Nome *", value=alvo.nome)
        c1, c2 = st.columns(2)
        apelido = c1.text_input("Apelido", value=alvo.apelido or "")
        pos_idx = ([""] + cadastros.POSICOES).index(alvo.posicao or "")
        posicao = c2.selectbox("Posição", [""] + cadastros.POSICOES, index=pos_idx)
        c3, c4 = st.columns(2)
        rg = c3.text_input("RG", value=alvo.rg or "")
        celular = c4.text_input("Celular", value=alvo.celular or "")
        nascimento = st.date_input(
            "Data de nascimento", value=alvo.data_nascimento,
            min_value=_NASC_MIN, max_value=date.today(), format="DD/MM/YYYY",
        )
        ativo = st.checkbox("Ativo", value=alvo.ativo)
        if st.form_submit_button("Salvar alterações", type="primary"):
            try:
                cadastros.editar_atleta(
                    alvo.id,
                    nome=nome,
                    apelido=apelido or None,
                    rg=rg or None,
                    celular=celular or None,
                    posicao=posicao or None,
                    ativo=ativo,
                    data_nascimento=nascimento,
                )
                st.success("Atleta atualizado!")
                st.rerun()
            except ValueError as e:
                st.error(str(e))
