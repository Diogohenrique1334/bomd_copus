"""Montagem da escalação a partir da forma dos atletas (heurística, sem ML).

Fluxo:
1. `stats.notas_por_jogo_jogador()` devolve as notas em formato longo.
2. `ranquear(df_notas, criterio, disponiveis)` agrega por jogador segundo o
   critério escolhido (média recente/histórica/ponderada, tendência, regularidade
   ou presença) e devolve um ranking.
3. `montar_escalacao(df_rank, formacao)` preenche os 11 slots da formação: cada
   vaga recebe o melhor disponível da posição certa; vagas sem atleta da posição
   são preenchidas pelo melhor restante (marcado como improvisado).

Coordenadas dos slots em % do campo (x: 0=esq, 100=dir; y: 0=defesa, 100=ataque),
usadas pelo gráfico `campo_futebol`.
"""
from __future__ import annotations

import statistics as _stats
from typing import List, Optional, Tuple

import pandas as pd

# ── Formações (Campo 11) ─────────────────────────────────────────────────────
# Cada slot: {slot (rótulo), pos (posições aceitas, em ordem de preferência),
# x, y}. As posições do elenco são: Goleiro, Lateral, Zagueiro, Volante,
# Meio-Campo, Atacante.

_GK = ("GOL", ["Goleiro"])
_LAT = ("LAT", ["Lateral"])
_ZAG = ("ZAG", ["Zagueiro"])
_VOL = ("VOL", ["Volante", "Meio-Campo"])
_MEI = ("MEI", ["Meio-Campo", "Volante"])
_ATA = ("ATA", ["Atacante"])
_ALA = ("ALA", ["Lateral", "Meio-Campo"])  # ala/ponta em esquemas com 3 zagueiros


def _espalhar(n: int, margem: int = 14) -> List[int]:
    """Posições x igualmente espaçadas para uma linha com `n` jogadores."""
    if n == 1:
        return [50]
    return [round(margem + i * (100 - 2 * margem) / (n - 1)) for i in range(n)]


def _linha(specs: List[tuple], y: int, margem: int = 14) -> List[dict]:
    xs = _espalhar(len(specs), margem)
    return [{"slot": s, "pos": list(p), "x": x, "y": y} for (s, p), x in zip(specs, xs)]


def _form(*linhas: List[dict]) -> List[dict]:
    slots: List[dict] = []
    for linha in linhas:
        slots.extend(linha)
    return slots


FORMACOES: dict = {
    "4-3-3": _form(
        _linha([_GK], 7),
        _linha([_LAT, _ZAG, _ZAG, _LAT], 26),
        _linha([_VOL, _MEI, _MEI], 52),
        _linha([_ATA, _ATA, _ATA], 84),
    ),
    "4-4-2": _form(
        _linha([_GK], 7),
        _linha([_LAT, _ZAG, _ZAG, _LAT], 26),
        _linha([_MEI, _VOL, _VOL, _MEI], 54),
        _linha([_ATA, _ATA], 84),
    ),
    "4-2-3-1": _form(
        _linha([_GK], 7),
        _linha([_LAT, _ZAG, _ZAG, _LAT], 23),
        _linha([_VOL, _VOL], 43, margem=30),
        _linha([_MEI, _MEI, _MEI], 64),
        _linha([_ATA], 87),
    ),
    "3-5-2": _form(
        _linha([_GK], 7),
        _linha([_ZAG, _ZAG, _ZAG], 24),
        _linha([_ALA, _VOL, _MEI, _VOL, _ALA], 54),
        _linha([_ATA, _ATA], 85),
    ),
    "3-4-3": _form(
        _linha([_GK], 7),
        _linha([_ZAG, _ZAG, _ZAG], 24),
        _linha([_ALA, _VOL, _MEI, _ALA], 54),
        _linha([_ATA, _ATA, _ATA], 85),
    ),
    "5-3-2": _form(
        _linha([_GK], 7),
        _linha([_LAT, _ZAG, _ZAG, _ZAG, _LAT], 24),
        _linha([_VOL, _MEI, _VOL], 55),
        _linha([_ATA, _ATA], 85),
    ),
    "4-5-1": _form(
        _linha([_GK], 7),
        _linha([_LAT, _ZAG, _ZAG, _LAT], 24),
        _linha([_MEI, _VOL, _MEI, _VOL, _MEI], 55),
        _linha([_ATA], 87),
    ),
}


# ── Critérios de ranqueamento ────────────────────────────────────────────────
# Rótulo exibido na UI -> chave interna usada no cálculo.
CRITERIOS: dict = {
    "Média últimos 3 jogos": "media3",
    "Média últimos 10 jogos": "media10",
    "Média histórica": "media_hist",
    "Média ponderada (recência)": "ponderada",
    "Em alta (tendência)": "tendencia",
    "Mais regular (menor desvio)": "regularidade",
    "Mais jogos jogados": "presenca",
}


