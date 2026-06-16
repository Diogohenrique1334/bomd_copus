"""Cadastro e edição de campos (locais de jogo). Área protegida."""
import streamlit as st

from src.auth.senha import exigir_senha
from src.servicos import cadastros

st.title("🏟️ Campos")

if not exigir_senha():
    st.stop()

aba_novo, aba_editar = st.tabs(["➕ Novo campo", "✏️ Editar / listar"])

with aba_novo:
    with st.form("novo_campo", clear_on_submit=True):
        nome = st.text_input("Nome do campo *")
        cidade = st.text_input("Cidade")
        if st.form_submit_button("Cadastrar campo", type="primary"):
            try:
                cadastros.criar_campo(nome=nome, cidade=cidade or None)
                st.success(f"Campo '{nome.strip()}' cadastrado!")
            except ValueError as e:
                st.error(str(e))

with aba_editar:
    campos = cadastros.listar_campos()
    if not campos:
        st.info("Nenhum campo cadastrado ainda.")
        st.stop()

    st.dataframe(
        [{"Nome": c.nome, "Cidade": c.cidade or ""} for c in campos],
        use_container_width=True,
        hide_index=True,
    )

    alvo = st.selectbox(
        "Editar campo", campos, format_func=lambda c: c.nome, key="edit_campo"
    )
    with st.form("editar_campo"):
        nome = st.text_input("Nome do campo *", value=alvo.nome)
        cidade = st.text_input("Cidade", value=alvo.cidade or "")
        if st.form_submit_button("Salvar alterações", type="primary"):
            try:
                cadastros.editar_campo(alvo.id, nome=nome, cidade=cidade or None)
                st.success("Campo atualizado!")
                st.rerun()
            except ValueError as e:
                st.error(str(e))
