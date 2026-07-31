from pathlib import Path
import re

p = Path("backend/app.py")
s = p.read_text(encoding="utf-8")

# Imports necessários
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
    for nome in ["HTMLResponse", "Response", "JSONResponse", "RedirectResponse"]:
        if nome not in nomes:
            nomes.append(nome)
    s = s[:m.start()] + "from fastapi.responses import " + ", ".join(nomes) + s[m.end():]

# Remove proteção antiga por Basic Auth, caso exista
while "async def vertice_basic_auth" in s:
    pos = s.find("async def vertice_basic_auth")
    starts = [
        s.rfind("# ==============================", 0, pos),
        s.rfind("VERTICE_AUTH_ENABLED", 0, pos),
        s.rfind("def _auth_required", 0, pos),
        s.rfind("def _vertice_auth_required", 0, pos),
    ]
    starts = [x for x in starts if x != -1]
    if not starts:
        break
    start = min(starts)
    start = s.rfind("\n", 0, start) + 1

    ends = [
        s.find("\n@app.get", pos),
        s.find("\n@app.post", pos),
        s.find("\napp.mount", pos),
    ]
    ends = [x for x in ends if x != -1]
    end = min(ends) if ends else len(s)

    s = s[:start] + s[end:]

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
async def vertice_visual_auth(request: Request, call_next):
    if not VERTICE_AUTH_ENABLED:
        return await call_next(request)

    path = request.url.path

    public_paths = {
        "/login",
        "/api/login",
        "/favicon.ico"
    }

    if path in public_paths:
        return await call_next(request)

    if _vertice_logged(request):
        return await call_next(request)

    if path.startswith("/api/"):
        return JSONResponse({"detail": "Acesso não autorizado"}, status_code=401)

    return RedirectResponse("/login")

VERTICE_LOGIN_HTML = """
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Login — VÉRTICE IA</title>
<style>
:root{
  --bg:#04060c;
  --panel:#0f172a;
  --line:#24324f;
  --text:#f8fafc;
  --muted:#94a3b8;
  --gold:#fbbf24;
  --gold2:#f97316;
  --red:#fb7185;
}
*{box-sizing:border-box}
body{
  margin:0;
  min-height:100vh;
  display:flex;
  align-items:center;
  justify-content:center;
  font-family:Arial,Helvetica,sans-serif;
  color:var(--text);
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
  color:var(--gold);
  font-weight:950;
  font-size:22px;
  margin-bottom:18px;
}
.eyebrow{
  color:var(--gold);
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
  color:var(--muted);
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
  border:1px solid var(--line);
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
  background:linear-gradient(135deg,var(--gold),var(--gold2));
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
    s = s.replace("\n@app.get", "\n" + login_code + "\n@app.get", 1)

p.write_text(s, encoding="utf-8")

# Adiciona botão sair no index.html
idx = Path("backend/static/index.html")
html = idx.read_text(encoding="utf-8")

if "logoutVertice" not in html:
    html = html.replace(
        '<span id="apiStatusDetail">Aguardando resposta da API local.</span>',
        '<span id="apiStatusDetail">Aguardando resposta da API local.</span><br><br><button class="btn ghost" onclick="logoutVertice()">Sair</button>'
    )

    html = html.replace(
        "function renderSobre(){",
        '''
async function logoutVertice(){
  await fetch("/api/logout", {method:"POST"});
  window.location.href = "/login";
}

function renderSobre(){'''
    )

idx.write_text(html, encoding="utf-8")

print("Login visual aplicado com sucesso.")
print("Usuario: vertice")
print("Senha: 262817")
