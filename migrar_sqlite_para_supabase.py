"""
Migra dados do majubox.db (SQLite) para Supabase/Postgres.

Como usar no Windows:
1) Instale dependências: pip install -r requirements.txt
2) Configure DATABASE_URL no ambiente, ou rode:
   set DATABASE_URL=postgresql://postgres.PROJECT_REF:SENHA@aws-0-sa-east-1.pooler.supabase.com:5432/postgres
3) Rode: python migrar_sqlite_para_supabase.py

Ele NÃO apaga dados do Supabase. Ele faz UPSERT/atualização para evitar duplicar.
"""
import os
import sqlite3
from pathlib import Path

try:
    import psycopg
except Exception as e:
    raise SystemExit("Instale as dependências primeiro: pip install -r requirements.txt") from e

SQLITE_PATH = Path(__file__).parent / "majubox.db"
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL") or os.environ.get("POSTGRES_URL")

TABLES = [
    "machines",
    "genres",
    "dvds",
    "playlists",
    "payments",
    "plays",
    "license_revenue",
    "machine_revenue_log",
    "karaoke_scores",
]


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def main():
    if not SQLITE_PATH.exists():
        raise SystemExit(f"Arquivo não encontrado: {SQLITE_PATH}")
    if not DATABASE_URL:
        raise SystemExit("Configure DATABASE_URL com a connection string do Supabase.")

    sqlite = sqlite3.connect(SQLITE_PATH)
    sqlite.row_factory = sqlite3.Row
    pg = psycopg.connect(DATABASE_URL)

    try:
        with pg:
            with pg.cursor() as cur:
                for table in TABLES:
                    rows = sqlite.execute(f"SELECT * FROM {table}").fetchall()
                    if not rows:
                        print(f"{table}: 0 registros")
                        continue

                    cols = list(rows[0].keys())
                    col_sql = ", ".join(quote_ident(c) for c in cols)
                    placeholders = ", ".join(["%s"] * len(cols))

                    # Chave primária usada no UPSERT.
                    pk = "id"
                    update_cols = [c for c in cols if c != pk]
                    update_sql = ", ".join(f"{quote_ident(c)} = EXCLUDED.{quote_ident(c)}" for c in update_cols)
                    conflict_sql = f"ON CONFLICT ({quote_ident(pk)}) DO UPDATE SET {update_sql}" if update_sql else f"ON CONFLICT ({quote_ident(pk)}) DO NOTHING"

                    sql = f"INSERT INTO {quote_ident(table)} ({col_sql}) VALUES ({placeholders}) {conflict_sql}"
                    for r in rows:
                        cur.execute(sql, tuple(r[c] for c in cols))
                    print(f"{table}: {len(rows)} registros migrados")

                # Ajusta sequências BIGSERIAL para continuar do maior ID importado.
                for table in ["genres", "dvds", "playlists", "plays", "license_revenue", "machine_revenue_log", "karaoke_scores"]:
                    seq = f"{table}_id_seq"
                    cur.execute(f"SELECT setval(%s, COALESCE((SELECT MAX(id) FROM {quote_ident(table)}), 1), true)", (seq,))

        print("\nMigração finalizada com sucesso!")
    finally:
        sqlite.close()
        pg.close()


if __name__ == "__main__":
    main()
