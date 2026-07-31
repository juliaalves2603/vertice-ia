from pathlib import Path
import re

REDIRECT = "https://appverticeia.com.br/api/facebook-login/callback"

# =========================
# 1. Corrigir .env
# =========================
env_path = Path("backend/.env")

if not env_path.exists():
    raise RuntimeError("Arquivo backend/.env não encontrado.")

env_text = env_path.read_text(encoding="utf-8")

Path("backend/.env_backup_redirect_final").write_text(env_text, encoding="utf-8")

env_lines = []
for line in env_text.splitlines():
    if not line.strip().startswith("META_REDIRECT_URI="):
        env_lines.append(line)

env_lines.append(f"META_REDIRECT_URI={REDIRECT}")

env_path.write_text("\n".join(env_lines) + "\n", encoding="utf-8")


# =========================
# 2. Corrigir app.py
# =========================
app_path = Path("backend/app.py")

if not app_path.exists():
    raise RuntimeError("Arquivo backend/app.py não encontrado.")

s = app_path.read_text(encoding="utf-8")

Path("backend/app_backup_redirect_final_limpo.py").write_text(s, encoding="utf-8")

# Troca qualquer callback antigo no código inteiro
s = re.sub(
    r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com/api/facebook-login/callback",
    REDIRECT,
    s
)

s = s.replace(
    "http://127.0.0.1:8000/api/facebook-login/callback",
    REDIRECT
)

# Remove qualquer função _meta_redirect_uri existente antes de _meta_login_scopes
s = re.sub(
    r"\ndef _meta_redirect_uri\(\):[\s\S]*?(?=\ndef _meta_login_scopes\(\):)",
    "\n",
    s
)

new_func = f'''
def _meta_redirect_uri():
    return "{REDIRECT}"
'''

if "def _meta_login_scopes():" in s:
    s = s.replace(
        "def _meta_login_scopes():",
        new_func.strip() + "\n\ndef _meta_login_scopes():",
        1
    )
else:
    raise RuntimeError("Não encontrei def _meta_login_scopes() no app.py")

app_path.write_text(s, encoding="utf-8")


# =========================
# 3. Diagnóstico final
# =========================
env_final = env_path.read_text(encoding="utf-8")
app_final = app_path.read_text(encoding="utf-8")

print("REDIRECT CONFIGURADO:")
print(REDIRECT)
print()
print("Quantidade de META_REDIRECT_URI no .env:", env_final.count("META_REDIRECT_URI="))
print("Quantidade de def _meta_redirect_uri no app.py:", app_final.count("def _meta_redirect_uri():"))
print("Ainda existe 127 no .env?", "127.0.0.1:8000/api/facebook-login/callback" in env_final)
print("Ainda existe 127 no app.py?", "127.0.0.1:8000/api/facebook-login/callback" in app_final)
print("Ainda existe trycloudflare no app.py?", "trycloudflare.com/api/facebook-login/callback" in app_final)
