from pathlib import Path
import re

REDIRECT = "https://appverticeia.com.br/api/facebook-login/callback"
BASE_URL = "https://appverticeia.com.br"

app_path = Path("backend/app.py")
env_path = Path("backend/.env")

if not app_path.exists():
    raise RuntimeError("backend/app.py não encontrado.")

if not env_path.exists():
    raise RuntimeError("backend/.env não encontrado.")

# Backup
Path("backend/app_backup_forcar_redirect_oauth_final.py").write_text(
    app_path.read_text(encoding="utf-8"),
    encoding="utf-8"
)

Path("backend/.env_backup_forcar_redirect_oauth_final").write_text(
    env_path.read_text(encoding="utf-8"),
    encoding="utf-8"
)

# 1. Corrige .env
env_lines = []
for line in env_path.read_text(encoding="utf-8").splitlines():
    if not line.strip().startswith("META_REDIRECT_URI="):
        env_lines.append(line)

env_lines.append(f"META_REDIRECT_URI={REDIRECT}")
env_path.write_text("\n".join(env_lines) + "\n", encoding="utf-8")


# 2. Corrige app.py
s = app_path.read_text(encoding="utf-8")

# Remove callbacks antigos no arquivo inteiro
s = s.replace("http://127.0.0.1:8000/api/facebook-login/callback", REDIRECT)
s = re.sub(
    r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com/api/facebook-login/callback",
    REDIRECT,
    s
)

# Adiciona constante global
if "VERTICE_META_REDIRECT_FINAL" not in s:
    s = s.replace(
        "# ==============================",
        f'VERTICE_META_REDIRECT_FINAL = "{REDIRECT}"\nVERTICE_META_BASE_URL_FINAL = "{BASE_URL}"\n\n# ==============================',
        1
    )

# Remove todas as funções _meta_redirect_uri antigas
s = re.sub(
    r"\ndef _meta_redirect_uri\(\):[\s\S]*?(?=\ndef |\n@app\.|$)",
    "\n",
    s
)

# Insere função definitiva antes de _meta_login_scopes
new_redirect_func = '''
def _meta_redirect_uri():
    return VERTICE_META_REDIRECT_FINAL

'''

if "def _meta_login_scopes():" in s:
    s = s.replace("def _meta_login_scopes():", new_redirect_func + "def _meta_login_scopes():", 1)
else:
    raise RuntimeError("Não encontrei def _meta_login_scopes() no app.py")


# Força a função /api/facebook-login/start a usar redirect final,
# mesmo se algum trecho interno tentar sobrescrever.
needle = 'login_url = f"https://www.facebook.com/{version}/dialog/oauth?" + urllib.parse.urlencode(params)'

if needle in s and "params[\"redirect_uri\"] = VERTICE_META_REDIRECT_FINAL" not in s:
    s = s.replace(
        needle,
        '    params["redirect_uri"] = VERTICE_META_REDIRECT_FINAL\n    ' + needle,
        1
    )
elif needle not in s:
    print("Aviso: não encontrei a linha login_url exata. Vamos diagnosticar depois.")


# Adiciona endpoint de diagnóstico
debug_endpoint = '''
@app.get("/api/facebook-login/debug-redirect")
def api_facebook_login_debug_redirect():
    return {
        "status": "sucesso",
        "running_file": __file__,
        "redirect_function": _meta_redirect_uri(),
        "redirect_final_constant": VERTICE_META_REDIRECT_FINAL,
        "env_redirect": os.getenv("META_REDIRECT_URI", ""),
        "base_url": VERTICE_META_BASE_URL_FINAL
    }

'''

if "/api/facebook-login/debug-redirect" not in s:
    marker = '@app.get("/api/facebook-login/start")'
    if marker in s:
        s = s.replace(marker, debug_endpoint + marker, 1)
    else:
        raise RuntimeError("Não encontrei /api/facebook-login/start para inserir debug.")


app_path.write_text(s, encoding="utf-8")


# Diagnóstico local no arquivo
final_app = app_path.read_text(encoding="utf-8")
final_env = env_path.read_text(encoding="utf-8")

print("CORREÇÃO APLICADA")
print("Redirect final:", REDIRECT)
print()
print("No .env:")
print("META_REDIRECT_URI count:", final_env.count("META_REDIRECT_URI="))
print("Existe 127 no .env?", "127.0.0.1:8000/api/facebook-login/callback" in final_env)
print()
print("No app.py:")
print("def _meta_redirect_uri count:", final_app.count("def _meta_redirect_uri():"))
print("Existe 127 no app.py?", "127.0.0.1:8000/api/facebook-login/callback" in final_app)
print("Existe trycloudflare no app.py?", "trycloudflare.com/api/facebook-login/callback" in final_app)
print("Forçou params redirect?", 'params["redirect_uri"] = VERTICE_META_REDIRECT_FINAL' in final_app)
print("Debug endpoint existe?", "/api/facebook-login/debug-redirect" in final_app)
