"""ETL: migra o histórico das planilhas Google (2023+) para o Neon.

Popula, nesta ordem: atletas, adversários, campos, jogos + gols e avaliações.
RESETA o schema antes (drop_all + create_all) — use apenas em base sem dados
que você queira preservar.

Uso (a partir da raiz do projeto)::

    python -m scripts.migrar_2023

Regras de mapeamento:
- O "tipo do jogo" não existe na planilha de jogos; é inferido cruzando a data
  com a planilha de avaliações (tipo mais frequente naquela data).
- Cada avaliação é ligada ao jogo pela data. Datas sem jogo correspondente são
  ignoradas e reportadas ao final.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import date

import pandas as pd

from src.db import repositorio as repo
from src.db.engine import SessionLocal, get_engine
from src.db.models import Avaliacao, Base, Gol

URL_JOGOS = "https://docs.google.com/spreadsheets/d/1Mqwm22JAYZc_19yAF4afXVUdFe8_0pzybfbXwcd5ysA/export?format=csv"
URL_AVAL = "https://docs.google.com/spreadsheets/d/14Bsmpg944oKWdBK3Xojfh5n1KX9Ng7-XqWHAf3C8cxM/export?format=csv"

# Campos que identificam jogo em casa do BDC.
_CAMPOS_CASA = {"arena dimas"}

# Valores-sentinela das planilhas que equivalem a "vazio".
VAZIOS = {"", "-", "sem gol", "sem assistência", "sem assistencia", "nan", "não jogou", "nao jogou"}

GOLS_POR_JOGO = 10          # blocos de gol na planilha
COLS_POR_GOL = 6            # autor, posição, forma, local, tempo, assistência
PRIMEIRA_COL_GOL = 6        # índice da coluna "1º -Gol"


def _texto(valor) -> str | None:
    """Normaliza célula: retorna None para vazios/sentinelas."""
    if pd.isna(valor):
        return None
    s = str(valor).strip()
    return None if s.lower() in VAZIOS else s


def _data(valor) -> date | None:
    dt = pd.to_datetime(str(valor).strip(), format="%d/%m/%Y", errors="coerce")
    return None if pd.isna(dt) else dt.date()


def _inteiro(valor) -> int:
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return 0


def _nota(valor) -> tuple[bool, float | None]:
    """Interpreta uma célula de nota. Retorna (jogou, nota)."""
    if pd.isna(valor):
        return (False, None)
    s = str(valor).strip()
    if s.lower() in {"não jogou", "nao jogou", ""}:
        return (False, None)
    try:
        return (True, float(s.replace(",", ".")))
    except ValueError:
        return (False, None)


def main() -> None:
    engine = get_engine()
    print("Resetando schema...")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    df_jogos = pd.read_csv(URL_JOGOS, dtype=str)
    df_aval = pd.read_csv(URL_AVAL, dtype=str)
    print(f"Planilhas baixadas: jogos={df_jogos.shape}, avaliacoes={df_aval.shape}")

    # Um mesmo votante pode ter reenviado o formulário para o mesmo jogo
    # (mesma data). Mantemos apenas o envio mais recente, pelo carimbo.
    col_carimbo, col_votante, col_data = df_aval.columns[:3]
    df_aval = df_aval.copy()
    df_aval["_carimbo"] = pd.to_datetime(
        df_aval[col_carimbo], format="%d/%m/%Y %H:%M:%S", errors="coerce"
    )
    antes = len(df_aval)
    df_aval = df_aval.sort_values("_carimbo").drop_duplicates(
        subset=[col_votante, col_data], keep="last"
    )
    if antes != len(df_aval):
        print(f"Votos duplicados removidos (votante+data): {antes - len(df_aval)}")

    # tipo do jogo por data (moda) a partir das avaliações
    tipos_por_data: dict[date, Counter] = defaultdict(Counter)
    for _, row in df_aval.iterrows():
        d = _data(row.iloc[2])
        tipo = _texto(row.iloc[3])
        if d and tipo:
            tipos_por_data[d][tipo] += 1
    tipo_da_data = {d: c.most_common(1)[0][0] for d, c in tipos_por_data.items()}

    # nomes dos jogadores avaliados (cabeçalhos "Performance no Geral [Nome]")
    nomes_avaliados: dict[int, str] = {}
    for idx in range(4, len(df_aval.columns)):
        m = re.search(r"\[(.+?)\]", df_aval.columns[idx])
        if m:
            nomes_avaliados[idx] = m.group(1).strip()

    with SessionLocal() as session:
        cache_jogador: dict[str, int] = {}
        cache_adversario: dict[str, int] = {}
        cache_campo: dict[str, int] = {}

        def jogador_id(nome: str | None) -> int | None:
            if not nome:
                return None
            chave = nome.strip()
            if chave not in cache_jogador:
                existente = repo.obter_jogador_por_nome(session, chave)
                obj = existente or repo.criar_jogador(session, nome=chave)
                cache_jogador[chave] = obj.id
            return cache_jogador[chave]

        # garante todos os jogadores avaliados, mesmo sem gols
        for nome in nomes_avaliados.values():
            jogador_id(nome)

        data_para_jogo: dict[date, int] = {}
        datas_duplicadas: list[date] = []

        # ----------------------------- Jogos + Gols -----------------------------
        for _, row in df_jogos.iterrows():
            d = _data(row.iloc[1])
            if not d:
                continue

            nome_adv = _texto(row.iloc[2])
            if nome_adv and nome_adv not in cache_adversario:
                cache_adversario[nome_adv] = repo.criar_adversario(session, nome=nome_adv).id

            nome_campo = _texto(row.iloc[3])
            if nome_campo and nome_campo not in cache_campo:
                cache_campo[nome_campo] = repo.criar_campo(session, nome=nome_campo).id

            _casa = (nome_campo.strip().lower() in _CAMPOS_CASA) if nome_campo else None
            jogo = repo.criar_jogo(
                session,
                data_jogo=d,
                tipo=tipo_da_data.get(d),
                adversario_id=cache_adversario.get(nome_adv) if nome_adv else None,
                campo_id=cache_campo.get(nome_campo) if nome_campo else None,
                cor_uniforme=None,
                gols_bdc=_inteiro(row.iloc[5]),
                gols_adversario=_inteiro(row.iloc[4]),
                casa=_casa,
            )

            if d in data_para_jogo:
                datas_duplicadas.append(d)
            else:
                data_para_jogo[d] = jogo.id

            for k in range(GOLS_POR_JOGO):
                base = PRIMEIRA_COL_GOL + k * COLS_POR_GOL
                if base + COLS_POR_GOL > len(row):
                    break
                autor = _texto(row.iloc[base])
                if not autor:
                    continue
                repo.adicionar_gol(
                    session,
                    Gol(
                        jogo_id=jogo.id,
                        jogador_id=jogador_id(autor),
                        assistente_id=jogador_id(_texto(row.iloc[base + 5])),
                        ordem=k + 1,
                        posicao=_texto(row.iloc[base + 1]),
                        forma=_texto(row.iloc[base + 2]),
                        local=_texto(row.iloc[base + 3]),
                        tempo=_texto(row.iloc[base + 4]),
                    ),
                )

        session.flush()

        # ----------------------------- Avaliações ------------------------------
        aval_gravadas = 0
        votos_sem_jogo = 0
        for _, row in df_aval.iterrows():
            d = _data(row.iloc[2])
            votante = _texto(row.iloc[1])
            if not d or not votante:
                continue
            jogo_id = data_para_jogo.get(d)
            if jogo_id is None:
                votos_sem_jogo += 1
                continue
            for idx, nome in nomes_avaliados.items():
                jogou, nota = _nota(row.iloc[idx])
                if not jogou and nota is None and pd.isna(row.iloc[idx]):
                    continue  # jogador fora daquela rodada de votação
                repo.adicionar_avaliacao(
                    session,
                    Avaliacao(
                        jogo_id=jogo_id,
                        jogador_id=jogador_id(nome),
                        votante=votante,
                        nota=nota,
                        jogou=jogou,
                    ),
                )
                aval_gravadas += 1

        session.commit()

    print("\n=== Resumo da migração ===")
    print(f"Atletas:      {len(cache_jogador)}")
    print(f"Adversários:  {len(cache_adversario)}")
    print(f"Campos:       {len(cache_campo)}")
    print(f"Jogos:        {len(data_para_jogo) + len(datas_duplicadas)}")
    print(f"Avaliações:   {aval_gravadas}")
    if datas_duplicadas:
        print(f"⚠️  Datas com >1 jogo (avaliações ligadas ao 1º): {sorted(set(datas_duplicadas))}")
    if votos_sem_jogo:
        print(f"⚠️  Linhas de avaliação sem jogo correspondente (ignoradas): {votos_sem_jogo}")


if __name__ == "__main__":
    main()
