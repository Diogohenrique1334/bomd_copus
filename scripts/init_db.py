"""Cria as tabelas do BDC App no Neon (idempotente).

Também aplica colunas novas que não existiam na criação original via
ALTER TABLE … ADD COLUMN IF NOT EXISTS.

Uso (a partir da raiz do projeto)::

    python -m scripts.init_db
"""
from sqlalchemy import inspect, text

from src.db.engine import get_engine
from src.db.models import Base

# Novas colunas adicionadas após o schema original — aplicadas com ADD COLUMN IF NOT EXISTS
_NOVAS_COLUNAS = [
    ("jogos", "casa", "BOOLEAN"),
]


def main() -> None:
    engine = get_engine()
    Base.metadata.create_all(engine)

    with engine.begin() as conn:
        for tabela, coluna, tipo in _NOVAS_COLUNAS:
            conn.execute(
                text(f"ALTER TABLE {tabela} ADD COLUMN IF NOT EXISTS {coluna} {tipo}")
            )

    tabelas = inspect(engine).get_table_names()
    print("Tabelas no banco:", ", ".join(sorted(tabelas)))


if __name__ == "__main__":
    main()
