from pathlib import Path
import re

# =========================
# BACKEND
# =========================

app_path = Path("backend/app.py")
s = app_path.read_text(encoding="utf-8")

Path("backend/app_backup_antes_login_facebook_cliente.py").write_text(s, encoding="utf-8")

imports = [
    "import secrets",
    "import urllib.parse",
    "from datetime import datetime, timedelta"
]

for imp in imports:
    if imp not in s:
        s = imp + "\n" + s

if "import requests" not in s:
    s = "import requests\n" + s

if "import json" not in s:
    s = "import json\n" + s

if "import sqlite3" not in s:
    s = "import sqlite3\n" + s

if "from pathlib import Path" not in s:
    s = "from pathlib import Path\n" + s

if "from fastapi.responses import HTMLResponse" not in s:
    if "from fastapi.responses import" in s:
        s = re.sub(
            r"from fastapi\.responses import ([^\n]+)",
            lambda m: m.group(0) + ", HTMLResponse" if "HTMLResponse" not in m.group(1) else m.group(0),
            s,
            count=1
        )
    else:
        s = "from fastapi.responses import HTMLResponse\n" + s

if "from fastapi import" in s:
    m = re.search(r"from fastapi import ([^\n]+)", s)
    if m:
        current = m.group(1)
        needed = []
        for name in ["HTTPException"]:
            if name not in current:
                needed.append(name)
        if needed:
            s = s.replace(m.group(0), "from fastapi import " + current + ", " + ", ".join(needed))
else:
    s = "from fastapi import HTTPException\n" + s

