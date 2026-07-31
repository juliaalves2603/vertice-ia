from pathlib import Path

p = Path("backend/app.py")

if not p.exists():
    raise RuntimeError("backend/app.py não encontrado.")

s = p.read_text(encoding="utf-8")
Path("backend/app_backup_token_longo_page_token.py").write_text(s, encoding="utf-8")

patch = r'''

# ============================================================
# VÉRTICE IA - TOKEN LONGO + PAGE ACCESS TOKEN
# ============================================================

def _meta_graph_get(path: str, params: dict | None = None):
    import os, requests

    api_version = os.getenv("META_API_VERSION", "v25.0")
    url = f"https://graph.facebook.com/{api_version}/{path.lstrip('/')}"
    params = params or {}

    try:
        r = requests.get(url, params=params, timeout=30)
        data = r.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "message": "Erro ao chamar Graph API.",
            "error": str(e)
        })

    if isinstance(data, dict) and data.get("error"):
        raise HTTPException(status_code=400, detail={
            "message": "Erro retornado pela Meta.",
            "path": path,
            "meta": data
        })

    return data


def _exchange_to_long_lived_token(short_token: str):
    import os, requests

    app_id = os.getenv("META_APP_ID")
    app_secret = os.getenv("META_APP_SECRET")

    if not app_id or not app_secret:
        raise HTTPException(status_code=500, detail="META_APP_ID ou META_APP_SECRET não configurado no .env.")

    url = "https://graph.facebook.com/oauth/access_token"

    params = {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": short_token
    }

    try:
        r = requests.get(url, params=params, timeout=30)
        data = r.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "message": "Erro ao trocar token curto por token longo.",
            "error": str(e)
        })

    if isinstance(data, dict) and data.get("error"):
        raise HTTPException(status_code=400, detail={
            "message": "A Meta recusou a troca do token.",
            "meta": data
        })

    token = data.get("access_token")
    if not token:
        raise HTTPException(status_code=400, detail={
            "message": "A Meta não retornou access_token longo.",
            "response": data
        })

    return {
        "access_token": token,
        "token_type": data.get("token_type"),
        "expires_in": data.get("expires_in")
    }


def _debug_token(token: str):
    import os, requests

    app_id = os.getenv("META_APP_ID")
    app_secret = os.getenv("META_APP_SECRET")

    if not app_id or not app_secret:
        raise HTTPException(status_code=500, detail="META_APP_ID ou META_APP_SECRET não configurado no .env.")

    app_token = f"{app_id}|{app_secret}"

    try:
        r = requests.get(
            "https://graph.facebook.com/debug_token",
            params={
                "input_token": token,
                "access_token": app_token
            },
            timeout=30
        )
        data = r.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "message": "Erro ao validar token.",
            "error": str(e)
        })

    return data


def _ensure_meta_token_columns():
    import sqlite3
    from pathlib import Path

    db_path = Path("backend") / "vertice_ia_limpa.db"
    if not db_path.exists():
        db_path = Path("vertice_ia_limpa.db")

    conn = sqlite3.connect(db_path)
    try:
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        names = {t[0] for t in tables}

        if "meta_connected_accounts" not in names:
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

        existing = conn.execute("PRAGMA table_info(meta_connected_accounts)").fetchall()
        cols = {c[1] for c in existing}

        add_cols = {
            "long_lived_user_token": "TEXT",
            "page_token_status": "TEXT",
            "token_expires_in": "INTEGER",
            "token_checked_at": "TEXT",
            "last_token_error": "TEXT"
        }

        for col, typ in add_cols.items():
            if col not in cols:
                conn.execute(f"ALTER TABLE meta_connected_accounts ADD COLUMN {col} {typ}")

        conn.commit()
    finally:
        conn.close()


@app.post("/api/meta-token/upgrade-connected")
def upgrade_connected_meta_tokens():
    """
    Converte tokens salvos em token longo de usuário,
    busca Page Access Token e salva no banco.
    """
    import sqlite3, datetime
    from pathlib import Path

    _ensure_meta_token_columns()

    db_path = Path("backend") / "vertice_ia_limpa.db"
    if not db_path.exists():
        db_path = Path("vertice_ia_limpa.db")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    resultados = []

    try:
        rows = conn.execute("""
            SELECT *
            FROM meta_connected_accounts
            ORDER BY id DESC
        """).fetchall()

        for row in rows:
            item = dict(row)
            account_id = item.get("id")
            short_or_old_token = item.get("user_access_token") or item.get("long_lived_user_token")

            if not short_or_old_token:
                resultados.append({
                    "id": account_id,
                    "status": "sem_token",
                    "message": "Conta sem user_access_token salvo."
                })
                continue

            try:
                long_data = _exchange_to_long_lived_token(short_or_old_token)
                long_token = long_data["access_token"]

                pages = _meta_graph_get("me/accounts", {
                    "fields": "id,name,access_token,instagram_business_account{id,username}",
                    "access_token": long_token
                })

                page_data = None
                ig_data = None

                for pg in pages.get("data", []):
                    if pg.get("instagram_business_account"):
                        page_data = pg
                        ig_data = pg.get("instagram_business_account")
                        break

                if not page_data and pages.get("data"):
                    page_data = pages["data"][0]
                    ig_data = page_data.get("instagram_business_account")

                if not page_data:
                    raise Exception("Nenhuma Página retornada em /me/accounts.")

                page_token = page_data.get("access_token")
                if not page_token:
                    raise Exception("A Página foi encontrada, mas sem page access token.")

                debug = _debug_token(page_token)
                is_valid = bool(debug.get("data", {}).get("is_valid"))

                now = datetime.datetime.now().isoformat(timespec="seconds")

                conn.execute("""
                    UPDATE meta_connected_accounts
                    SET
                        long_lived_user_token = ?,
                        page_id = COALESCE(?, page_id),
                        page_name = COALESCE(?, page_name),
                        page_access_token = ?,
                        instagram_business_account_id = COALESCE(?, instagram_business_account_id),
                        instagram_username = COALESCE(?, instagram_username),
                        page_token_status = ?,
                        token_expires_in = ?,
                        token_checked_at = ?,
                        last_token_error = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    long_token,
                    page_data.get("id"),
                    page_data.get("name"),
                    page_token,
                    ig_data.get("id") if isinstance(ig_data, dict) else None,
                    ig_data.get("username") if isinstance(ig_data, dict) else None,
                    "ativo" if is_valid else "verificar",
                    long_data.get("expires_in"),
                    now,
                    account_id
                ))

                resultados.append({
                    "id": account_id,
                    "client_name": item.get("client_name"),
                    "status": "atualizado",
                    "page": page_data.get("name"),
                    "page_id": page_data.get("id"),
                    "instagram": ig_data.get("username") if isinstance(ig_data, dict) else None,
                    "page_token_valid": is_valid,
                    "expires_in": long_data.get("expires_in")
                })

            except Exception as e:
                now = datetime.datetime.now().isoformat(timespec="seconds")
                conn.execute("""
                    UPDATE meta_connected_accounts
                    SET
                        page_token_status = ?,
                        token_checked_at = ?,
                        last_token_error = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    "precisa_reconectar",
                    now,
                    str(e),
                    account_id
                ))

                resultados.append({
                    "id": account_id,
                    "client_name": item.get("client_name"),
                    "status": "erro",
                    "message": str(e)
                })

        conn.commit()

    finally:
        conn.close()

    return {
        "ok": True,
        "message": "Processo de upgrade de token executado.",
        "resultados": resultados
    }


@app.get("/api/meta-token/status")
def meta_token_status():
    import sqlite3
    from pathlib import Path

    _ensure_meta_token_columns()

    db_path = Path("backend") / "vertice_ia_limpa.db"
    if not db_path.exists():
        db_path = Path("vertice_ia_limpa.db")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        rows = conn.execute("""
            SELECT
                id,
                client_name,
                page_id,
                page_name,
                instagram_business_account_id,
                instagram_username,
                page_token_status,
                token_expires_in,
                token_checked_at,
                last_token_error,
                created_at,
                updated_at
            FROM meta_connected_accounts
            ORDER BY id DESC
        """).fetchall()

        data = []
        for r in rows:
            item = dict(r)
            item["has_page_access_token"] = False
            data.append(item)

        return {
            "ok": True,
            "accounts": data
        }

    finally:
        conn.close()


@app.post("/api/meta-token/check")
def check_connected_meta_tokens():
    import sqlite3, datetime
    from pathlib import Path

    _ensure_meta_token_columns()

    db_path = Path("backend") / "vertice_ia_limpa.db"
    if not db_path.exists():
        db_path = Path("vertice_ia_limpa.db")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    resultados = []

    try:
        rows = conn.execute("""
            SELECT id, client_name, page_access_token
            FROM meta_connected_accounts
            ORDER BY id DESC
        """).fetchall()

        for row in rows:
            token = row["page_access_token"]
            now = datetime.datetime.now().isoformat(timespec="seconds")

            if not token:
                conn.execute("""
                    UPDATE meta_connected_accounts
                    SET page_token_status = ?, token_checked_at = ?, last_token_error = ?
                    WHERE id = ?
                """, ("precisa_reconectar", now, "Sem Page Access Token salvo.", row["id"]))

                resultados.append({
                    "id": row["id"],
                    "client_name": row["client_name"],
                    "status": "precisa_reconectar",
                    "message": "Sem Page Access Token salvo."
                })
                continue

            debug = _debug_token(token)
            is_valid = bool(debug.get("data", {}).get("is_valid"))

            status = "ativo" if is_valid else "precisa_reconectar"
            error_msg = None if is_valid else str(debug)

            conn.execute("""
                UPDATE meta_connected_accounts
                SET page_token_status = ?, token_checked_at = ?, last_token_error = ?
                WHERE id = ?
            """, (status, now, error_msg, row["id"]))

            resultados.append({
                "id": row["id"],
                "client_name": row["client_name"],
                "status": status,
                "debug": debug.get("data", {})
            })

        conn.commit()

    finally:
        conn.close()

    return {
        "ok": True,
        "message": "Verificação de tokens concluída.",
        "resultados": resultados
    }

# ============================================================
# FIM - TOKEN LONGO + PAGE ACCESS TOKEN
# ============================================================

'''

if "VÉRTICE IA - TOKEN LONGO + PAGE ACCESS TOKEN" not in s:
    s = s + patch

p.write_text(s, encoding="utf-8")

print("Patch de token longo instalado no backend.")
