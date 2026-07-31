import sqlite3
from pathlib import Path

db = Path("backend/vertice_ia_limpa.db")

if not db.exists():
    raise RuntimeError("Banco não encontrado: backend/vertice_ia_limpa.db")

conn = sqlite3.connect(db)

try:
    existe = conn.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='meta_connected_accounts'
    """).fetchone()

    if not existe:
        print("Tabela meta_connected_accounts não existe. Nada para limpar.")
    else:
        qtd = conn.execute("SELECT COUNT(*) FROM meta_connected_accounts").fetchone()[0]
        print("Conexões Meta encontradas:", qtd)

        conn.execute("DELETE FROM meta_connected_accounts")
        conn.commit()

        print("Conexões Meta inválidas removidas com sucesso.")

finally:
    conn.close()
