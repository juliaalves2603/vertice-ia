from pathlib import Path
import re

p = Path("backend/app.py")
s = p.read_text(encoding="utf-8")

# Backup antes da correção
Path("backend/app_backup_remover_caixa_navegador.py").write_text(s, encoding="utf-8")

# Remove qualquer middleware que use Basic Auth / WWW-Authenticate
pattern = r'\n@app\.middleware\("http"\)\s*\nasync def ([a-zA-Z0-9_]+)\([^)]*\):[\s\S]*?(?=\n@app\.middleware|\n@app\.get|\n@app\.post|\n@app\.put|\n@app\.delete|\napp\.mount|\ndef |\nclass |\Z)'

def remover_basic_auth(match):
    bloco = match.group(0)
    if (
        "WWW-Authenticate" in bloco
        or "Basic " in bloco
        or "Basic realm" in bloco
        or "authorization" in bloco.lower() and "basic" in bloco.lower()
        or match.group(1) == "vertice_basic_auth"
    ):
        return "\n"
    return bloco

s = re.sub(pattern, remover_basic_auth, s)

# Remove funções antigas que geravam a caixa do navegador
s = re.sub(
    r'\ndef _auth_required\([\s\S]*?(?=\ndef |\n@app\.|\nclass |\Z)',
    '\n',
    s
)

s = re.sub(
    r'\ndef _vertice_auth_required\([\s\S]*?(?=\ndef |\n@app\.|\nclass |\Z)',
    '\n',
    s
)

# Remove sobras de WWW-Authenticate
s = s.replace('headers={"WWW-Authenticate": \'Basic realm="VERTICE IA"\'}', '')
s = s.replace('headers={"WWW-Authenticate": \'Basic realm="VÉRTICE IA"\'}', '')
s = s.replace('"WWW-Authenticate"', '"REMOVIDO"')

# Garante imports do login visual
if "import hmac" not in s:
    s = s.replace("import requests", "import hmac, hashlib\nimport requests")

m = re.search(r"from fastapi import ([^\n]+)", s)
if m:
    nomes = [x.strip() for x in m.group(1).split(",")]
    if "Request" not in nomes:
        nomes.append("Request")
    s = s[:m.start()] + "from fastapi import " + ", ".join(nomes) + s[m.end():]

m = re.search(r"from fastapi\.responses import ([^\n]+)", s)
if m:
    nomes = [x.strip() for x in m.group(1).split(",")]
    for nome in ["HTMLResponse", "JSONResponse", "RedirectResponse"]:
        if nome not in nomes:
            nomes.append(nome)
    s = s[:m.start()] + "from fastapi.responses import " + ", ".join(nomes) + s[m.end():]

