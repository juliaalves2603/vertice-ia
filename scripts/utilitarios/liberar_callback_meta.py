from pathlib import Path

p = Path("backend/app.py")
s = p.read_text(encoding="utf-8")

Path("backend/app_backup_liberar_callback_meta.py").write_text(s, encoding="utf-8")

# Tenta adicionar o callback nas listas de rotas públicas já existentes
public_paths = [
    '"/api/facebook-login/callback"',
    '"/api/facebook-login/config"'
]

for item in public_paths:
    if item not in s:
        # Caso exista alguma lista com /login e /api/login, adiciona perto dela
        s = s.replace('"/api/login"', '"/api/login",\n        ' + item, 1)

p.write_text(s, encoding="utf-8")

print("Callback da Meta liberado nas rotas públicas quando houver lista de autenticação.")
