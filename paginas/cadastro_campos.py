"""Cadastro e edição de campos (locais de jogo). Área protegida."""
import streamlit as st

from src.auth.senha import exigir_senha
from src.servicos import cadastros
from src.servicos import organizacao
from paginas._mesclar import secao_mesclar

st.title("🏟️ Campos")

if not exigir_senha():
    st.stop()

aba_novo, aba_editar, aba_mesclar = st.tabs(
    ["➕ Novo campo", "✏️ Editar / listar", "🧹 Mesclar duplicados"]
)

with aba_novo:
    with st.form("novo_campo", clear_on_submit=True):
        nome = st.text_input("Nome do campo *")
        cidade = st.text_input("Cidade")
        c1, c2 = st.columns(2)
        nota_q = c1.number_input("Nota qualidade (0–10)", min_value=0.0,
                                 max_value=10.0, step=0.5, value=None)
        nota_d = c2.number_input("Nota distância (0–10)", min_value=0.0,
                                 max_value=10.0, step=0.5, value=None,
                                 help="10 = pertinho; 0 = longe demais.")
        if st.form_submit_button("Cadastrar campo", type="primary"):
            try:
                cadastros.criar_campo(nome=nome, cidade=cidade or None,
                                      nota_qualidade=nota_q, nota_distancia=nota_d)
                st.success(f"Campo '{nome.strip()}' cadastrado!")
            except ValueError as e:
                st.error(str(e))

with aba_editar:
    campos = cadastros.listar_campos()
    if not campos:
        st.info("Nenhum campo cadastrado ainda.")
        st.stop()

    st.dataframe(
        [
            {
                "Nome": c.nome,
                "Cidade": c.cidade or "",
                "Qualidade": c.nota_qualidade if c.nota_qualidade is not None else "",
                "Distância": c.nota_distancia if c.nota_distancia is not None else "",
            }
            for c in campos
        ],
        use_container_width=True,
        hide_index=True,
    )

    alvo = st.selectbox(
        "Editar campo", campos, format_func=lambda c: c.nome, key="edit_campo"
    )
    with st.form("editar_campo"):
        nome = st.text_input("Nome do campo *", value=alvo.nome)
        cidade = st.text_input("Cidade", value=alvo.cidade or "")
        c1, c2 = st.columns(2)
        nota_q = c1.number_input("Nota qualidade (0–10)", min_value=0.0,
                                 max_value=10.0, step=0.5, value=alvo.nota_qualidade)
        nota_d = c2.number_input("Nota distância (0–10)", min_value=0.0,
                                 max_value=10.0, step=0.5, value=alvo.nota_distancia,
                                 help="10 = pertinho; 0 = longe demais.")
        if st.form_submit_button("Salvar alterações", type="primary"):
            try:
                cadastros.editar_campo(alvo.id, nome=nome, cidade=cidade or None,
                                       nota_qualidade=nota_q, nota_distancia=nota_d)
                st.success("Campo atualizado!")
                st.rerun()
            except ValueError as e:
                st.error(str(e))

with aba_mesclar:
    secao_mesclar(
        entidade="campos",
        sugerir=organizacao.sugerir_duplicados_campos,
        fundir=organizacao.fundir_campos,
    )