# Login visual, caso ainda não exista
login_code = r'''
# ==============================
# LOGIN VISUAL - VÉRTICE IA
# ==============================

VERTICE_AUTH_ENABLED = os.getenv("VERTICE_AUTH_ENABLED", "false").lower() == "true"
VERTICE_USER = os.getenv("VERTICE_USER", "vertice").strip()
VERTICE_PASSWORD = os.getenv("VERTICE_PASSWORD", "").strip()
VERTICE_SESSION_SECRET = os.getenv("VERTICE_SESSION_SECRET", VERTICE_PASSWORD + "_VERTICE_IA").strip()

def _vertice_token():
    return hmac.new(
        VERTICE_SESSION_SECRET.encode("utf-8"),
        b"VERTICE_IA_SESSION",
        hashlib.sha256
    ).hexdigest()

def _vertice_logged(request: Request):
    cookie = request.cookies.get("vertice_session", "")
    return bool(cookie) and hmac.compare_digest(cookie, _vertice_token())

@app.middleware("http")
async def vertice_visual_login_middleware(request: Request, call_next):
    if not VERTICE_AUTH_ENABLED:
        return await call_next(request)

    path = request.url.path

    if path in ["/login", "/api/login", "/favicon.ico"]:
        return await call_next(request)

    if _vertice_logged(request):
        return await call_next(request)

    if path.startswith("/api/"):
        return JSONResponse({"detail": "Acesso não autorizado. Faça login na VÉRTICE IA."}, status_code=401)

    return RedirectResponse("/login")

VERTICE_LOGIN_HTML = """
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Login — VÉRTICE IA</title>
<style>
*{box-sizing:border-box}
body{
  margin:0;
  min-height:100vh;
  display:flex;
  align-items:center;
  justify-content:center;
  font-family:Arial,Helvetica,sans-serif;
  color:#f8fafc;
  background:
    radial-gradient(circle at 20% 10%,rgba(251,191,36,.18),transparent 30%),
    radial-gradient(circle at 90% 20%,rgba(96,165,250,.14),transparent 28%),
    linear-gradient(135deg,#020617,#05070d 55%,#08111f);
}
.card{
  width:min(440px,92vw);
  border:1px solid rgba(251,191,36,.25);
  border-radius:28px;
  background:linear-gradient(180deg,rgba(15,23,42,.94),rgba(8,17,31,.92));
  box-shadow:0 30px 100px rgba(0,0,0,.42);
  padding:34px;
}
.logo{
  width:62px;
  height:62px;
  border-radius:20px;
  display:flex;
  align-items:center;
  justify-content:center;
  background:rgba(251,191,36,.13);
  border:1px solid rgba(251,191,36,.38);
  color:#fbbf24;
  font-weight:950;
  font-size:22px;
  margin-bottom:18px;
}
.eyebrow{
  color:#fbbf24;
  font-size:10px;
  letter-spacing:.28em;
  text-transform:uppercase;
  font-weight:900;
}
h1{
  margin:8px 0 8px;
  font-size:34px;
  letter-spacing:-.04em;
}
p{
  margin:0 0 22px;
  color:#94a3b8;
  line-height:1.55;
}
label{
  display:block;
  font-size:12px;
  font-weight:900;
  color:#cbd5e1;
  margin:16px 0 8px;
}
input{
  width:100%;
  border:1px solid #24324f;
  background:#020617;
  color:white;
  border-radius:16px;
  padding:14px 15px;
  font-size:15px;
  outline:none;
}
input:focus{
  border-color:rgba(251,191,36,.65);
  box-shadow:0 0 0 4px rgba(251,191,36,.08);
}
button{
  margin-top:22px;
  width:100%;
  border:0;
  border-radius:16px;
  padding:15px;
  font-size:15px;
  font-weight:950;
  color:#07101f;
  background:linear-gradient(135deg,#fbbf24,#f97316);
  cursor:pointer;
}
.error{
  display:none;
  margin-top:14px;
  border:1px solid rgba(251,113,133,.35);
  background:rgba(251,113,133,.1);
  color:#fecdd3;
  border-radius:14px;
  padding:12px;
  font-size:13px;
}
.footer{
  margin-top:20px;
  color:#64748b;
  font-size:11px;
  line-height:1.5;
}
</style>
</head>
<body>
  <main class="card">
    <div class="logo">V</div>
    <div class="eyebrow">Acesso restrito</div>
    <h1>VÉRTICE IA</h1>
    <p>Entre para acessar o painel estratégico com dados reais, relatórios e análise de conteúdo.</p>

    <form id="loginForm">
      <label>Usuário</label>
      <input id="username" autocomplete="username" placeholder="Digite o usuário" required>

      <label>Senha</label>
      <input id="password" type="password" autocomplete="current-password" placeholder="Digite a senha" required>

      <button type="submit">Entrar no painel</button>
      <div class="error" id="error">Usuário ou senha incorretos.</div>
    </form>

    <div class="footer">
      VÉRTICE IA • Acesso protegido para demonstração e operação do painel.
    </div>
  </main>

<script>
document.getElementById("loginForm").addEventListener("submit", async function(e){
  e.preventDefault();

  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value.trim();
  const error = document.getElementById("error");

  error.style.display = "none";

  const res = await fetch("/api/login", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({username,password})
  });

  if(res.ok){
    window.location.href = "/";
  }else{
    error.style.display = "block";
  }
});
</script>
</body>
</html>
"""

@app.get("/login", response_class=HTMLResponse)
def vertice_login_page():
    return VERTICE_LOGIN_HTML

@app.post("/api/login")
async def vertice_login_api(request: Request):
    data = await request.json()
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", "")).strip()

    if hmac.compare_digest(username, VERTICE_USER) and hmac.compare_digest(password, VERTICE_PASSWORD):
        response = JSONResponse({"ok": True})
        response.set_cookie(
            "vertice_session",
            _vertice_token(),
            httponly=True,
            samesite="lax",
            max_age=60 * 60 * 12,
            path="/"
        )
        return response

    return JSONResponse({"ok": False, "detail": "Usuário ou senha incorretos"}, status_code=401)

@app.post("/api/logout")
def vertice_logout_api():
    response = JSONResponse({"ok": True})
    response.delete_cookie("vertice_session", path="/")
    return response
'''

if "LOGIN VISUAL - VÉRTICE IA" not in s:
    m = re.search(r'\n@app\.get\(\s*[\'"]/[\'"]', s)
    if not m:
        raise RuntimeError("Não encontrei a rota principal para inserir o login visual.")
    s = s[:m.start()] + "\n" + login_code + "\n" + s[m.start():]

p.write_text(s, encoding="utf-8")

print("Correção aplicada.")
print("Agora não deve existir caixa de login do navegador.")