backend_code = r'''
# ==============================
# LOGIN FACEBOOK DO CLIENTE - VÉRTICE IA
# ==============================

def _meta_client_db_path():
    return Path(__file__).resolve().parent / "vertice_ia_limpa.db"

def _ensure_meta_client_tables():
    db = _meta_client_db_path()
    conn = sqlite3.connect(db)

    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS meta_oauth_states (
                state TEXT PRIMARY KEY,
                client_name TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS meta_connected_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT,
                fb_user_id TEXT,
                fb_user_name TEXT,
                user_access_token TEXT,
                token_expires_at TEXT,
                page_id TEXT,
                page_name TEXT,
                page_access_token TEXT,
                ig_user_id TEXT,
                ig_username TEXT,
                raw_payload TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()

    finally:
        conn.close()

def _meta_version():
    return os.getenv("META_API_VERSION", "v25.0").strip() or "v25.0"

def _meta_app_id():
    return os.getenv("META_APP_ID", "").strip()

def _meta_app_secret():
    return os.getenv("META_APP_SECRET", "").strip()

def _meta_redirect_uri():
    return os.getenv("META_REDIRECT_URI", "http://127.0.0.1:8000/api/facebook-login/callback").strip()

def _meta_login_scopes():
    return os.getenv(
        "META_LOGIN_SCOPES",
        "pages_show_list,pages_read_engagement,instagram_basic,instagram_manage_insights"
    ).strip()

def _meta_require_config():
    if not _meta_app_id():
        raise HTTPException(status_code=400, detail="META_APP_ID não configurado no backend/.env.")

    if not _meta_app_secret():
        raise HTTPException(status_code=400, detail="META_APP_SECRET não configurado no backend/.env.")

def _meta_connected_row_to_dict(row):
    if not row:
        return None

    data = dict(row)

    try:
        data["raw_payload"] = json.loads(data.get("raw_payload") or "{}")
    except Exception:
        data["raw_payload"] = {}

    safe = dict(data)
    safe["user_access_token"] = "***"
    safe["page_access_token"] = "***"

    return safe

def _meta_graph_get(path, token, params=None, timeout=30):
    version = _meta_version()
    url = f"https://graph.facebook.com/{version}/{path.lstrip('/')}"

    payload = dict(params or {})
    payload["access_token"] = token

    r = requests.get(url, params=payload, timeout=timeout)

    try:
        data = r.json()
    except Exception:
        data = {"raw": r.text}

    if not r.ok:
        raise HTTPException(status_code=400, detail={
            "message": "Erro na chamada da Meta.",
            "path": path,
            "meta": data
        })

    return data

@app.get("/api/facebook-login/config")
def api_facebook_login_config():
    return {
        "status": "sucesso",
        "configured": bool(_meta_app_id() and _meta_app_secret()),
        "app_id_present": bool(_meta_app_id()),
        "app_secret_present": bool(_meta_app_secret()),
        "redirect_uri": _meta_redirect_uri(),
        "scopes": _meta_login_scopes()
    }

@app.get("/api/facebook-login/start")
def api_facebook_login_start(client_name: str = ""):
    _ensure_meta_client_tables()
    _meta_require_config()

    client_name = (client_name or "").strip()
    state = secrets.token_urlsafe(32)

    db = _meta_client_db_path()
    conn = sqlite3.connect(db)

    try:
        conn.execute(
            "INSERT INTO meta_oauth_states (state, client_name) VALUES (?, ?)",
            (state, client_name)
        )
        conn.commit()
    finally:
        conn.close()

    version = _meta_version()
    params = {
        "client_id": _meta_app_id(),
        "redirect_uri": _meta_redirect_uri(),
        "state": state,
        "response_type": "code",
        "scope": _meta_login_scopes()
    }

    login_url = f"https://www.facebook.com/{version}/dialog/oauth?" + urllib.parse.urlencode(params)

    return {
        "status": "sucesso",
        "login_url": login_url,
        "redirect_uri": _meta_redirect_uri(),
        "scopes": _meta_login_scopes()
    }

@app.get("/api/facebook-login/callback")
def api_facebook_login_callback(code: str = "", state: str = "", error: str = "", error_description: str = ""):
    _ensure_meta_client_tables()
    _meta_require_config()

    if error:
        return HTMLResponse(f"""
        <html>
        <body style="font-family:Arial;background:#020617;color:white;padding:40px">
          <h1>Login cancelado</h1>
          <p>{error}</p>
          <p>{error_description}</p>
        </body>
        </html>
        """)

    if not code:
        return HTMLResponse("""
        <html>
        <body style="font-family:Arial;background:#020617;color:white;padding:40px">
          <h1>Erro</h1>
          <p>A Meta não retornou o código de autorização.</p>
        </body>
        </html>
        """)

    db = _meta_client_db_path()
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row

    try:
        row = conn.execute(
            "SELECT * FROM meta_oauth_states WHERE state = ?",
            (state,)
        ).fetchone()

        if not row:
            return HTMLResponse("""
            <html>
            <body style="font-family:Arial;background:#020617;color:white;padding:40px">
              <h1>State inválido</h1>
              <p>O login não pôde ser validado. Gere um novo link pela VÉRTICE IA.</p>
            </body>
            </html>
            """)

        client_name = row["client_name"] or ""

        version = _meta_version()

        token_url = f"https://graph.facebook.com/{version}/oauth/access_token"

        short_resp = requests.get(token_url, params={
            "client_id": _meta_app_id(),
            "client_secret": _meta_app_secret(),
            "redirect_uri": _meta_redirect_uri(),
            "code": code
        }, timeout=30)

        short_data = short_resp.json()

        if not short_resp.ok:
            return HTMLResponse(f"""
            <html>
            <body style="font-family:Arial;background:#020617;color:white;padding:40px">
              <h1>Erro ao trocar código por token</h1>
              <pre>{json.dumps(short_data, ensure_ascii=False, indent=2)}</pre>
            </body>
            </html>
            """)

        short_token = short_data.get("access_token")

        long_resp = requests.get(token_url, params={
            "grant_type": "fb_exchange_token",
            "client_id": _meta_app_id(),
            "client_secret": _meta_app_secret(),
            "fb_exchange_token": short_token
        }, timeout=30)

        long_data = long_resp.json()

        if not long_resp.ok:
            return HTMLResponse(f"""
            <html>
            <body style="font-family:Arial;background:#020617;color:white;padding:40px">
              <h1>Erro ao gerar token longo</h1>
              <pre>{json.dumps(long_data, ensure_ascii=False, indent=2)}</pre>
            </body>
            </html>
            """)

        user_token = long_data.get("access_token") or short_token
        expires_in = int(long_data.get("expires_in") or 5184000)
        token_expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat()

        me = _meta_graph_get("me", user_token, {
            "fields": "id,name"
        })

        pages = _meta_graph_get("me/accounts", user_token, {
            "fields": "id,name,access_token,instagram_business_account{id,username,name}"
        })

        saved = []

        for page in pages.get("data", []):
            ig = page.get("instagram_business_account")

            if not ig or not ig.get("id"):
                continue

            existing = conn.execute(
                """
                SELECT id FROM meta_connected_accounts
                 WHERE fb_user_id = ? AND ig_user_id = ?
                """,
                (me.get("id"), ig.get("id"))
            ).fetchone()

            raw_payload = {
                "me": me,
                "page": {
                    "id": page.get("id"),
                    "name": page.get("name")
                },
                "ig": ig
            }

            if existing:
                item_id = existing["id"]

                conn.execute("""
                    UPDATE meta_connected_accounts
                       SET client_name = ?,
                           fb_user_name = ?,
                           user_access_token = ?,
                           token_expires_at = ?,
                           page_id = ?,
                           page_name = ?,
                           page_access_token = ?,
                           ig_username = ?,
                           raw_payload = ?,
                           updated_at = CURRENT_TIMESTAMP
                     WHERE id = ?
                """, (
                    client_name,
                    me.get("name"),
                    user_token,
                    token_expires_at,
                    page.get("id"),
                    page.get("name"),
                    page.get("access_token"),
                    ig.get("username"),
                    json.dumps(raw_payload, ensure_ascii=False),
                    item_id
                ))

            else:
                cur = conn.execute("""
                    INSERT INTO meta_connected_accounts (
                        client_name,
                        fb_user_id,
                        fb_user_name,
                        user_access_token,
                        token_expires_at,
                        page_id,
                        page_name,
                        page_access_token,
                        ig_user_id,
                        ig_username,
                        raw_payload
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    client_name,
                    me.get("id"),
                    me.get("name"),
                    user_token,
                    token_expires_at,
                    page.get("id"),
                    page.get("name"),
                    page.get("access_token"),
                    ig.get("id"),
                    ig.get("username"),
                    json.dumps(raw_payload, ensure_ascii=False)
                ))

                item_id = cur.lastrowid

            saved.append({
                "id": item_id,
                "client_name": client_name,
                "page_name": page.get("name"),
                "ig_username": ig.get("username"),
                "ig_user_id": ig.get("id")
            })

        conn.execute(
            "DELETE FROM meta_oauth_states WHERE state = ?",
            (state,)
        )

        conn.commit()

        if not saved:
            return HTMLResponse(f"""
            <html>
            <body style="font-family:Arial;background:#020617;color:white;padding:40px">
              <h1>Login concluído, mas nenhum Instagram profissional foi localizado</h1>
              <p>O cliente precisa ter uma conta Instagram Business ou Creator conectada a uma Página do Facebook que ele administre.</p>
              <pre>{json.dumps(pages, ensure_ascii=False, indent=2)}</pre>
            </body>
            </html>
            """)

        items = "".join([
            f"<li><strong>@{x['ig_username']}</strong> — Página: {x['page_name']}</li>"
            for x in saved
        ])

        return HTMLResponse(f"""
        <html>
        <body style="font-family:Arial;background:#020617;color:white;padding:40px">
          <h1>Cliente conectado com sucesso</h1>
          <p>A VÉRTICE IA já pode consultar os insights autorizados deste cliente.</p>
          <ul>{items}</ul>
          <p>Volte para a aba <strong>Conectar Cliente Meta</strong> e clique em <strong>Atualizar contas conectadas</strong>.</p>
        </body>
        </html>
        """)

    finally:
        conn.close()

@app.get("/api/meta-connected/accounts")
def api_meta_connected_accounts():
    _ensure_meta_client_tables()

    db = _meta_client_db_path()
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row

    try:
        rows = conn.execute("""
            SELECT * FROM meta_connected_accounts
             ORDER BY updated_at DESC, id DESC
        """).fetchall()

        return {
            "status": "sucesso",
            "items": [_meta_connected_row_to_dict(row) for row in rows]
        }

    finally:
        conn.close()

def _parse_insights_response(data):
    out = {}

    for item in data.get("data", []):
        name = item.get("name")
        values = item.get("values") or []

        value = 0

        if values:
            raw = values[0].get("value", 0)

            if isinstance(raw, dict):
                value = sum(int(v or 0) for v in raw.values())
            else:
                try:
                    value = int(raw or 0)
                except Exception:
                    value = 0

        out[name] = value

    return out

def _connected_client_strategy(account, posts):
    posts = posts or []

    total_reach = sum(int(p.get("reach") or 0) for p in posts)
    total_saved = sum(int(p.get("saved") or 0) for p in posts)
    total_shares = sum(int(p.get("shares") or 0) for p in posts)
    total_likes = sum(int(p.get("like_count") or 0) for p in posts)
    total_comments = sum(int(p.get("comments_count") or 0) for p in posts)

    def score(p):
        return (
            int(p.get("reach") or 0) * 0.2 +
            int(p.get("saved") or 0) * 8 +
            int(p.get("shares") or 0) * 7 +
            int(p.get("comments_count") or 0) * 5 +
            int(p.get("like_count") or 0)
        )

    ranked = sorted(posts, key=score, reverse=True)

    top_posts = []

    for p in ranked[:8]:
        caption = (p.get("caption") or "Publicação sem legenda").replace("\n", " ").strip()

        top_posts.append({
            "id": p.get("id"),
            "caption": caption[:220] + ("..." if len(caption) > 220 else ""),
            "media_type": p.get("media_type"),
            "permalink": p.get("permalink"),
            "timestamp": p.get("timestamp"),
            "reach": int(p.get("reach") or 0),
            "saved": int(p.get("saved") or 0),
            "shares": int(p.get("shares") or 0),
            "like_count": int(p.get("like_count") or 0),
            "comments_count": int(p.get("comments_count") or 0),
            "score": round(score(p), 2)
        })

    evidence = [
        f"Conta conectada: @{account.get('ig_username')}.",
        f"Foram analisados {len(posts)} posts com token autorizado pelo cliente.",
        f"Alcance total observado: {total_reach}.",
        f"Salvamentos totais observados: {total_saved}.",
        f"Compartilhamentos totais observados: {total_shares}.",
        f"Curtidas públicas observadas: {total_likes}.",
        f"Comentários públicos observados: {total_comments}."
    ]

    if top_posts:
        top = top_posts[0]
        evidence.append(
            f"Conteúdo com melhor pontuação estratégica: {top['reach']} de alcance, {top['saved']} salvamentos, {top['shares']} compartilhamentos, {top['comments_count']} comentários."
        )

    strengths = []

    if total_saved > 0:
        strengths.append("Existem salvamentos, indicando conteúdos com valor de consulta ou interesse posterior.")

    if total_shares > 0:
        strengths.append("Existem compartilhamentos, indicando conteúdos com potencial de circulação orgânica.")

    if total_comments > 0:
        strengths.append("Existem comentários, indicando abertura para conversa e relacionamento.")

    if ranked:
        strengths.append("Já há base real para identificar conteúdos que merecem repetição, ajuste ou teste de tráfego.")

    adjustments = []

    if total_saved == 0:
        adjustments.append("Os posts analisados não apresentaram salvamentos relevantes. É necessário criar conteúdos mais úteis, como checklists, dicas, erros comuns e passo a passo.")

    if total_shares == 0:
        adjustments.append("Os posts analisados não apresentaram compartilhamentos relevantes. É necessário criar conteúdos com identificação, opinião, utilidade ou prova social.")

    if total_comments == 0:
        adjustments.append("Os posts analisados não geraram conversa. É necessário inserir CTAs, perguntas e temas que provoquem resposta.")

    if total_reach == 0:
        adjustments.append("A API não retornou alcance para os posts analisados. Verifique permissões, tipo de mídia e validade do token.")

    recommendations = []

    if top_posts:
        recommendations.append(
            "Repetir o tema do post com melhor combinação de alcance, salvamentos, compartilhamentos e comentários."
        )

    recommendations.append("Usar posts com salvamentos como base para conteúdos educativos e materiais de autoridade.")
    recommendations.append("Usar posts com compartilhamentos como base para conteúdos de alcance e reconhecimento.")
    recommendations.append("Usar posts com comentários como base para relacionamento, dúvidas e conversão.")
    recommendations.append("Separar os próximos conteúdos em três grupos: autoridade, prova social e oferta.")

    return {
        "modo": "cliente_conectado_meta",
        "resumo_executivo": "Relatório gerado com dados autorizados da conta profissional do cliente.",
        "diagnostico": "Esta leitura usa insights reais recebidos após login Facebook/Meta do cliente.",
        "account": account,
        "totais": {
            "posts": len(posts),
            "alcance": total_reach,
            "salvos": total_saved,
            "compartilhamentos": total_shares,
            "curtidas": total_likes,
            "comentarios": total_comments
        },
        "evidencias": evidence,
        "pontos_fortes": strengths,
        "pontos_de_ajuste": adjustments,
        "recomendacoes": recommendations,
        "top_posts": top_posts
    }

@app.get("/api/meta-connected/accounts/{account_id}/insights")
def api_meta_connected_account_insights(account_id: int, limit: int = 25):
    _ensure_meta_client_tables()

    try:
        limit = int(limit or 25)
    except Exception:
        limit = 25

    limit = max(1, min(limit, 50))

    db = _meta_client_db_path()
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row

    try:
        row = conn.execute(
            "SELECT * FROM meta_connected_accounts WHERE id = ?",
            (account_id,)
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Conta conectada não encontrada.")

        account = dict(row)
        token = account.get("page_access_token")
        ig_user_id = account.get("ig_user_id")

        if not token or not ig_user_id:
            raise HTTPException(status_code=400, detail="Conta conectada sem token ou Instagram ID.")

        media = _meta_graph_get(f"{ig_user_id}/media", token, {
            "fields": "id,caption,media_type,permalink,timestamp,like_count,comments_count",
            "limit": limit
        })

        posts = []

        for m in media.get("data", []):
            insights = {}

            metric_sets = [
                "reach,saved,shares,total_interactions",
                "reach,saved,total_interactions",
                "reach"
            ]

            for metrics in metric_sets:
                try:
                    raw = _meta_graph_get(f"{m.get('id')}/insights", token, {
                        "metric": metrics
                    })
                    insights = _parse_insights_response(raw)
                    break
                except Exception:
                    insights = {}

            posts.append({
                "id": m.get("id"),
                "caption": m.get("caption") or "",
                "media_type": m.get("media_type") or "",
                "permalink": m.get("permalink") or "",
                "timestamp": m.get("timestamp") or "",
                "like_count": int(m.get("like_count") or 0),
                "comments_count": int(m.get("comments_count") or 0),
                "reach": int(insights.get("reach") or 0),
                "saved": int(insights.get("saved") or 0),
                "shares": int(insights.get("shares") or 0),
                "total_interactions": int(insights.get("total_interactions") or 0),
                "insights": insights
            })

        safe_account = _meta_connected_row_to_dict(row)

        return {
            "status": "sucesso",
            "account": safe_account,
            "posts": posts,
            "report": _connected_client_strategy(safe_account, posts)
        }

    finally:
        conn.close()
'''

