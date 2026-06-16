"""Migração additive dos dados 2021–2022 (Resultados + Artilharia).

Não reseta o schema — apenas insere registros novos.
Execução:
    python -m scripts.migrar_2021_2022
"""
from __future__ import annotations

import io
import unicodedata
from datetime import date

import pandas as pd
from sqlalchemy import text

from src.db.engine import get_engine

# ── Dados extraídos das planilhas ────────────────────────────────────────────

_CSV_RESULTADOS = """\
DATA,TIPO DO JOGO,ADVERSÁRIO,PLACAR,X,BDC,RESULTADO,MELHOR EM CAMPO
21/02/2021,AMISTOSO,RAIZES DO YPE,4,X,2,DERROTA,FERRUGEM
14/02/2021,AMISTOSO,REAL SOCIEDAD,2,X,2,EMPATE,KOKA
16/05/2021,AMISTOSO,CORUJA F.C,3,X,1,DERROTA,ERIEL
23/05/2021,FESTIVAL,NATIVOS F.C,1,X,1,DERROTA,SILAS
30/05/2021,AMISTOSO,E.C. NELLY F.C.,4,X,4,EMPATE,LUIZINHO
06/06/2021,AMISTOSO,RATUEIRA F.C.,2,X,1,DERROTA,WILINHA
13/06/2021,AMISTOSO,SANTA TERESA F.C.,0,X,5,VITÓRIA,FERRUGEM
20/06/2021,AMISTOSO,F.C. FRANCHINI,4,X,1,DERROTA,DIOGO
27/06/2021,AMISTOSO,TURIBIO,2,X,2,EMPATE,ERICK
04/07/2021,FESTIVAL,VILA REAL,1,X,1,EMPATE,JULIANO
18/07/2021,AMISTOSO,LARGADOS E.C.,0,X,2,VITÓRIA,ERICK
25/07/2021,AMISTOSO,NATIVOS F.C,2,X,0,DERROTA,KOKA
01/08/2021,AMISTOSO,REAL SOCIEDAD,1,X,1,EMPATE,KOKA
08/08/2021,AMISTOSO,DIVINOS F.C,1,X,3,VITÓRIA,DAVID
22/08/2021,AMISTOSO,MOTIVO PRA BEBER,3,X,3,EMPATE,ERICK
29/08/2021,FESTIVAL,BOIADEIROS,4,X,1,DERROTA,RODRIGO
12/09/2021,AMISTOSO,CORUJA F.C,2,X,5,VITÓRIA,ERICK
19/09/2021,AMISTOSO,GREMIO BUTANTA,3,X,2,DERROTA,DAVID
03/10/2021,AMISTOSO,INDEPENDENTE F.C,1,x,1,EMPATE,ERICK
26/09/2021,FESTIVAL,JUVENTUDE F.C,3,X,2,DERROTA,Koka
10/10/2021,AMISTOSO,ALMEIDA F.C,2,x,2,EMPATE,Luan
24/10/2021,AMISTOSO,XV DE NOVEMBRO F.C,3,x,0,DERROTA,Koka
31/10/2021,AMISTOSO,SANTA LUCIA F.C,0,x,1,VITÓRIA,João
07/11/2021,FESTIVAL,CORUJA F.C,1,x,0,DERROTA,SILAS
21/11/2021,AMISTOSO,PORTO F.C,2,x,1,DERROTA,Menor
28/11/2021,AMISTOSO,AMIGOS DO KLEBER,2,x,4,VITÓRIA,LUIZINHO
05/12/2021,FESTIVAL,UNIÃO ESPORTE E BREJA,1,X,2,VITÓRIA,RODRIGO
30/01/2022,FESTIVAL,REAL PALÁCIO,2,x,2,EMPATE,
06/02/2022,AMISTOSO,,1,x,1,EMPATE,
13/02/2022,AMISTOSO,,4,x,2,DERROTA,
20/02/2022,FESTIVAL,,0,x,2,VITÓRIA,
02/06/2022,AMISTOSO,,1,x,2,VITÓRIA,
"""

