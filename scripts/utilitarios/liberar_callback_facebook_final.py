from pathlib import Path
import re

p = Path("backend/app.py")
s = p.read_text(encoding="utf-8")

Path("backend/app_backup_liberar_callback_facebook_final.py").write_text(s, encoding="utf-8")

PUBLIC_PATHS = [
    "/api/facebook-login/callback",
    "/api/facebook-login/config",
    "/favicon.ico"
]

# Adiciona uma proteção no início de qualquer middleware de auth que use request.url.path
# sem depender do nome exato da lista pública existente.
insert = '''
    if request.url.path in [
        "/api/facebook-login/callback",
        "/api/facebook-login/config",
        "/favicon.ico"
    ]:
        return await call_next(request)
'''

if '"/api/facebook-login/callback"' not in s:
    s = s.replace(
        'if request.url.path in [',
        'if request.url.path in [\n        "/api/facebook-login/callback",\n        "/api/facebook-login/config",',
        1
    )

# Caso o middleware não use lista simples, injeta o bypass depois da assinatura do middleware.
if "/api/facebook-login/callback" not in s or "return await call_next(request)" not in s:
    s = s.replace(
        "async def",
        "async def",
        1
    )

# Correção mais direta: em qualquer middleware com call_next, insere bypass se ainda não estiver próximo.
if "@app.middleware" in s and '"/api/facebook-login/callback"' not in s[s.find("@app.middleware"):s.find("@app.middleware")+1200]:
    m = re.search(r'(@app\.middleware\("http"\)\s*\nasync def [^\n]+\n)', s)
    if m:
        pos = m.end()
        s = s[:pos] + insert + s[pos:]

p.write_text(s, encoding="utf-8")

print("Callback público conferido/adicionado.")
