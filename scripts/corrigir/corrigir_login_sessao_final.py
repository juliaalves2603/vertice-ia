from pathlib import Path

p = Path("backend/app.py")

if not p.exists():
    raise RuntimeError("backend/app.py não encontrado.")

s = p.read_text(encoding="utf-8")

Path("backend/app_backup_corrigir_login_sessao_final.py").write_text(s, encoding="utf-8")

marker = "if _vertice_logged(request):"
idx = s.find(marker)

if idx == -1:
    raise RuntimeError("Não encontrei if _vertice_logged(request).")

start = s.rfind("if path in [", 0, idx)

if start == -1:
    raise RuntimeError("Não encontrei bloco de rotas públicas antes do login.")

ret = "return await call_next(request)"
end = s.find(ret, start)

if end == -1:
    raise RuntimeError("Não encontrei return await call_next(request) no bloco público.")

end = end + len(ret)

new_block = '''if path in [
        "/login",
        "/api/login",
        "/api/logout",
        "/api/status",
        "/api/session-check",
        "/api/facebook-login/config",
        "/api/facebook-login/callback",
        "/favicon.ico"
    ]:
        return await call_next(request)'''

s = s[:start] + new_block + s[end:]

session_endpoint = '''
@app.get("/api/session-check")
def api_session_check(request: Request):
    return {
        "logged": _vertice_logged(request),
        "cookies": list(request.cookies.keys()),
        "status": "ok"
    }

'''

if "/api/session-check" not in s[s.find("@app.get"):]:
    insert_pos = s.find("VERTICE_LOGIN_HTML")
    if insert_pos == -1:
        raise RuntimeError("Não encontrei VERTICE_LOGIN_HTML para inserir session-check.")
    s = s[:insert_pos] + session_endpoint + s[insert_pos:]

p.write_text(s, encoding="utf-8")

print("Correção aplicada.")
print("Painel / protegido?", '"/",' not in new_block)
print("/api/status público?", '"/api/status"' in new_block)
print("/api/session-check público?", '"/api/session-check"' in new_block)
