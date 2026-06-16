"""Cadastro e edição de adversários. Área protegida."""
import streamlit as st

from src.auth.senha import exigir_senha
from src.servicos import cadastros

st.title("🛡️ Adversários")

if not exigir_senha():
    st.stop()

aba_novo, aba_editar = st.tabs(["➕ Novo adversário", "✏️ Editar / listar"])

with aba_novo:
    with st.form("novo_adversario", clear_on_submit=True):
        nome = st.text_input("Nome *")
        bairro = st.text_input("Bairro")
        if st.form_submit_button("Cadastrar adversário", type="primary"):
            try:
                cadastros.criar_adversario(nome=nome, bairro=bairro or None)
                st.success(f"Adversário '{nome.strip()}' cadastrado!")
            except ValueError as e:
                st.error(str(e))

with aba_editar:
    adversarios = cadastros.listar_adversarios()
    if not adversarios:
        st.info("Nenhum adversário cadastrado ainda.")
        st.stop()

    st.dataframe(
        [{"Nome": a.nome, "Bairro": a.bairro or ""} for a in adversarios],
        use_container_width=True,
        hide_index=True,
    )

    alvo = st.selectbox(
        "Editar adversário", adversarios, format_func=lambda a: a.nome, key="edit_adv"
    )
    with st.form("editar_adversario"):
        nome = st.text_input("Nome *", value=alvo.nome)
        bairro = st.text_input("Bairro", value=alvo.bairro or "")
        if st.form_submit_button("Salvar alterações", type="primary"):
            try:
                cadastros.editar_adversario(alvo.id, nome=nome, bairro=bairro or None)
                st.success("Adversário atualizado!")
                st.rerun()
            except ValueError as e:
                st.error(str(e))
