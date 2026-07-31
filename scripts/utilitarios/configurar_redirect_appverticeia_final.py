from pathlib import Path
import re

REDIRECT = "https://appverticeia.com.br/api/facebook-login/callback"

env_path = Path("backend/.env")
lines = env_path.read_text(encoding="utf-8").splitlines()

new_lines = []
for line in lines:
    if not line.strip().startswith("META_REDIRECT_URI="):
        new_lines.append(line)

new_lines.append(f"META_REDIRECT_URI={REDIRECT}")
env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

app_path = Path("backend/app.py")
s = app_path.read_text(encoding="utf-8")

Path("backend/app_backup_redirect_appverticeia_final.py").write_text(s, encoding="utf-8")

s = re.sub(
    r'https://[a-z0-9\-]+\.trycloudflare\.com/api/facebook-login/callback',
    REDIRECT,
    s
)

s = s.replace(
    "http://127.0.0.1:8000/api/facebook-login/callback",
    REDIRECT
)

pattern = r'def _meta_redirect_uri\(\):[\s\S]*?(?=\ndef _meta_login_scopes\(\):)'

new_func = f'''
def _meta_redirect_uri():
    return "{REDIRECT}"
'''

if re.search(pattern, s):
    s = re.sub(pattern, new_func.strip() + "\n", s, count=1)
elif "def _meta_login_scopes():" in s:
    s = s.replace("def _meta_login_scopes():", new_func.strip() + "\n\ndef _meta_login_scopes():", 1)

app_path.write_text(s, encoding="utf-8")

print("Redirect final configurado:")
print(REDIRECT)
print("Ainda existe trycloudflare?", "trycloudflare.com" in s)
print("Ainda existe 127 no callback?", "127.0.0.1:8000/api/facebook-login/callback" in s)
