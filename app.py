"""BDC App — entrypoint Streamlit.

Executar a partir da raiz do projeto::

    streamlit run app.py

Define a navegação multipágina; cada página vive em ``paginas/``.
"""
import streamlit as st

st.set_page_config(page_title="BDC App", page_icon="⚽", layout="wide")

dashboard = st.Page("paginas/dashboard.py", title="Dashboard", icon="📊", default=True)
avaliar = st.Page("paginas/avaliar.py", title="Avaliar jogadores", icon="⭐")
registrar = st.Page("paginas/registrar_jogo.py", title="Registrar jogo", icon="⚽")
atletas = st.Page("paginas/cadastro_atletas.py", title="Atletas", icon="👥")
adversarios = st.Page("paginas/cadastro_adversarios.py", title="Adversários", icon="🛡️")
campos = st.Page("paginas/cadastro_campos.py", title="Campos", icon="🏟️")

st.navigation(
    {
        "Visão geral": [dashboard],
        "Coleta de dados": [avaliar, registrar],
        "Cadastros": [atletas, adversarios, campos],
    }
).run()
