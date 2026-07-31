from pathlib import Path
import re

# Corrige .env
env_path = Path("backend/.env")
env = env_path.read_text(encoding="utf-8").splitlines()

novo_redirect = "https://generally-vertical-green-doctrine.trycloudflare.com/api/facebook-login/callback"

linhas = []
for line in env:
    if not line.strip().startswith("META_REDIRECT_URI="):
        linhas.append(line)

linhas.append(f"META_REDIRECT_URI={novo_redirect}")

env_path.write_text("\n".join(linhas) + "\n", encoding="utf-8")


# Corrige backend para ler direto do .env
app_path = Path("backend/app.py")
s = app_path.read_text(encoding="utf-8")

Path("backend/app_backup_corrigir_redirect_env_direto.py").write_text(s, encoding="utf-8")

new_func = r'''
def _meta_redirect_uri():
    env_file = Path(__file__).resolve().parent / ".env"

    if env_file.exists():
        try:
            for raw in env_file.read_text(encoding="utf-8").splitlines():
                line = raw.strip()

                if line.startswith("META_REDIRECT_URI="):
                    value = line.split("=", 1)[1].strip().strip('"').strip("'")

                    if value:
                        return value
        except Exception:
            pass

    return os.getenv(
        "META_REDIRECT_URI",
        "http://127.0.0.1:8000/api/facebook-login/callback"
    ).strip()
'''

pattern = r'def _meta_redirect_uri\(\):[\s\S]*?def _meta_login_scopes\(\):'

if re.search(pattern, s):
    s = re.sub(
        pattern,
        new_func.strip() + "\n\ndef _meta_login_scopes():",
        s,
        count=1
    )
else:
    raise RuntimeError("Não encontrei a função _meta_redirect_uri no backend/app.py")

app_path.write_text(s, encoding="utf-8")

print("Redirect URI corrigido para:")
print(novo_redirect)
print("Backend ajustado para ler META_REDIRECT_URI direto do backend/.env")
