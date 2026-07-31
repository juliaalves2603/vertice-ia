from pathlib import Path
import re

REDIRECT = "https://appverticeia.com.br/api/facebook-login/callback"

app_path = Path("backend/app.py")
env_path = Path("backend/.env")

if not app_path.exists():
    raise RuntimeError("backend/app.py não encontrado.")

if not env_path.exists():
    raise RuntimeError("backend/.env não encontrado.")

# Backup
Path("backend/app_backup_corrigir_indentation_facebook.py").write_text(
    app_path.read_text(encoding="utf-8"),
    encoding="utf-8"
)

Path("backend/.env_backup_corrigir_indentation_facebook").write_text(
    env_path.read_text(encoding="utf-8"),
    encoding="utf-8"
)

# =========================
# Corrige .env
# =========================
env_lines = []

for line in env_path.read_text(encoding="utf-8").splitlines():
    if not line.strip().startswith("META_REDIRECT_URI="):
        env_lines.append(line)

env_lines.append(f"META_REDIRECT_URI={REDIRECT}")
env_path.write_text("\n".join(env_lines) + "\n", encoding="utf-8")


# =========================
# Corrige app.py
# =========================
s = app_path.read_text(encoding="utf-8")

# Garante constantes corretas
if "VERTICE_META_REDIRECT_FINAL" in s:
    s = re.sub(
        r'VERTICE_META_REDIRECT_FINAL\s*=\s*"[^"]*"',
        f'VERTICE_META_REDIRECT_FINAL = "{REDIRECT}"',
        s
    )
else:
    s = f'VERTICE_META_REDIRECT_FINAL = "{REDIRECT}"\n' + s

# Troca redirects antigos no arquivo inteiro
s = s.replace(
    "http://127.0.0.1:8000/api/facebook-login/callback",
    REDIRECT
)

s = re.sub(
    r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com/api/facebook-login/callback",
    REDIRECT,
    s
)

# Remove funções antigas de redirect
s = re.sub(
    r"\ndef _meta_redirect_uri\(\):[\s\S]*?(?=\ndef |\n@app\.|$)",
    "\n",
    s
)

# Reinsere função limpa antes de _meta_login_scopes
redirect_func = f'''
def _meta_redirect_uri():
    return "{REDIRECT}"

'''

if "def _meta_login_scopes():" not in s:
    raise RuntimeError("Não encontrei def _meta_login_scopes() no app.py.")

s = s.replace(
    "def _meta_login_scopes():",
    redirect_func + "def _meta_login_scopes():",
    1
)

# Substitui a função inteira /api/facebook-login/start por uma versão limpa
start_marker = '@app.get("/api/facebook-login/start")'
callback_marker = '@app.get("/api/facebook-login/callback")'

start = s.find(start_marker)
end = s.find(callback_marker)

if start == -1:
    raise RuntimeError("Não encontrei @app.get('/api/facebook-login/start').")

if end == -1:
    raise RuntimeError("Não encontrei @app.get('/api/facebook-login/callback').")

clean_start_function = f'''
@app.get("/api/facebook-login/start")
def api_facebook_login_start(client_name: str = ""):
    _ensure_meta_client_tables()
    _meta_require_config()

    client_name = (client_name or "").strip()
    state = secrets.token_urlsafe(32)

    db = _meta_client_db_path()
    conn = sqlite3.connect(db)

    try:
        conn.execute(
            "INSERT INTO meta_oauth_states (state, client_name) VALUES (?, ?)",
            (state, client_name)
        )
        conn.commit()
    finally:
        conn.close()

    version = _meta_version()

    params = {{
        "client_id": _meta_app_id(),
        "redirect_uri": "{REDIRECT}",
        "state": state,
        "response_type": "code",
        "scope": _meta_login_scopes()
    }}

    login_url = f"https://www.facebook.com/{{version}}/dialog/oauth?" + urllib.parse.urlencode(params)

    return {{
        "status": "sucesso",
        "login_url": login_url,
        "redirect_uri": "{REDIRECT}",
        "scopes": _meta_login_scopes()
    }}

'''

s = s[:start] + clean_start_function + "\n" + s[end:]

# Adiciona endpoint de diagnóstico limpo, se ainda não existir
debug_endpoint = f'''
@app.get("/api/facebook-login/debug-redirect")
def api_facebook_login_debug_redirect():
    return {{
        "status": "sucesso",
        "running_file": __file__,
        "redirect": "{REDIRECT}",
        "redirect_function": _meta_redirect_uri(),
        "env_redirect": os.getenv("META_REDIRECT_URI", "")
    }}

'''

if "/api/facebook-login/debug-redirect" not in s:
    s = s.replace(start_marker, debug_endpoint + start_marker, 1)

app_path.write_text(s, encoding="utf-8")


# Diagnóstico local
final_app = app_path.read_text(encoding="utf-8")
final_env = env_path.read_text(encoding="utf-8")

print("Correção aplicada.")
print("Redirect final:", REDIRECT)
print("META_REDIRECT_URI no .env:", final_env.count("META_REDIRECT_URI="))
print("def _meta_redirect_uri no app.py:", final_app.count("def _meta_redirect_uri():"))
print("Existe 127 no app.py?", "127.0.0.1:8000/api/facebook-login/callback" in final_app)
print("Existe trycloudflare no app.py?", "trycloudflare.com/api/facebook-login/callback" in final_app)