if "LOGIN FACEBOOK DO CLIENTE - VÉRTICE IA" not in s:
    m = re.search(r"\napp\.mount\(", s)
    if not m:
        raise RuntimeError("Não encontrei ponto seguro antes do app.mount.")
    s = s[:m.start()] + "\n" + backend_code + "\n" + s[m.start():]

app_path.write_text(s, encoding="utf-8")


# =========================
# FRONTEND
# =========================

index_path = Path("backend/static/index.html")
html = index_path.read_text(encoding="utf-8")

Path("backend/static/index_backup_antes_login_facebook_cliente.html").write_text(html, encoding="utf-8")

if '["conectarMeta","Conectar Cliente Meta","◇"]' not in html:
    if '["historicoComercial","Histórico Comercial","▣"],' in html:
        html = html.replace(
            '["historicoComercial","Histórico Comercial","▣"],',
            '["historicoComercial","Histórico Comercial","▣"],\n  ["conectarMeta","Conectar Cliente Meta","◇"],'
        )
    elif '["perfilCliente","Perfil Cliente","◐"],' in html:
        html = html.replace(
            '["perfilCliente","Perfil Cliente","◐"],',
            '["perfilCliente","Perfil Cliente","◐"],\n  ["conectarMeta","Conectar Cliente Meta","◇"],'
        )
    else:
        html = html.replace(
            '["estrategico","Estratégico","◈"],',
            '["estrategico","Estratégico","◈"],\n  ["conectarMeta","Conectar Cliente Meta","◇"],'
        )

