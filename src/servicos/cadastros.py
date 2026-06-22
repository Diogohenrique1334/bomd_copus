"""Regras de negócio dos cadastros básicos: atletas, adversários e campos.

Cada função abre sua própria sessão e faz commit. As funções de edição
recebem o id e os novos valores e atualizam apenas os campos informados.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from src.db import repositorio as repo
from src.db.engine import SessionLocal
from src.db.models import Adversario, Campo, Jogador

POSICOES = ["Goleiro", "Zagueiro", "Lateral", "Volante", "Meio-Campo", "Atacante"]


# ------------------------------ Atletas ------------------------------
def listar_atletas(apenas_ativos: bool = False) -> list[Jogador]:
    with SessionLocal() as session:
        return repo.listar_jogadores(session, apenas_ativos=apenas_ativos)


def criar_atleta(
    *,
    nome: str,
    apelido: Optional[str] = None,
    rg: Optional[str] = None,
    celular: Optional[str] = None,
    posicao: Optional[str] = None,
    data_nascimento: Optional[date] = None,
) -> int:
    nome = nome.strip()
    if not nome:
        raise ValueError("Nome do atleta é obrigatório.")
    with SessionLocal() as session:
        if repo.obter_jogador_por_nome(session, nome):
            raise ValueError(f"Já existe um atleta chamado '{nome}'.")
        atleta = repo.criar_jogador(
            session, nome=nome, apelido=apelido, rg=rg, celular=celular,
            posicao=posicao, data_nascimento=data_nascimento,
        )
        session.commit()
        return atleta.id


def editar_atleta(
    atleta_id: int,
    *,
    nome: str,
    apelido: Optional[str],
    rg: Optional[str],
    celular: Optional[str],
    posicao: Optional[str],
    ativo: bool,
    data_nascimento: Optional[date] = None,
) -> None:
    with SessionLocal() as session:
        atleta = repo.obter_jogador(session, atleta_id)
        if not atleta:
            raise ValueError("Atleta não encontrado.")
        atleta.nome = nome.strip()
        atleta.apelido = apelido
        atleta.rg = rg
        atleta.celular = celular
        atleta.posicao = posicao
        atleta.data_nascimento = data_nascimento
        atleta.ativo = ativo
        session.commit()


# ---------------------------- Adversários ----------------------------
def listar_adversarios() -> list[Adversario]:
    with SessionLocal() as session:
        return repo.listar_adversarios(session)


def criar_adversario(*, nome: str, bairro: Optional[str] = None) -> int:
    nome = nome.strip()
    if not nome:
        raise ValueError("Nome do adversário é obrigatório.")
    with SessionLocal() as session:
        if repo.obter_adversario_por_nome(session, nome):
            raise ValueError(f"Adversário '{nome}' já cadastrado.")
        adv = repo.criar_adversario(session, nome=nome, bairro=bairro)
        session.commit()
        return adv.id


def editar_adversario(adversario_id: int, *, nome: str, bairro: Optional[str]) -> None:
    with SessionLocal() as session:
        adv = repo.obter_adversario(session, adversario_id)
        if not adv:
            raise ValueError("Adversário não encontrado.")
        adv.nome = nome.strip()
        adv.bairro = bairro
        session.commit()


# ------------------------------- Campos ------------------------------
def listar_campos() -> list[Campo]:
    with SessionLocal() as session:
        return repo.listar_campos(session)


def criar_campo(*, nome: str, cidade: Optional[str] = None) -> int:
    nome = nome.strip()
    if not nome:
        raise ValueError("Nome do campo é obrigatório.")
    with SessionLocal() as session:
        if repo.obter_campo_por_nome(session, nome, cidade):
            raise ValueError(f"Campo '{nome}' já cadastrado para esta cidade.")
        campo = repo.criar_campo(session, nome=nome, cidade=cidade)
        session.commit()
        return campo.id


def editar_campo(campo_id: int, *, nome: str, cidade: Optional[str]) -> None:
    with SessionLocal() as session:
        campo = repo.obter_campo(session, campo_id)
        if not campo:
            raise ValueError("Campo não encontrado.")
        campo.nome = nome.strip()
        campo.cidade = cidade
        session.commit()
