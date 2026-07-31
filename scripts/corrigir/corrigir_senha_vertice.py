from pathlib import Path

p = Path("backend/app.py")
s = p.read_text(encoding="utf-8")

# imports
if "import base64" not in s:
    s = s.replace("import os, json, sqlite3", "import os, json, sqlite3, base64, secrets")

if "Request" not in s:
    s = s.replace(
        "from fastapi import FastAPI, HTTPException, Query",
        "from fastapi import FastAPI, HTTPException, Query, Request"
    )

if "Response" not in s:
    s = s.replace(
        "from fastapi.responses import HTMLResponse",
        "from fastapi.responses import HTMLResponse, Response"
    )

auth_code = r'''

# ==============================
# PROTEÇÃO POR SENHA - VÉRTICE IA
# ==============================

VERTICE_AUTH_ENABLED = os.getenv("VERTICE_AUTH_ENABLED", "false").lower() == "true"
VERTICE_USER = os.getenv("VERTICE_USER", "vertice").strip()
VERTICE_PASSWORD = os.getenv("VERTICE_PASSWORD", "").strip()

def _vertice_auth_required():
    return Response(
        "Acesso restrito - VERTICE IA",
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="VERTICE IA"'}
    )

@app.middleware("http")
async def vertice_basic_auth(request: Request, call_next):
    if not VERTICE_AUTH_ENABLED:
        return await call_next(request)

    if request.method == "OPTIONS":
        return await call_next(request)

    auth = request.headers.get("authorization", "")

    if not auth.startswith("Basic "):
        return _vertice_auth_required()

    try:
        raw = base64.b64decode(auth.split(" ", 1)[1]).decode("utf-8")
        user, password = raw.split(":", 1)
    except Exception:
        return _vertice_auth_required()

    if secrets.compare_digest(user, VERTICE_USER) and secrets.compare_digest(password, VERTICE_PASSWORD):
        return await call_next(request)

    return _vertice_auth_required()
'''

# remove bloco antigo, se existir incompleto
start_marker = "# ==============================\n# PROTEÇÃO POR SENHA - VÉRTICE IA"
if start_marker in s:
    s = s.split(start_marker)[0] + s.split(start_marker, 1)[1].split("@app.get", 1)[0].replace(s.split(start_marker, 1)[1].split("@app.get", 1)[0], "") + "@app.get" + s.split("@app.get", 1)[1]

# insere antes da primeira rota
if "async def vertice_basic_auth" not in s:
    s = s.replace("@app.get", auth_code + "\n@app.get", 1)

p.write_text(s, encoding="utf-8")

print("Senha aplicada com sucesso.")
print("Usuario: vertice")
print("Senha: 262817")
