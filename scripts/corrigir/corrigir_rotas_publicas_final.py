from pathlib import Path

p = Path("backend/app.py")

if not p.exists():
    raise RuntimeError("backend/app.py não encontrado.")

s = p.read_text(encoding="utf-8")

Path("backend/app_backup_liberar_rotas_publicas_final.py").write_text(s, encoding="utf-8")

old = 'if path in ["/login", "/api/login", "/favicon.ico"]:'

new = '''if path in [
        "/",
        "/login",
        "/api/login",
        "/api/logout",
        "/api/status",
        "/api/facebook-login/config",
        "/api/facebook-login/callback",
        "/favicon.ico"
    ]:'''

if old not in s:
    raise RuntimeError("Não encontrei a linha exata para substituir.")

s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")

print("Rotas públicas liberadas com sucesso.")
print("api/status liberado?", '"/api/status"' in s)
print("callback Facebook liberado?", '"/api/facebook-login/callback"' in s)
