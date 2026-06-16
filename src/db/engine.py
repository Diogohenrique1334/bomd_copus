"""Configuração da conexão com o Neon (Postgres) via SQLAlchemy.

Lê a variável DATABASE_URL do ambiente (arquivo .env na raiz) e expõe um
engine e uma fábrica de sessões reutilizáveis pelo restante da aplicação.
"""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

load_dotenv()


def _normalizar_url(url: str) -> str:
    """Garante o uso do driver psycopg v3 no SQLAlchemy.

    O Neon entrega a string no formato ``postgresql://...``; o SQLAlchemy
    precisa do prefixo ``postgresql+psycopg://`` para usar o psycopg 3, que
    suporta ``channel_binding=require`` sem ajustes.
    """
    if url.startswith("postgresql+"):
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Retorna um engine singleton configurado para o Neon."""
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL não definida. Configure-a no arquivo .env na raiz do projeto."
        )
    return create_engine(
        _normalizar_url(url.strip()),
        pool_pre_ping=True,   # revalida conexões ociosas (Neon hiberna)
        pool_recycle=300,
    )


SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)
