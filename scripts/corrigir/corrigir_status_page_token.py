from pathlib import Path
import re

p = Path("backend/app.py")

if not p.exists():
    raise RuntimeError("backend/app.py não encontrado.")

s = p.read_text(encoding="utf-8")
Path("backend/app_backup_corrigir_has_page_access_token.py").write_text(s, encoding="utf-8")

# Corrige SELECT do endpoint /api/meta-token/status para incluir page_access_token internamente
s = s.replace(
'''SELECT
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
            FROM meta_connected_accounts''',
'''SELECT
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
                updated_at,
                page_access_token
            FROM meta_connected_accounts'''
)

# Troca o bloco que sempre colocava False
s = s.replace(
'''item = dict(r)
            item["has_page_access_token"] = False
            data.append(item)''',
'''item = dict(r)
            token = item.pop("page_access_token", None)
            item["has_page_access_token"] = bool(token)
            data.append(item)'''
)

p.write_text(s, encoding="utf-8")

print("Status do Page Access Token corrigido sem expor o token.")