if '<section id="conectarMeta" class="section"></section>' not in html:
    html = html.replace(
        '<section id="sobre" class="section"></section>',
        '<section id="conectarMeta" class="section"></section>\n    <section id="sobre" class="section"></section>'
    )

if 'if(state.tab==="conectarMeta") renderConectarMeta();' not in html:
    if 'if(state.tab==="historicoComercial") renderHistoricoComercial();' in html:
        html = html.replace(
            'if(state.tab==="historicoComercial") renderHistoricoComercial();',
            'if(state.tab==="historicoComercial") renderHistoricoComercial();\n  if(state.tab==="conectarMeta") renderConectarMeta();'
        )
    else:
        html = html.replace(
            'if(state.tab==="sobre") renderSobre();',
            'if(state.tab==="conectarMeta") renderConectarMeta();\n  if(state.tab==="sobre") renderSobre();'
        )

frontend_code = r'''
// ==============================
// CONECTAR CLIENTE META
// ==============================

function metaEsc(text){
  return String(text || "")
    .replaceAll("&","&amp;")
    .replaceAll("<","&lt;")
    .replaceAll(">","&gt;")
    .replaceAll('"',"&quot;")
    .replaceAll("'","&#039;");
}

function metaGet(id){
  const el = document.getElementById(id);
  return el ? el.value.trim() : "";
}

async function metaApi(url, options={}){
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    }
  });

  let data = null;

  try{
    data = await res.json();
  }catch{
    data = {};
  }

  if(!res.ok){
    const detail = data.detail || data.message || "Erro na integração Meta.";
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }

  return data;
}

async function metaCheckConfig(){
  try{
    const data = await metaApi("/api/facebook-login/config");

    const box = document.getElementById("metaConfigBox");

    if(!box) return;

    if(data.configured){
      box.innerHTML = `
        <div class="alert success">
          Configuração Meta encontrada. Redirect URI: <strong>${metaEsc(data.redirect_uri)}</strong>
        </div>
      `;
    }else{
      box.innerHTML = `
        <div class="alert">
          Configure META_APP_ID, META_APP_SECRET e META_REDIRECT_URI no backend/.env antes de gerar login para clientes.
        </div>
      `;
    }

  }catch(e){
    show(e.message);
  }
}

async function metaGenerateLogin(){
  const clientName = metaGet("metaClientName");

  try{
    const data = await metaApi(`/api/facebook-login/start?client_name=${encodeURIComponent(clientName)}`);

    const box = document.getElementById("metaLoginBox");

    if(box){
      box.innerHTML = `
        <div class="card gold">
          <div class="eyebrow">Link de autorização</div>
          <h2>Login Facebook do cliente</h2>
          <p class="muted">Envie este link para o cliente ou abra no navegador para teste.</p>

          <input value="${metaEsc(data.login_url)}" readonly style="width:100%;border-radius:14px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:12px;margin-top:6px;">

          <br><br>

          <div class="row">
            <button class="btn" onclick="window.open('${data.login_url}', '_blank')">Abrir login</button>
            <button class="btn secondary" onclick="navigator.clipboard.writeText('${data.login_url}'); show('Link copiado.', 'success')">Copiar link</button>
          </div>

          <br>

          <div class="alert success">
            Depois que o cliente concluir o login, clique em <strong>Atualizar contas conectadas</strong>.
          </div>
        </div>
      `;
    }

    show("Link de login gerado.", "success");

  }catch(e){
    show(e.message);
  }
}

async function metaListAccounts(){
  try{
    const data = await metaApi("/api/meta-connected/accounts");
    const box = document.getElementById("metaAccountsBox");

    if(!box) return;

    const items = data.items || [];

    if(!items.length){
      box.innerHTML = `<div class="empty">Nenhuma conta conectada ainda.</div>`;
      return;
    }

    box.innerHTML = `
      <div class="grid two">
        ${items.map(item => `
          <div class="card">
            <div class="between">
              <div>
                <div class="eyebrow">Conta conectada #${item.id}</div>
                <h2>@${metaEsc(item.ig_username || "")}</h2>
                <p class="muted">${metaEsc(item.client_name || "Cliente sem nome")} • Página: ${metaEsc(item.page_name || "")}</p>
              </div>
              <span class="badge green">Autorizada</span>
            </div>

            <div class="reportBlock">
              <h3>Token</h3>
              <p>Expira em: ${metaEsc((item.token_expires_at || "").slice(0,19).replace("T"," "))}</p>
            </div>

            <div class="row">
              <button class="btn" onclick="metaLoadInsights(${item.id})">Gerar relatório com insights</button>
            </div>
          </div>
        `).join("")}
      </div>
    `;

  }catch(e){
    show(e.message);
  }
}

function metaReportHtml(report){
  const t = report.totais || {};
  const top = report.top_posts || [];

  return `
    <div class="card gold">
      <div class="between">
        <div>
          <div class="eyebrow">Relatório com login do cliente</div>
          <h2>${metaEsc(report.account?.client_name || "Cliente conectado")}</h2>
          <p class="muted">@${metaEsc(report.account?.ig_username || "")} • dados autorizados via Meta</p>
        </div>
        <span class="badge green">Insights reais</span>
      </div>

      <div class="grid five">
        <div class="stat gold"><small>Posts</small><strong>${fmt(t.posts || 0)}</strong></div>
        <div class="stat"><small>Alcance</small><strong>${fmt(t.alcance || 0)}</strong></div>
        <div class="stat"><small>Salvos</small><strong>${fmt(t.salvos || 0)}</strong></div>
        <div class="stat"><small>Shares</small><strong>${fmt(t.compartilhamentos || 0)}</strong></div>
        <div class="stat"><small>Comentários</small><strong>${fmt(t.comentarios || 0)}</strong></div>
      </div>

      <div class="reportBlock">
        <h3>Resumo</h3>
        <p>${metaEsc(report.resumo_executivo || "")}</p>
        <p>${metaEsc(report.diagnostico || "")}</p>
      </div>
    </div>

    <br>

    <div class="grid two">
      <div class="card">
        <div class="eyebrow">Evidências</div>
        <h2>O que os dados mostram</h2>
        <ul>${(report.evidencias || []).map(x => `<li>${metaEsc(x)}</li>`).join("")}</ul>
      </div>

      <div class="card">
        <div class="eyebrow">Estratégia</div>
        <h2>Recomendações</h2>
        <ul>${(report.recomendacoes || []).map(x => `<li>${metaEsc(x)}</li>`).join("")}</ul>
      </div>
    </div>

    <br>

    <div class="grid two">
      <div class="card">
        <div class="eyebrow">Forças</div>
        <h2>Pontos fortes</h2>
        <ul>${(report.pontos_fortes || []).map(x => `<li>${metaEsc(x)}</li>`).join("") || "<li>Nenhum ponto forte suficiente identificado.</li>"}</ul>
      </div>

      <div class="card">
        <div class="eyebrow">Ajustes</div>
        <h2>Pontos de ajuste</h2>
        <ul>${(report.pontos_de_ajuste || []).map(x => `<li>${metaEsc(x)}</li>`).join("") || "<li>Nenhum ajuste crítico identificado.</li>"}</ul>
      </div>
    </div>

    <br>

    <div class="card">
      <div class="eyebrow">Ranking</div>
      <h2>Posts com maior força estratégica</h2>
      ${top.map((p, i) => `
        <div class="item">
          <div class="row">
            <span class="badge gold">#${i + 1}</span>
            <span class="badge">Alcance: ${fmt(p.reach || 0)}</span>
            <span class="badge green">Salvos: ${fmt(p.saved || 0)}</span>
            <span class="badge blue">Shares: ${fmt(p.shares || 0)}</span>
            <span class="badge">Comentários: ${fmt(p.comments_count || 0)}</span>
          </div>
          <div class="postTitle">${metaEsc(p.caption || "Publicação sem legenda")}</div>
          ${p.permalink ? `<a href="${p.permalink}" target="_blank">Abrir post</a>` : ""}
        </div>
      `).join("")}
    </div>
  `;
}

async function metaLoadInsights(id){
  try{
    show("Buscando insights reais da conta conectada...", "success");

    const data = await metaApi(`/api/meta-connected/accounts/${id}/insights?limit=25`);

    const box = document.getElementById("metaInsightsBox");

    if(box){
      box.innerHTML = metaReportHtml(data.report || {});
    }

    show("Relatório com insights do cliente gerado.", "success");

  }catch(e){
    show(e.message);
  }
}

function renderConectarMeta(){
  $("conectarMeta").innerHTML = `
    <div class="card gold">
      <div class="between">
        <div>
          <div class="eyebrow">Login Facebook do cliente</div>
          <h2>Conectar Cliente Meta</h2>
          <p class="muted">
            Use esta aba para o cliente autorizar a VÉRTICE IA a acessar os insights reais da conta profissional dele.
          </p>
        </div>
        <span class="badge gold">OAuth Meta</span>
      </div>
    </div>

    <br>

    <div id="metaConfigBox"></div>

    <br>

    <div class="card">
      <div class="eyebrow">Gerar login</div>
      <h2>Solicitar autorização do cliente</h2>

      <label class="muted">Nome do cliente</label>
      <input id="metaClientName" placeholder="Ex: Espaço TM Pilates" style="width:100%;border-radius:14px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:12px;margin-top:6px;">

      <br><br>

      <div class="alert">
        O cliente precisa entrar com o Facebook que administra a Página conectada ao Instagram profissional dele.
      </div>

      <br>

      <div class="row">
        <button class="btn" onclick="metaGenerateLogin()">Gerar link de login Facebook</button>
        <button class="btn secondary" onclick="metaListAccounts()">Atualizar contas conectadas</button>
      </div>
    </div>

    <br>

    <div id="metaLoginBox"></div>

    <br>

    <div class="card">
      <div class="between">
        <div>
          <div class="eyebrow">Contas autorizadas</div>
          <h2>Clientes conectados</h2>
        </div>
        <button class="btn secondary" onclick="metaListAccounts()">Atualizar</button>
      </div>

      <br>

      <div id="metaAccountsBox">
        <div class="empty">Clique em <strong>Atualizar contas conectadas</strong>.</div>
      </div>
    </div>

    <br>

    <div id="metaInsightsBox"></div>
  `;

  setTimeout(() => {
    metaCheckConfig();
    metaListAccounts();
  }, 80);
}
'''

if "function renderConectarMeta()" not in html:
    html = html.replace("function renderSobre(){", frontend_code + "\nfunction renderSobre(){")

index_path.write_text(html, encoding="utf-8")

print("Login Facebook do Cliente adicionado com sucesso.")
print("Nova aba: Conectar Cliente Meta")
print("Endpoints adicionados:")
print("- /api/facebook-login/config")
print("- /api/facebook-login/start")
print("- /api/facebook-login/callback")
print("- /api/meta-connected/accounts")
print("- /api/meta-connected/accounts/{id}/insights")