_CSV_ARTILHARIA = """\
Data,Jogador
21/02/2021,DAVID
21/02/2021,FERRUGEM
14/02/2021,LUIZINHO
14/02/2021,WILINHA
16/05/2021,RODRIGO
23/05/2021,LUIZINHO
30/05/2021,DAVID
30/05/2021,LUIZINHO
30/05/2021,FERRUGEM
30/05/2021,MENOR
06/06/2021,WILINHA
13/06/2021,MATHEUS
13/06/2021,DAVID
13/06/2021,DAVID
13/06/2021,FERRUGEM
13/06/2021,LUCAS
20/06/2021,DIOGO
27/06/2021,ERICK
27/06/2021,ERICK
04/07/2021,ERICK
18/07/2021,WILINHA
18/07/2021,ERICK
01/08/2021,LUAN
08/08/2021,DAVID
08/08/2021,DAVID
08/08/2021,ERICK
22/08/2021,FERRUGEM
22/08/2021,ERICK
22/08/2021,ERICK
29/08/2021,LUIZINHO NARIGUDO
12/09/2021,ERICK
12/09/2021,ERICK
12/09/2021,WILINHA
12/09/2021,ALEX
12/09/2021,LUIZINHO
19/09/2021,DAVID
19/09/2021,LUIZINHO
03/10/2021,ERICK
10/10/2021,LUAN
10/10/2021,KOKA
26/09/2021,DAVID
26/09/2021,LUIZINHO
31/10/2021,GIO
21/11/2021,JOÃO
28/11/2021,ERICK
28/11/2021,MENOR
28/11/2021,LUIZINHO
28/11/2021,VINICIUS
05/12/2021,WILINHA
05/12/2021,VITÃO
30/01/2022,MENOR
30/01/2022,MENOR
06/02/2022,ALEX
13/02/2022,ERICK
13/02/2022,VITÃO
20/02/2022,ALEX
20/02/2022,KOKA
06/03/2022,DIOGO
06/03/2022,ERICK
"""

# Data da artilharia 06/03/2022 corresponde ao jogo de 02/06/2022 nos resultados
# (provável erro de digitação na planilha original – BDC fez 2 gols em ambos)
_DATA_ALIAS = {
    date(2022, 3, 6): date(2022, 6, 2),
}

_TIPO_MAP = {"AMISTOSO": "Amistoso", "FESTIVAL": "Festival", "CAMPEONATO": "Campeonato"}


def _parse_data(valor: str) -> date:
    valor = valor.strip()
    dia, mes, ano = valor.split("/")
    return date(int(ano), int(mes), int(dia))


def _normalizar_nome(nome: str) -> str:
    return nome.strip().upper()


def _buscar_ou_criar_adversario(conn, nome: str) -> int:
    nome = nome.strip()
    if not nome:
        return None
    row = conn.execute(
        text("SELECT id FROM adversarios WHERE upper(nome) = upper(:n)"),
        {"n": nome},
    ).fetchone()
    if row:
        return row[0]
    result = conn.execute(
        text("INSERT INTO adversarios (nome) VALUES (:n) RETURNING id"),
        {"n": nome},
    )
    novo_id = result.fetchone()[0]
    print(f"    [adversario] Criado: {nome}")
    return novo_id


