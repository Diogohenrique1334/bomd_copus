"""Agregações de leitura que alimentam o dashboard.

Cada função devolve um pandas.DataFrame ou dict prontos para os gráficos.
As consultas usam o engine diretamente (somente leitura).

Filtros: toda função aceita um `Filtros` opcional (ano/mês/tipo de jogo e, onde
faz sentido, posição). A cláusula é injetada no WHERE via `clausula_jogos()` —
ver `src/servicos/filtros.py`.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd
from sqlalchemy import text

from src.db.engine import get_engine
from src.servicos.filtros import FILTROS_VAZIO, Filtros

_MESES_PT = {
    1: "jan", 2: "fev", 3: "mar", 4: "abr", 5: "mai", 6: "jun",
    7: "jul", 8: "ago", 9: "set", 10: "out", 11: "nov", 12: "dez",
}

_RES_SQL = """CASE
    WHEN gols_bdc > gols_adversario THEN 'Vitória'
    WHEN gols_bdc = gols_adversario THEN 'Empate'
    ELSE 'Derrota'
END"""

# Nome de exibição do atleta no dashboard: apelido quando houver, senão o nome.
# Assume o alias `p` para a tabela jogadores nas queries.
_NOME_EXIB = "COALESCE(NULLIF(p.apelido, ''), p.nome)"


def _ler_sql(query: str, params: Optional[dict] = None) -> pd.DataFrame:
    with get_engine().connect() as conn:
        return pd.read_sql(text(query), conn, params=params or {})


def _f(filtros: Optional[Filtros]) -> Filtros:
    return filtros or FILTROS_VAZIO


# ═══════════════════════════════ JOGOS ════════════════════════════════

def resumo_completo(filtros: Optional[Filtros] = None) -> dict:
    """KPIs gerais: jogos, V/E/D, gols, medianas, desvios, aproveitamento."""
    fc, fp = _f(filtros).clausula_jogos("jogos")
    df = _ler_sql(f"""
        SELECT
            COUNT(*)                                              AS jogos,
            SUM(CASE WHEN gols_bdc > gols_adversario THEN 1 ELSE 0 END) AS vitorias,
            SUM(CASE WHEN gols_bdc = gols_adversario THEN 1 ELSE 0 END) AS empates,
            SUM(CASE WHEN gols_bdc < gols_adversario THEN 1 ELSE 0 END) AS derrotas,
            SUM(gols_bdc)                                         AS gols_pro,
            SUM(gols_adversario)                                  AS gols_contra,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY gols_bdc)          AS mediana_gols_pro,
            ROUND(STDDEV_POP(gols_bdc)::numeric, 2)               AS desv_gols_pro,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY gols_adversario)   AS mediana_gols_contra,
            ROUND(STDDEV_POP(gols_adversario)::numeric, 2)        AS desv_gols_contra,
            ROUND(
                (SUM(CASE WHEN gols_bdc > gols_adversario THEN 3
                          WHEN gols_bdc = gols_adversario THEN 1 ELSE 0 END
                )::float / NULLIF(COUNT(*) * 3, 0) * 100)::numeric, 1
            ) AS aproveitamento_pct
        FROM jogos
        WHERE 1=1 {fc}
    """, fp)
    return df.iloc[0].to_dict() if not df.empty else {}


def aproveitamento_casa_fora(filtros: Optional[Filtros] = None) -> pd.DataFrame:
    """Aproveitamento (% pontos) dividido por casa/fora (colunas: local, jogos, aproveitamento_pct)."""
    fc, fp = _f(filtros).clausula_jogos("jogos")
    return _ler_sql(f"""
        SELECT
            CASE WHEN casa THEN 'Casa' ELSE 'Fora' END AS local,
            COUNT(*) AS jogos,
            ROUND(
                (SUM(CASE WHEN gols_bdc > gols_adversario THEN 3
                          WHEN gols_bdc = gols_adversario THEN 1 ELSE 0 END
                )::float / NULLIF(COUNT(*) * 3, 0) * 100)::numeric, 2
            ) AS aproveitamento_pct
        FROM jogos
        WHERE casa IS NOT NULL {fc}
        GROUP BY casa
        ORDER BY casa DESC
    """, fp)


def visao_geral_casa_fora(filtros: Optional[Filtros] = None) -> pd.DataFrame:
    """V/E/D divididos por casa/fora para o gráfico empilhado."""
    fc, fp = _f(filtros).clausula_jogos("jogos")
    return _ler_sql(f"""
        SELECT
            CASE WHEN casa THEN 'Casa' ELSE 'Fora' END AS local,
            {_RES_SQL} AS resultado,
            COUNT(*) AS jogos
        FROM jogos
        WHERE casa IS NOT NULL {fc}
        GROUP BY casa, resultado
        ORDER BY casa DESC, resultado
    """, fp)


def ultimos_jogos(n: int = 20, filtros: Optional[Filtros] = None) -> pd.DataFrame:
    """Últimos N jogos com adversário, gols e resultado."""
    fc, fp = _f(filtros).clausula_jogos("j")
    df = _ler_sql(f"""
        SELECT
            j.data,
            COALESCE(a.nome, '?') AS adversario,
            j.gols_bdc,
            j.gols_adversario,
            {_RES_SQL} AS resultado
        FROM jogos j
        LEFT JOIN adversarios a ON a.id = j.adversario_id
        WHERE 1=1 {fc}
        ORDER BY j.data DESC
        LIMIT :n
    """, {**fp, "n": n})
    # Volta em ordem cronológica para o gráfico
    return df.iloc[::-1].reset_index(drop=True)


def aproveitamento_por_mes(filtros: Optional[Filtros] = None) -> pd.DataFrame:
    """% aproveitamento por mês (colunas: mes, aproveitamento_pct)."""
    fc, fp = _f(filtros).clausula_jogos("jogos")
    df = _ler_sql(f"""
        SELECT
            EXTRACT(MONTH FROM data)::int AS mes_num,
            ROUND(
                (SUM(CASE WHEN gols_bdc > gols_adversario THEN 3
                          WHEN gols_bdc = gols_adversario THEN 1 ELSE 0 END
                )::float / NULLIF(COUNT(*) * 3, 0) * 100)::numeric, 1
            ) AS aproveitamento_pct
        FROM jogos
        WHERE 1=1 {fc}
        GROUP BY mes_num
        ORDER BY mes_num
    """, fp)
    df["mes"] = df["mes_num"].map(_MESES_PT)
    return df[["mes", "aproveitamento_pct"]]


def media_jogadores_por_campo(filtros: Optional[Filtros] = None) -> pd.DataFrame:
    """Média de jogadores (jogou=True) por campo (colunas: campo, media_jogadores)."""
    fc, fp = _f(filtros).clausula_jogos("j")
    return _ler_sql(f"""
        SELECT c.nome AS campo,
               ROUND(AVG(cnt)::numeric, 1) AS media_jogadores
        FROM (
            SELECT j.campo_id, COUNT(DISTINCT a.jogador_id) AS cnt
            FROM jogos j
            JOIN avaliacoes a ON a.jogo_id = j.id
            WHERE a.jogou = TRUE AND j.campo_id IS NOT NULL {fc}
            GROUP BY j.id, j.campo_id
        ) sub
        JOIN campos c ON c.id = sub.campo_id
        GROUP BY c.nome
        ORDER BY media_jogadores DESC
    """, fp)


# ═══════════════════════════════ AVALIAÇÕES ════════════════════════════

def resumo_avaliacoes(filtros: Optional[Filtros] = None) -> dict:
    """N. média de votos por jogo, desvio; nota média geral e desvio."""
    fc, fp = _f(filtros).clausula_jogos("j")
    df = _ler_sql(f"""
        SELECT
            ROUND(AVG(votos_por_jogo)::numeric, 2) AS media_votos_jogo,
            ROUND(STDDEV_POP(votos_por_jogo)::numeric, 2) AS desv_votos_jogo,
            ROUND(AVG(nota_media_jogador)::numeric, 2) AS media_nota_atletas,
            ROUND(STDDEV_POP(nota_media_jogador)::numeric, 2) AS desv_nota_atletas
        FROM (
            SELECT
                a.jogo_id,
                COUNT(DISTINCT a.votante)::float AS votos_por_jogo,
                AVG(a.nota) AS nota_media_jogador
            FROM avaliacoes a
            JOIN jogos j ON j.id = a.jogo_id
            WHERE a.jogou = TRUE AND a.nota IS NOT NULL {fc}
            GROUP BY a.jogo_id
        ) sub
    """, fp)
    return df.iloc[0].to_dict() if not df.empty else {}


def nota_media_por_resultado(filtros: Optional[Filtros] = None) -> pd.DataFrame:
    """Nota média por resultado do jogo (colunas: resultado, nota_media)."""
    fc, fp = _f(filtros).clausula_jogos("j")
    return _ler_sql(f"""
        SELECT
            {_RES_SQL} AS resultado,
            ROUND(AVG(a.nota)::numeric, 2) AS nota_media
        FROM avaliacoes a
        JOIN jogos j ON j.id = a.jogo_id
        WHERE a.jogou = TRUE AND a.nota IS NOT NULL {fc}
        GROUP BY resultado
        ORDER BY nota_media DESC
    """, fp)


def nota_media_por_tipo(filtros: Optional[Filtros] = None) -> pd.DataFrame:
    """Nota média por tipo de jogo (colunas: tipo, nota_media)."""
    fc, fp = _f(filtros).clausula_jogos("j")
    return _ler_sql(f"""
        SELECT
            COALESCE(j.tipo, 'Sem tipo') AS tipo,
            ROUND(AVG(a.nota)::numeric, 2) AS nota_media
        FROM avaliacoes a
        JOIN jogos j ON j.id = a.jogo_id
        WHERE a.jogou = TRUE AND a.nota IS NOT NULL {fc}
        GROUP BY j.tipo
        ORDER BY nota_media DESC
    """, fp)


def nota_media_por_posicao(filtros: Optional[Filtros] = None) -> pd.DataFrame:
    """Nota média e desvio padrão por posição do jogador."""
    f = _f(filtros)
    fc, fp = f.clausula_jogos("j")
    pc, pp = f.clausula_posicao("p")
    return _ler_sql(f"""
        SELECT
            COALESCE(p.posicao, 'Sem pos.') AS posicao,
            ROUND(AVG(a.nota)::numeric, 2) AS nota_media,
            ROUND(STDDEV_POP(a.nota)::numeric, 2) AS desvio
        FROM avaliacoes a
        JOIN jogos j ON j.id = a.jogo_id
        JOIN jogadores p ON p.id = a.jogador_id
        WHERE a.jogou = TRUE AND a.nota IS NOT NULL AND p.posicao IS NOT NULL {fc} {pc}
        GROUP BY p.posicao
        ORDER BY posicao
    """, {**fp, **pp})


def nota_media_por_campo(filtros: Optional[Filtros] = None) -> pd.DataFrame:
    """Nota média por campo (colunas: campo, nota_media)."""
    fc, fp = _f(filtros).clausula_jogos("j")
    return _ler_sql(f"""
        SELECT c.nome AS campo,
               ROUND(AVG(a.nota)::numeric, 2) AS nota_media
        FROM avaliacoes a
        JOIN jogos j ON j.id = a.jogo_id
        JOIN campos c ON c.id = j.campo_id
        WHERE a.jogou = TRUE AND a.nota IS NOT NULL {fc}
        GROUP BY c.nome
        ORDER BY nota_media DESC
    """, fp)


def nota_media_por_partida(filtros: Optional[Filtros] = None) -> pd.DataFrame:
    """Nota média por partida com resultado (para barras coloridas)."""
    fc, fp = _f(filtros).clausula_jogos("j")
    return _ler_sql(f"""
        SELECT
            j.data,
            COALESCE(adv.nome, '?') AS adversario,
            ROUND(AVG(a.nota)::numeric, 2) AS nota_media,
            {_RES_SQL} AS resultado
        FROM avaliacoes a
        JOIN jogos j ON j.id = a.jogo_id
        LEFT JOIN adversarios adv ON adv.id = j.adversario_id
        WHERE a.jogou = TRUE AND a.nota IS NOT NULL {fc}
        GROUP BY j.id, j.data, adv.nome, j.gols_bdc, j.gols_adversario
        ORDER BY j.data
    """, fp)


def ranking_notas(filtros: Optional[Filtros] = None) -> pd.DataFrame:
    """Nota média por jogador (colunas: jogador, nota_media, votos)."""
    f = _f(filtros)
    fc, fp = f.clausula_jogos("j")
    pc, pp = f.clausula_posicao("p")
    return _ler_sql(f"""
        SELECT {_NOME_EXIB} AS jogador,
               ROUND(AVG(a.nota)::numeric, 2) AS nota_media,
               COUNT(a.nota) AS votos
        FROM avaliacoes a
        JOIN jogadores p ON p.id = a.jogador_id
        JOIN jogos j ON j.id = a.jogo_id
        WHERE a.jogou = TRUE {fc} {pc}
        GROUP BY {_NOME_EXIB}
        HAVING COUNT(a.nota) > 0
        ORDER BY nota_media DESC
    """, {**fp, **pp})


def nota_media_por_mes(filtros: Optional[Filtros] = None) -> pd.DataFrame:
    """Nota média por mês (colunas: mes, nota_media)."""
    fc, fp = _f(filtros).clausula_jogos("j")
    df = _ler_sql(f"""
        SELECT
            EXTRACT(MONTH FROM j.data)::int AS mes_num,
            ROUND(AVG(a.nota)::numeric, 2) AS nota_media
        FROM avaliacoes a
        JOIN jogos j ON j.id = a.jogo_id
        WHERE a.jogou = TRUE AND a.nota IS NOT NULL {fc}
        GROUP BY mes_num
        ORDER BY mes_num
    """, fp)
    df["mes"] = df["mes_num"].map(_MESES_PT)
    return df[["mes", "nota_media"]]


def evolucao_jogador(nome: str, filtros: Optional[Filtros] = None) -> pd.DataFrame:
    """Nota média do jogador por jogo ao longo do tempo."""
    fc, fp = _f(filtros).clausula_jogos("j")
    return _ler_sql(f"""
        SELECT j.data AS data,
               ROUND(AVG(a.nota)::numeric, 2) AS nota_media
        FROM avaliacoes a
        JOIN jogos j ON j.id = a.jogo_id
        JOIN jogadores p ON p.id = a.jogador_id
        WHERE {_NOME_EXIB} = :nome AND a.jogou = TRUE {fc}
        GROUP BY j.data
        ORDER BY j.data
    """, {**fp, "nome": nome})


def jogos_avaliados() -> pd.DataFrame:
    """Jogos que têm avaliações, do mais recente ao mais antigo.

    Colunas: id, data, adversario, gols_bdc, gols_adversario. Alimenta o seletor
    de jogo da seção "Melhor em Campo & Ranking do Jogo".
    """
    return _ler_sql("""
        SELECT j.id, j.data,
               COALESCE(adv.nome, '?') AS adversario,
               j.gols_bdc, j.gols_adversario
        FROM jogos j
        LEFT JOIN adversarios adv ON adv.id = j.adversario_id
        WHERE EXISTS (
            SELECT 1 FROM avaliacoes a
            WHERE a.jogo_id = j.id AND a.jogou = TRUE AND a.nota IS NOT NULL
        )
        ORDER BY j.data DESC
    """)


def notas_do_jogo(jogo_id: int) -> pd.DataFrame:
    """Ranking de notas dos jogadores em um jogo específico.

    Colunas: jogador_id, jogador (apelido), nota (média dos votos), votos —
    ordenado da maior nota para a menor. A 1ª linha é o "Melhor em Campo".
    """
    return _ler_sql(f"""
        SELECT p.id AS jogador_id,
               {_NOME_EXIB} AS jogador,
               ROUND(AVG(a.nota)::numeric, 2) AS nota,
               COUNT(a.nota) AS votos
        FROM avaliacoes a
        JOIN jogadores p ON p.id = a.jogador_id
        WHERE a.jogo_id = :jogo_id AND a.jogou = TRUE AND a.nota IS NOT NULL
              AND COALESCE(p.eh_atleta, TRUE)
        GROUP BY p.id, {_NOME_EXIB}
        ORDER BY nota DESC
    """, {"jogo_id": jogo_id})


def ranking_melhor_em_campo(filtros: Optional[Filtros] = None) -> pd.DataFrame:
    """Quantas vezes cada jogador foi o melhor em campo (maior nota do jogo).

    Por jogo, calcula a nota média de cada atleta e marca como "melhor" quem tem
    a maior nota (empates contam para todos os empatados). Colunas: jogador, vezes.
    """
    fc, fp = _f(filtros).clausula_jogos("j")
    return _ler_sql(f"""
        WITH nota_jogo AS (
            SELECT a.jogo_id, a.jogador_id, AVG(a.nota) AS media
            FROM avaliacoes a
            JOIN jogos j ON j.id = a.jogo_id
            WHERE a.jogou = TRUE AND a.nota IS NOT NULL {fc}
            GROUP BY a.jogo_id, a.jogador_id
        ),
        ranqueado AS (
            SELECT jogo_id, jogador_id,
                   RANK() OVER (PARTITION BY jogo_id ORDER BY media DESC) AS posicao
            FROM nota_jogo
        )
        SELECT {_NOME_EXIB} AS jogador, COUNT(*) AS vezes
        FROM ranqueado r
        JOIN jogadores p ON p.id = r.jogador_id
        WHERE r.posicao = 1
        GROUP BY {_NOME_EXIB}
        ORDER BY vezes DESC
    """, fp)


# ═══════════════════════════════ GOLS ═════════════════════════════════

def resumo_gols(filtros: Optional[Filtros] = None) -> dict:
    """KPIs de gols: total, atletas, média, desvio, assists, média assists."""
    f = _f(filtros)
    fc_j, fp_j = f.clausula_jogos("j")     # para subqueries de jogos
    fc_g, fp_g = f.clausula_jogos("j2")    # para subqueries de gols (join jogos j2)
    df = _ler_sql(f"""
        SELECT
            (SELECT COUNT(*) FROM gols g
             JOIN jogos j2 ON j2.id = g.jogo_id WHERE 1=1 {fc_g}) AS total_gols,
            (SELECT COUNT(DISTINCT g.jogador_id) FROM gols g
             JOIN jogos j2 ON j2.id = g.jogo_id
             JOIN jogadores p ON p.id = g.jogador_id
             WHERE COALESCE(p.eh_atleta, TRUE) {fc_g}) AS atletas,
            (SELECT COUNT(*) FROM gols g
             JOIN jogos j2 ON j2.id = g.jogo_id
             WHERE g.assistente_id IS NOT NULL {fc_g}) AS total_assists,
            (SELECT ROUND(AVG(gols_bdc)::numeric, 2) FROM jogos j WHERE 1=1 {fc_j}) AS media_gols,
            (SELECT ROUND(STDDEV_POP(gols_bdc)::numeric, 2) FROM jogos j WHERE 1=1 {fc_j}) AS desv_gols,
            (SELECT ROUND(AVG(cnt)::numeric, 2)
             FROM (SELECT g.jogo_id, COUNT(*) AS cnt FROM gols g
                   JOIN jogos j2 ON j2.id = g.jogo_id
                   WHERE g.assistente_id IS NOT NULL {fc_g}
                   GROUP BY g.jogo_id) sub
            ) AS media_assists
    """, {**fp_j, **fp_g})
    return df.iloc[0].to_dict() if not df.empty else {}


def status_assistencias(filtros: Optional[Filtros] = None) -> pd.DataFrame:
    """Gols com e sem assistência (colunas: status, qtd)."""
    fc, fp = _f(filtros).clausula_jogos("j")
    return _ler_sql(f"""
        SELECT
            CASE WHEN g.assistente_id IS NOT NULL THEN 'Com assistência' ELSE 'Sem assistência' END AS status,
            COUNT(*) AS qtd
        FROM gols g
        JOIN jogos j ON j.id = g.jogo_id
        WHERE 1=1 {fc}
        GROUP BY (g.assistente_id IS NOT NULL)
    """, fp)


def media_gols_casa_fora(filtros: Optional[Filtros] = None) -> pd.DataFrame:
    """Média de gols BDC por jogo, separado por casa/fora."""
    fc, fp = _f(filtros).clausula_jogos("jogos")
    return _ler_sql(f"""
        SELECT
            CASE WHEN casa THEN 'Casa' ELSE 'Fora' END AS local,
            ROUND(AVG(gols_bdc)::numeric, 1) AS media_gols
        FROM jogos
        WHERE casa IS NOT NULL {fc}
        GROUP BY casa
        ORDER BY casa DESC
    """, fp)


def media_gols_por_tipo(filtros: Optional[Filtros] = None) -> pd.DataFrame:
    """Média de gols BDC por tipo de jogo."""
    fc, fp = _f(filtros).clausula_jogos("jogos")
    return _ler_sql(f"""
        SELECT
            COALESCE(tipo, 'Sem tipo') AS tipo,
            ROUND(AVG(gols_bdc)::numeric, 1) AS media_gols
        FROM jogos
        WHERE 1=1 {fc}
        GROUP BY tipo
        ORDER BY media_gols DESC
    """, fp)


def media_gols_por_resultado(filtros: Optional[Filtros] = None) -> pd.DataFrame:
    """Média de gols BDC por resultado do jogo."""
    fc, fp = _f(filtros).clausula_jogos("jogos")
    return _ler_sql(f"""
        SELECT
            {_RES_SQL} AS resultado,
            ROUND(AVG(gols_bdc)::numeric, 1) AS media_gols
        FROM jogos
        WHERE 1=1 {fc}
        GROUP BY resultado
        ORDER BY media_gols DESC
    """, fp)


def participacoes_por_posicao(filtros: Optional[Filtros] = None) -> pd.DataFrame:
    """Gols + assistências por posição (colunas: posicao, gols, assists, total)."""
    f = _f(filtros)
    fc, fp = f.clausula_jogos("j")
    pc, pp = f.clausula_posicao("p")
    df = _ler_sql(f"""
        WITH g_filtrados AS (
            SELECT g.jogador_id, g.assistente_id
            FROM gols g
            JOIN jogos j ON j.id = g.jogo_id
            WHERE 1=1 {fc}
        )
        SELECT
            COALESCE(p.posicao, 'Sem pos.') AS posicao,
            COUNT(*) FILTER (WHERE gf.jogador_id = p.id) AS gols,
            COUNT(*) FILTER (WHERE gf.assistente_id = p.id) AS assists
        FROM jogadores p
        LEFT JOIN g_filtrados gf ON gf.jogador_id = p.id OR gf.assistente_id = p.id
        WHERE p.posicao IS NOT NULL {pc}
        GROUP BY p.posicao
        ORDER BY posicao
    """, {**fp, **pp})
    df["total"] = df["gols"] + df["assists"]
    return df.sort_values("total", ascending=False)


def artilharia(filtros: Optional[Filtros] = None) -> pd.DataFrame:
    """Total de gols por jogador (colunas: jogador, gols)."""
    f = _f(filtros)
    fc, fp = f.clausula_jogos("j")
    pc, pp = f.clausula_posicao("p")
    return _ler_sql(f"""
        SELECT {_NOME_EXIB} AS jogador, COUNT(*) AS gols
        FROM gols g
        JOIN jogadores p ON p.id = g.jogador_id
        JOIN jogos j ON j.id = g.jogo_id
        WHERE COALESCE(p.eh_atleta, TRUE) {fc} {pc}
        GROUP BY {_NOME_EXIB}
        ORDER BY gols DESC
    """, {**fp, **pp})


def assistencias(filtros: Optional[Filtros] = None) -> pd.DataFrame:
    """Total de assistências por jogador."""
    f = _f(filtros)
    fc, fp = f.clausula_jogos("j")
    pc, pp = f.clausula_posicao("p")
    return _ler_sql(f"""
        SELECT {_NOME_EXIB} AS jogador, COUNT(*) AS assistencias
        FROM gols g
        JOIN jogadores p ON p.id = g.assistente_id
        JOIN jogos j ON j.id = g.jogo_id
        WHERE g.assistente_id IS NOT NULL AND COALESCE(p.eh_atleta, TRUE) {fc} {pc}
        GROUP BY {_NOME_EXIB}
        ORDER BY assistencias DESC
    """, {**fp, **pp})


def gols_por_tempo(filtros: Optional[Filtros] = None) -> pd.DataFrame:
    """Gols divididos por 1º/2º tempo."""
    fc, fp = _f(filtros).clausula_jogos("j")
    return _ler_sql(f"""
        SELECT COALESCE(g.tempo, 'Não inf.') AS tempo, COUNT(*) AS gols
        FROM gols g
        JOIN jogos j ON j.id = g.jogo_id
        WHERE 1=1 {fc}
        GROUP BY g.tempo
        ORDER BY gols DESC
    """, fp)


def assists_por_tempo(filtros: Optional[Filtros] = None) -> pd.DataFrame:
    """Assistências divididas por 1º/2º tempo."""
    fc, fp = _f(filtros).clausula_jogos("j")
    return _ler_sql(f"""
        SELECT COALESCE(g.tempo, 'Não inf.') AS tempo, COUNT(*) AS assists
        FROM gols g
        JOIN jogos j ON j.id = g.jogo_id
        WHERE g.assistente_id IS NOT NULL {fc}
        GROUP BY g.tempo
        ORDER BY assists DESC
    """, fp)


def forma_gol(filtros: Optional[Filtros] = None) -> pd.DataFrame:
    """Distribuição de formas de gol."""
    fc, fp = _f(filtros).clausula_jogos("j")
    return _ler_sql(f"""
        SELECT COALESCE(g.forma, 'Não inf.') AS forma, COUNT(*) AS gols
        FROM gols g
        JOIN jogos j ON j.id = g.jogo_id
        WHERE 1=1 {fc}
        GROUP BY g.forma
        ORDER BY gols DESC
    """, fp)


def local_gol(filtros: Optional[Filtros] = None) -> pd.DataFrame:
    """Distribuição de locais de gol."""
    fc, fp = _f(filtros).clausula_jogos("j")
    return _ler_sql(f"""
        SELECT COALESCE(g.local, 'Não inf.') AS local, COUNT(*) AS gols
        FROM gols g
        JOIN jogos j ON j.id = g.jogo_id
        WHERE 1=1 {fc}
        GROUP BY g.local
        ORDER BY gols DESC
    """, fp)


def media_gols_por_mes(filtros: Optional[Filtros] = None) -> pd.DataFrame:
    """Total de gols BDC por mês (colunas: mes, total_gols)."""
    fc, fp = _f(filtros).clausula_jogos("jogos")
    df = _ler_sql(f"""
        SELECT
            EXTRACT(MONTH FROM data)::int AS mes_num,
            SUM(gols_bdc) AS total_gols
        FROM jogos
        WHERE 1=1 {fc}
        GROUP BY mes_num
        ORDER BY mes_num
    """, fp)
    df["mes"] = df["mes_num"].map(_MESES_PT)
    return df[["mes", "total_gols"]]


# ═══════════════════════════════ ESCALAÇÃO ════════════════════════════════════

def notas_por_jogo_jogador(filtros: Optional[Filtros] = None,
                           apenas_ativos: bool = True) -> pd.DataFrame:
    """Notas em formato longo: uma linha por jogador × jogo em que ele jogou.

    A "nota do jogo" é a média dos votos que o atleta recebeu naquela partida.
    Colunas: jogador, posicao, data, nota_jogo (ordenado por jogador e data).
    Aceita os mesmos filtros do dashboard (ano/mês/tipo) — assim a forma pode ser
    calculada sobre um recorte (ex.: só o ano atual). Base para os critérios de
    `servicos/escalacao.py` (média recente, histórica, ponderada, tendência...).
    """
    fc, fp = _f(filtros).clausula_jogos("j")
    filtro_ativo = "AND COALESCE(p.ativo, TRUE) = TRUE" if apenas_ativos else ""
    return _ler_sql(f"""
        SELECT {_NOME_EXIB} AS jogador,
               p.posicao AS posicao,
               j.data AS data,
               AVG(a.nota) AS nota_jogo
        FROM avaliacoes a
        JOIN jogos j ON j.id = a.jogo_id
        JOIN jogadores p ON p.id = a.jogador_id
        WHERE a.jogou = TRUE AND a.nota IS NOT NULL AND p.posicao IS NOT NULL
              {filtro_ativo} {fc}
        GROUP BY {_NOME_EXIB}, p.posicao, j.data
        ORDER BY {_NOME_EXIB}, j.data
    """, fp)
