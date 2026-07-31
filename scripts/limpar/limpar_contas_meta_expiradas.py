import sqlite3
from pathlib import Path

db = Path("backend/vertice_ia_limpa.db")

if not db.exists():
    raise RuntimeError("Banco não encontrado: backend/vertice_ia_limpa.db")

conn = sqlite3.connect(db)

try:
    tabelas = conn.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table'
        ORDER BY name
    """).fetchall()

    print("Tabelas encontradas:")
    for t in tabelas:
        print("-", t[0])

    if conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='meta_connected_accounts'").fetchone():
        qtd = conn.execute("SELECT COUNT(*) FROM meta_connected_accounts").fetchone()[0]
        print("Contas conectadas antigas:", qtd)

        conn.execute("DELETE FROM meta_connected_accounts")
        conn.commit()

        print("Contas Meta conectadas antigas removidas com sucesso.")
    else:
        print("Tabela meta_connected_accounts não encontrada.")
finally:
    conn.close()