def _sem_acento(s: str) -> str:
    """Remove diacríticos: 'Joãozinho' → 'JOAOZINHO'."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s.upper())
        if unicodedata.category(c) != "Mn"
    )


# Nomes da planilha que diferem do campo `nome` no banco
_NOMES_ALIAS: dict[str, str] = {
    "LUIZINHO NARIGUDO": "NARIGUDO",   # banco tem "Narigudo"
    "JOAO": "JOAOZINHO",               # banco tem "Joãozinho"
    "JOÃO": "JOAOZINHO",
}


def _build_lookup(conn) -> dict[str, tuple[int, str]]:
    """Carrega todos os jogadores e devolve {chave_normalizada: (id, nome)}."""
    rows = conn.execute(
        text("SELECT id, nome, apelido FROM jogadores")
    ).fetchall()
    lookup: dict[str, tuple[int, str]] = {}
    for jog_id, nome, apelido in rows:
        lookup[_sem_acento(nome)] = (jog_id, nome)
        if apelido:
            lookup[_sem_acento(apelido)] = (jog_id, nome)
    return lookup


def _buscar_jogador(lookup: dict, nome_csv: str):
    """Retorna (id, nome_real) ou None. Usa lookup pré-carregado em memória."""
    chave = _sem_acento(nome_csv)
    # Tenta alias explícito primeiro
    chave = _NOMES_ALIAS.get(chave, _NOMES_ALIAS.get(nome_csv.upper(), chave))
    return lookup.get(chave)


def _jogo_existe(conn, data_jogo: date, adversario_id) -> int | None:
    row = conn.execute(
        text("""
            SELECT id FROM jogos
            WHERE data = :d AND (adversario_id = :a OR (adversario_id IS NULL AND :a IS NULL))
        """),
        {"d": data_jogo, "a": adversario_id},
    ).fetchone()
    return row[0] if row else None


def main():
    df_res = pd.read_csv(io.StringIO(_CSV_RESULTADOS))
    df_art = pd.read_csv(io.StringIO(_CSV_ARTILHARIA))

    # Normaliza datas na artilharia
    df_art["data_obj"] = df_art["Data"].apply(_parse_data)
    # Aplica alias de datas
    df_art["data_obj"] = df_art["data_obj"].apply(lambda d: _DATA_ALIAS.get(d, d))

    # Agrupa gols por jogo (data)
    gols_por_data: dict[date, list[str]] = {}
    for _, row in df_art.iterrows():
        d = row["data_obj"]
        gols_por_data.setdefault(d, []).append(_normalizar_nome(row["Jogador"]))

    jogos_inseridos = 0
    gols_inseridos = 0
    jogos_pulados = 0
    nao_encontrados: list[str] = []

    with get_engine().begin() as conn:
        lookup = _build_lookup(conn)

        for _, row in df_res.iterrows():
            data_jogo = _parse_data(str(row["DATA"]))
            tipo = _TIPO_MAP.get(str(row["TIPO DO JOGO"]).strip().upper(), "Amistoso")
            adv_nome = str(row["ADVERSÁRIO"]).strip() if pd.notna(row["ADVERSÁRIO"]) else ""
            gols_adv = int(row["PLACAR"])
            gols_bdc = int(row["BDC"])

            adversario_id = _buscar_ou_criar_adversario(conn, adv_nome) if adv_nome else None

            # Pula se jogo já existe
            if _jogo_existe(conn, data_jogo, adversario_id):
                jogos_pulados += 1
                continue

            result = conn.execute(
                text("""
                    INSERT INTO jogos
                        (data, tipo, adversario_id, campo_id, cor_uniforme,
                         gols_bdc, gols_adversario, casa)
                    VALUES (:data, :tipo, :adv, NULL, 'Preto',
                            :gbdc, :gadv, NULL)
                    RETURNING id
                """),
                {
                    "data": data_jogo,
                    "tipo": tipo,
                    "adv": adversario_id,
                    "gbdc": gols_bdc,
                    "gadv": gols_adv,
                },
            )
            jogo_id = result.fetchone()[0]
            jogos_inseridos += 1

            adv_label = adv_nome or "(sem adversario)"
            print(f"  Jogo {data_jogo} vs {adv_label} {gols_bdc}x{gols_adv} id={jogo_id}")

            # Insere gols deste jogo
            gols_neste_jogo = gols_por_data.get(data_jogo, [])
            for ordem, nome_upper in enumerate(gols_neste_jogo, start=1):
                resultado = _buscar_jogador(lookup, nome_upper)
                if resultado is None:
                    nao_encontrados.append(f"{data_jogo} | {nome_upper}")
                    print(f"    [gol] Jogador NAO encontrado: {nome_upper}")
                    continue
                jogador_id, nome_real = resultado
                conn.execute(
                    text("""
                        INSERT INTO gols
                            (jogo_id, jogador_id, assistente_id, ordem,
                             posicao, forma, local, tempo)
                        VALUES (:j, :p, NULL, :o, NULL, NULL, NULL, NULL)
                    """),
                    {"j": jogo_id, "p": jogador_id, "o": ordem},
                )
                gols_inseridos += 1
                print(f"    [gol {ordem}] {nome_real}")

    print(f"\nConcluido:")
    print(f"  Jogos inseridos : {jogos_inseridos}")
    print(f"  Jogos pulados   : {jogos_pulados} (ja existiam)")
    print(f"  Gols inseridos  : {gols_inseridos}")
    if nao_encontrados:
        print(f"  Jogadores NAO encontrados ({len(nao_encontrados)}):")
        for x in nao_encontrados:
            print(f"    - {x}")


if __name__ == "__main__":
    main()
