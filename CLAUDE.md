# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## O que é

**BDC App** — aplicativo Streamlit do time de futebol BDC. Reúne em um só lugar a
**coleta de dados** (notas dos jogadores e detalhes dos gols, substituindo um
Google Forms) e o **dashboard** (ECharts, substituindo um relatório Power BI). Os
dados são persistidos no **Neon** (Postgres serverless).

## Comandos

```bash
# Ambiente (Python 3.9)
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt   # Windows/PowerShell

# Criar/atualizar as tabelas no Neon (idempotente)
python -m scripts.init_db

# Migrar o histórico das planilhas Google para o Neon (RESETA o schema antes!)
python -m scripts.migrar_2023

# Rodar o app (sempre a partir da raiz)
streamlit run app.py
```

Não há suíte de testes nem linter configurados ainda. Para um sanity check rápido
de imports após mudanças: `python -c "from src.servicos import stats, avaliacoes, jogos"`.

## Configuração / segredos

- `.env` na raiz (não versionado) define `DATABASE_URL` (string do Neon) e
  `TEAM_PASSWORD` (senha única que libera as páginas de escrita).
- `engine.py` reescreve `postgresql://` → `postgresql+psycopg://` para usar o
  driver **psycopg v3**, necessário pelo `channel_binding=require` do Neon.
- Em deploy no Streamlit Cloud, as mesmas chaves vão em `.streamlit/secrets.toml`
  (a auth lê de `st.secrets` com fallback para variável de ambiente).

## Arquitetura

Camadas explícitas — **nunca colapsar responsabilidades**; respeitar a direção das
dependências (páginas → serviços → repositório → models):

- `app.py` — entrypoint; define a navegação com `st.navigation`/`st.Page`
  (seções: Visão geral, Coleta de dados, Cadastros).
- `paginas/` — uma página Streamlit por arquivo (UI apenas). Páginas de escrita
  chamam `exigir_senha()` no topo e `st.stop()` se não liberado.
- `src/db/` — `engine.py` (sessão/engine singleton), `models.py` (ORM),
  `repositorio.py` (CRUD puro, **sem** commit nem regra de negócio).
- `src/servicos/` — regras de negócio e transações. Abrem `SessionLocal()`,
  orquestram o repositório e dão `commit`. `cadastros.py` (atletas/adversários/
  campos, com edição), `jogos.py`, `avaliacoes.py`. `stats.py` é o único que lê
  via SQL direto (somente leitura) e devolve `DataFrame` para o dashboard.
- `scripts/` — `init_db.py` (cria tabelas) e `migrar_2023.py` (ETL das planilhas).
- `src/auth/senha.py` — gate de senha única do time, via `st.session_state`.
- `src/graficos/echarts_bdc.py` — funções que recebem `DataFrame` já agregado e
  devolvem o dict de opção do ECharts (sem tocar no banco).

## Modelo de dados (formato longo/normalizado)

Decisão central: **não** replicar o layout "wide" das planilhas. Cada nota e cada
gol é uma linha própria, então adicionar um jogador novo não altera o schema e as
agregações do dashboard viram `GROUP BY`. Adversário e campo são **entidades
cadastradas** (FK), não texto livre: ao registrar um jogo eles precisam já existir.

- `jogadores` (nome único; nome, apelido, rg, celular, posição, ativo)
- `adversarios` (nome único, bairro)
- `campos` (nome + cidade; único por nome+cidade)
- `jogos` (data, tipo, adversario_id, campo_id, cor_uniforme, gols_bdc, gols_adversario)
- `avaliacoes` (jogo, jogador, votante, nota 5–10, jogou) — única em
  (jogo, jogador, votante); reenvio de um votante substitui o voto anterior
- `gols` (jogo, autor, assistente opcional, ordem, posição, forma, local, tempo)

## Convenções

- Português (pt-BR) em nomes de domínio, docstrings e UI; `snake_case`.
- Origem dos dados: planilhas Google de avaliações (wide, saída de Forms) e de
  controle de jogos. O histórico 2023+ **já foi migrado** via `scripts.migrar_2023`
  (o "tipo do jogo" é inferido cruzando a data com a planilha de avaliações; votos
  duplicados do mesmo votante/jogo são deduplicados pelo carimbo).
- Type hints nos `models.py` usam `Optional`/`List` do `typing`, **não** `X | None`:
  o SQLAlchemy resolve anotações em runtime e o ambiente é Python 3.9.
