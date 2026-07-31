from pathlib import Path
import re

app = Path("backend/app.py")

if not app.exists():
    raise RuntimeError("backend/app.py não encontrado.")

s = app.read_text(encoding="utf-8")

Path("backend/app_backup_liberar_status_backend.py").write_text(s, encoding="utf-8")

public_block_marker = "__VERTICE_PUBLIC_LOAD_ROUTES__"

if public_block_marker not in s:
    pattern = r'(@app\.middleware\("http"\)\s*\nasync def\s+\w+\((\w+)\s*,\s*(\w+)\)\s*:\s*\n)'
    m = re.search(pattern, s)

    if not m:
        raise RuntimeError("Não encontrei o middleware de autenticação. Procure por Acesso não autorizado no app.py.")

    request_name = m.group(2)
    call_next_name = m.group(3)

    insert = f'''    # {public_block_marker}
    if {request_name}.url.path in [
        "/",
        "/login",
        "/api/login",
        "/api/logout",
        "/api/status",
        "/api/facebook-login/config",
        "/api/facebook-login/callback",
        "/favicon.ico"
    ] or {request_name}.url.path.startswith("/static"):
        return await {call_next_name}({request_name})

'''

    s = s[:m.end()] + insert + s[m.end():]

app.write_text(s, encoding="utf-8")

print("Rotas públicas de carregamento liberadas.")
print("Status liberado?", '"/api/status"' in s)
print("Facebook config liberado?", '"/api/facebook-login/config"' in s)
print("Callback liberado?", '"/api/facebook-login/callback"' in s)
