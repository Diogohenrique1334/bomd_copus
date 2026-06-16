# ⚽ BDC App

App do time de futebol **BDC**: coleta de avaliações dos jogadores e detalhes dos
gols, com dashboard interativo — substituindo o fluxo antigo de
**Google Forms → Google Sheets → Power BI** por um único app **Streamlit + ECharts**
com banco **Neon (Postgres)**.

## Funcionalidades

- **Dashboard** — resumo da temporada, ranking de notas, artilharia, assistências
  e evolução individual (ECharts).
- **Avaliar jogadores** — formulário de notas (5–10) por jogo; reenvio substitui o
  voto anterior do mesmo votante.
- **Registrar jogo** — cadastro da partida (com cor do uniforme) e de cada gol
  (autor, assistência, posição, forma, local, tempo). Adversário, campo e atletas
  precisam estar cadastrados.
- **Cadastros** — atletas (nome, apelido, RG, celular, posição), adversários
  (nome, bairro) e campos (nome, cidade), todos com edição.

As páginas de escrita são protegidas por uma **senha única do time**.

## Como rodar (Windows / Python 3.9)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Crie um arquivo `.env` na raiz:

```ini
DATABASE_URL = postgresql://<usuario>:<senha>@<host>.neon.tech/<db>?sslmode=require&channel_binding=require
TEAM_PASSWORD = sua_senha_do_time
```

Crie as tabelas e suba o app:

```powershell
.\.venv\Scripts\python.exe -m scripts.init_db
.\.venv\Scripts\streamlit.exe run app.py
```

Para carregar o histórico das planilhas Google (⚠️ reseta o schema antes):

```powershell
.\.venv\Scripts\python.exe -m scripts.migrar_2023
```

## Estrutura

```
app.py                 # entrypoint + navegação
paginas/               # Dashboard, Avaliar, Registrar jogo, Cadastros
src/
  db/                  # engine, models (ORM), repositorio
  servicos/            # cadastros, jogos, avaliacoes, stats
  auth/                # senha única do time
  graficos/            # wrappers ECharts
scripts/
  init_db.py           # cria as tabelas no Neon
  migrar_2023.py       # ETL das planilhas Google -> Neon
```

## Stack

Streamlit · streamlit-echarts · SQLAlchemy 2.0 · psycopg 3 · Neon (Postgres) · pandas
