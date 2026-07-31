import sqlite3
from pathlib import Path

db = Path("backend/vertice_ia_limpa.db")

if not db.exists():
    raise RuntimeError("Banco não encontrado: backend/vertice_ia_limpa.db")

backup = Path("backend/vertice_ia_limpa_backup_corrigir_colunas_meta_token.db")
backup.write_bytes(db.read_bytes())

conn = sqlite3.connect(db)

try:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS meta_connected_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT,
            user_id TEXT,
            user_name TEXT,
            user_access_token TEXT,
            page_id TEXT,
            page_name TEXT,
            page_access_token TEXT,
            instagram_business_account_id TEXT,
            instagram_username TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cols = conn.execute("PRAGMA table_info(meta_connected_accounts)").fetchall()
    existing = {c[1] for c in cols}

    required_cols = {
        "client_name": "TEXT",
        "user_id": "TEXT",
        "user_name": "TEXT",
        "user_access_token": "TEXT",
        "page_id": "TEXT",
        "page_name": "TEXT",
        "page_access_token": "TEXT",
        "instagram_business_account_id": "TEXT",
        "instagram_username": "TEXT",
        "long_lived_user_token": "TEXT",
        "page_token_status": "TEXT",
        "token_expires_in": "INTEGER",
        "token_checked_at": "TEXT",
        "last_token_error": "TEXT",
        "created_at": "TEXT",
        "updated_at": "TEXT"
    }

    for col, typ in required_cols.items():
        if col not in existing:
            print("Criando coluna:", col)
            conn.execute(f"ALTER TABLE meta_connected_accounts ADD COLUMN {col} {typ}")

    conn.commit()

    cols_after = conn.execute("PRAGMA table_info(meta_connected_accounts)").fetchall()
    print("\nColunas atuais:")
    for c in cols_after:
        print("-", c[1])

    print("\nBanco corrigido com sucesso.")
    print("Backup criado em:", backup)

finally:
    conn.close()