def _agregar(df_notas: pd.DataFrame) -> pd.DataFrame:
    """Calcula, por jogador, todas as métricas de forma a partir das notas longas."""
    linhas = []
    for (jogador, posicao), grp in df_notas.sort_values("data").groupby(["jogador", "posicao"]):
        notas = [float(x) for x in grp["nota_jogo"].tolist()]
        n = len(notas)
        media_hist = round(_stats.mean(notas), 2)
        media3 = round(_stats.mean(notas[-3:]), 2)
        media10 = round(_stats.mean(notas[-10:]), 2)
        pesos = list(range(1, n + 1))  # mais recente = peso maior (linear)
        ponderada = round(sum(p * x for p, x in zip(pesos, notas)) / sum(pesos), 2)
        desvio = round(_stats.pstdev(notas), 2) if n > 1 else 0.0
        tend = round(media3 - media_hist, 2)
        linhas.append({
            "jogador": jogador, "posicao": posicao, "n": n,
            "media_hist": media_hist, "media3": media3, "media10": media10,
            "ponderada": ponderada, "desvio": desvio, "tend": tend,
        })
    return pd.DataFrame(linhas)


def ranquear(df_notas: pd.DataFrame, criterio: str,
             disponiveis: Optional[List[str]] = None) -> pd.DataFrame:
    """Ranqueia os atletas pelo critério escolhido.

    Devolve um DataFrame ordenado (melhor primeiro) com colunas:
    jogador, posicao, valor_rank (float p/ ordenar), valor_exib (texto no campo),
    jogos. `disponiveis`: se informado, restringe aos atletas selecionados.
    """
    agg = _agregar(df_notas)
    if disponiveis is not None:
        agg = agg[agg["jogador"].isin(disponiveis)]
    chave = CRITERIOS.get(criterio, "media3")

    out = []
    for _, r in agg.iterrows():
        if chave == "presenca":
            rank, exib = float(r["n"]), f"{int(r['n'])}j"
        elif chave == "tendencia":
            seta = "▲" if r["tend"] >= 0 else "▼"
            rank, exib = float(r["tend"]), f"{seta}{abs(r['tend']):.2f}"
        elif chave == "regularidade":
            # menor desvio = melhor; exige >=3 jogos para o desvio ser confiável
            rank = -(r["desvio"]) if r["n"] >= 3 else -99.0
            exib = f"σ{r['desvio']}"
        else:  # médias
            rank, exib = float(r[chave]), f"{r[chave]}"
        out.append({"jogador": r["jogador"], "posicao": r["posicao"],
                    "valor_rank": rank, "valor_exib": exib, "jogos": int(r["n"])})

    if not out:
        return pd.DataFrame(columns=["jogador", "posicao", "valor_rank", "valor_exib", "jogos"])
    return (
        pd.DataFrame(out)
        .sort_values("valor_rank", ascending=False)
        .reset_index(drop=True)
    )


def montar_escalacao(
    df_rank: pd.DataFrame,
    formacao: Optional[List[dict]] = None,
    min_jogos: int = 1,
) -> Tuple[List[dict], List[dict]]:
    """Preenche os slots da formação a partir do ranking.

    titulares: um dict por slot — slot, x, y, jogador, posicao, exib, jogos,
        improvisado. reservas: atletas que sobraram (jogador, posicao, exib, jogos).
    """
    formacao = formacao or FORMACOES["4-3-3"]
    disp = df_rank[df_rank["jogos"] >= min_jogos].reset_index(drop=True)  # já ordenado por rank

    usados: set = set()
    titulares: List[dict] = []

    def _registrar(slot: dict, idx, row, improvisado: bool) -> dict:
        usados.add(idx)
        return {
            "slot": slot["slot"], "x": slot["x"], "y": slot["y"],
            "jogador": row["jogador"], "posicao": row["posicao"],
            "exib": row["valor_exib"], "jogos": int(row["jogos"]),
            "improvisado": improvisado,
        }

    # 1ª passada — melhor atleta da posição certa
    for slot in formacao:
        escolhido = None
        for idx, row in disp.iterrows():
            if idx not in usados and row["posicao"] in slot["pos"]:
                escolhido = (idx, row)
                break
        if escolhido:
            titulares.append(_registrar(slot, escolhido[0], escolhido[1], improvisado=False))
        else:
            titulares.append({
                "slot": slot["slot"], "x": slot["x"], "y": slot["y"],
                "jogador": None, "posicao": None, "exib": None, "jogos": 0,
                "improvisado": True,
            })

    # 2ª passada — preenche vagas vazias com o melhor restante (improvisado)
    for t in titulares:
        if t["jogador"] is None:
            for idx, row in disp.iterrows():
                if idx not in usados:
                    p = _registrar(t, idx, row, improvisado=True)
                    t.update({"jogador": p["jogador"], "posicao": p["posicao"],
                              "exib": p["exib"], "jogos": p["jogos"]})
                    break

    reservas = [
        {"jogador": row["jogador"], "posicao": row["posicao"],
         "exib": row["valor_exib"], "jogos": int(row["jogos"])}
        for idx, row in disp.iterrows() if idx not in usados
    ]
    return titulares, reservas
