from pathlib import Path
import re

REDIRECT = "https://generally-vertical-green-doctrine.trycloudflare.com/api/facebook-login/callback"

# 1. Corrige .env
env_path = Path("backend/.env")
env_lines = env_path.read_text(encoding="utf-8").splitlines()

new_env = []

for line in env_lines:
    if not line.strip().startswith("META_REDIRECT_URI="):
        new_env.append(line)

new_env.append(f"META_REDIRECT_URI={REDIRECT}")

env_path.write_text("\n".join(new_env) + "\n", encoding="utf-8")


# 2. Corrige app.py removendo TODAS as funções _meta_redirect_uri existentes
app_path = Path("backend/app.py")
s = app_path.read_text(encoding="utf-8")

Path("backend/app_backup_redirect_definitivo.py").write_text(s, encoding="utf-8")

new_func = f'''
def _meta_redirect_uri():
    return "{REDIRECT}"
'''

# Remove qualquer definição existente de _meta_redirect_uri até a próxima função def _meta_login_scopes
pattern = r'def _meta_redirect_uri\(\):[\s\S]*?(?=\ndef _meta_login_scopes\(\):)'

matches = re.findall(pattern, s)

if matches:
    s = re.sub(pattern, new_func.strip() + "\n", s)
else:
    # Se não encontrar pelo padrão principal, insere antes de _meta_login_scopes
    if "def _meta_login_scopes():" in s:
        s = s.replace("def _meta_login_scopes():", new_func.strip() + "\n\ndef _meta_login_scopes():", 1)
    else:
        raise RuntimeError("Não encontrei ponto seguro para inserir _meta_redirect_uri.")

# 3. Garante que não sobrou redirect antigo hardcoded no login
s = s.replace(
    "http://127.0.0.1:8000/api/facebook-login/callback",
    REDIRECT
)

app_path.write_text(s, encoding="utf-8")

print("Redirect definitivo aplicado:")
print(REDIRECT)
print()
print("Quantidade de _meta_redirect_uri no app.py:", s.count("def _meta_redirect_uri():"))
print("Ainda existe 127 no app.py?", "http://127.0.0.1:8000/api/facebook-login/callback" in s)
