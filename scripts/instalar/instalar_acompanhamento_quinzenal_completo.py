from pathlib import Path

p = Path("backend/app.py")

if not p.exists():
    raise RuntimeError("backend/app.py não encontrado.")

s = p.read_text(encoding="utf-8")
Path("backend/app_backup_acompanhamento_quinzenal_completo.py").write_text(s, encoding="utf-8")

patch = r'''

# ============================================================
# VÉRTICE IA - ACOMPANHAMENTO QUINZENAL COMPLETO
# ============================================================

def _ensure_acompanhamento_quinzenal_tables():
    import sqlite3
    from pathlib import Path

    db_path = Path("backend") / "vertice_ia_limpa.db"
    if not db_path.exists():
        db_path = Path("vertice_ia_limpa.db")

    conn = sqlite3.connect(db_path)

    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS acompanhamento_quinzenal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER,
                client_name TEXT,
                page_id TEXT,
                page_name TEXT,
                instagram_business_account_id TEXT,
                instagram_username TEXT,
                period_start TEXT,
                period_end TEXT,
                followers_count INTEGER DEFAULT 0,
                media_count INTEGER DEFAULT 0,
                reach INTEGER DEFAULT 0,
                impressions INTEGER DEFAULT 0,
                profile_views INTEGER DEFAULT 0,
                website_clicks INTEGER DEFAULT 0,
                total_interactions INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0,
                saves INTEGER DEFAULT 0,
                posts_count INTEGER DEFAULT 0,
                best_post_id TEXT,
                best_post_caption TEXT,
                best_post_permalink TEXT,
                best_post_metric INTEGER DEFAULT 0,
                raw_json TEXT,
                strategic_analysis TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()

    finally:
        conn.close()


def _aq_get_db_path():
    from pathlib import Path

    db_path = Path("backend") / "vertice_ia_limpa.db"
    if not db_path.exists():
        db_path = Path("vertice_ia_limpa.db")

    return db_path


def _aq_get_connected_accounts():
    import sqlite3

    _ensure_acompanhamento_quinzenal_tables()

    db_path = _aq_get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        rows = conn.execute("""
            SELECT
                id,
                client_name,
                page_id,
                page_name,
                page_access_token,
                instagram_business_account_id,
                instagram_username,
                page_token_status,
                token_checked_at
            FROM meta_connected_accounts
            ORDER BY id DESC
        """).fetchall()

        accounts = []

        for r in rows:
            item = dict(r)
            token = item.pop("page_access_token", None)
            item["has_page_access_token"] = bool(token)
            accounts.append(item)

        return accounts

    finally:
        conn.close()


def _aq_get_connected_account(account_id=None):
    import sqlite3

    db_path = _aq_get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        if account_id:
            row = conn.execute("""
                SELECT *
                FROM meta_connected_accounts
                WHERE id = ?
                LIMIT 1
            """, (account_id,)).fetchone()
        else:
            row = conn.execute("""
                SELECT *
                FROM meta_connected_accounts
                ORDER BY id DESC
                LIMIT 1
            """).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Nenhuma conta Meta conectada encontrada.")

        account = dict(row)

        if not account.get("page_access_token"):
            raise HTTPException(status_code=400, detail="Conta sem Page Access Token salvo. Reconecte a Meta.")

        if not account.get("instagram_business_account_id"):
            raise HTTPException(status_code=400, detail="Conta sem Instagram Business Account ID. Reconecte a Meta.")

        return account

    finally:
        conn.close()


def _aq_sum_metric(metric_item):
    total = 0

    try:
        values = metric_item.get("values") or []

        for v in values:
            value = v.get("value", 0)

            if isinstance(value, dict):
                for sub in value.values():
                    if isinstance(sub, (int, float)):
                        total += int(sub)

            elif isinstance(value, (int, float)):
                total += int(value)

        return total

    except Exception:
        return 0


def _aq_get_metric(metrics_map, name):
    value = metrics_map.get(name)
    if value is None:
        return 0
    return int(value or 0)


def _aq_fetch_basic_account(ig_id, token):
    return _meta_graph_get(ig_id, token, {
        "fields": "id,username,followers_count,media_count"
    })


def _aq_fetch_insights(ig_id, token, since, until):
    """
    Algumas métricas podem variar conforme tipo da conta, permissão e versão da API.
    Por isso tentamos primeiro um conjunto amplo e depois fazemos fallback seguro.
    """
    attempts = [
        "reach,impressions,profile_views,website_clicks,total_interactions,likes,comments,shares,saves",
        "reach,impressions,profile_views,website_clicks",
        "reach,profile_views",
        "reach"
    ]

    last_error = None

    for metrics in attempts:
        try:
            return _meta_graph_get(f"{ig_id}/insights", token, {
                "metric": metrics,
                "period": "day",
                "since": since,
                "until": until
            })
        except Exception as e:
            last_error = str(e)

    return {
        "data": [],
        "warning": "A Meta não retornou métricas de insights para este período.",
        "last_error": last_error
    }


def _aq_fetch_media(ig_id, token, since, until):
    try:
        data = _meta_graph_get(f"{ig_id}/media", token, {
            "fields": "id,caption,media_type,timestamp,like_count,comments_count,permalink",
            "limit": 100
        })
    except Exception:
        return []

    posts = data.get("data", []) if isinstance(data, dict) else []
    filtered = []

    for post in posts:
        ts = (post.get("timestamp") or "")[:10]
        if since <= ts <= until:
            filtered.append(post)

    return filtered


def _aq_percent_change(current, previous):
    current = current or 0
    previous = previous or 0

    if previous == 0:
        return None

    return round(((current - previous) / previous) * 100, 1)


def _aq_build_analysis(current, previous=None):
    lines = []

    reach = current.get("reach") or 0
    followers = current.get("followers_count") or 0
    interactions = current.get("total_interactions") or 0
    impressions = current.get("impressions") or 0
    profile_views = current.get("profile_views") or 0
    posts_count = current.get("posts_count") or 0

    lines.append("DIAGNÓSTICO QUINZENAL")
    lines.append("")
    lines.append("Resumo do período:")
    lines.append(f"- Contas alcançadas: {reach}")
    lines.append(f"- Visualizações/impressões: {impressions}")
    lines.append(f"- Seguidores atuais: {followers}")
    lines.append(f"- Interações totais: {interactions}")
    lines.append(f"- Visitas ao perfil: {profile_views}")
    lines.append(f"- Publicações no período: {posts_count}")

    if reach > 0 and interactions > 0:
        rate = round((interactions / reach) * 100, 2)
        lines.append(f"- Taxa aproximada de interação sobre alcance: {rate}%")
    else:
        lines.append("- Taxa de interação sobre alcance: sem dados suficientes.")

    if previous:
        lines.append("")
        lines.append("Comparativo com a quinzena anterior:")

        checks = [
            ("Alcance", "reach"),
            ("Visualizações", "impressions"),
            ("Interações", "total_interactions"),
            ("Visitas ao perfil", "profile_views"),
            ("Publicações", "posts_count")
        ]

        for label, key in checks:
            curr = current.get(key) or 0
            prev = previous.get(key) or 0
            pct = _aq_percent_change(curr, prev)
            abs_diff = curr - prev

            if pct is None:
                lines.append(f"- {label}: {curr} no período atual. Sem base anterior suficiente para percentual.")
            else:
                sinal = "crescimento" if abs_diff > 0 else "queda" if abs_diff < 0 else "estabilidade"
                lines.append(f"- {label}: {pct}% ({sinal}), variação absoluta de {abs_diff}.")

        curr_followers = current.get("followers_count") or 0
        prev_followers = previous.get("followers_count") or 0
        lines.append(f"- Seguidores: variação de {curr_followers - prev_followers} seguidores.")

    lines.append("")
    lines.append("Leitura estratégica:")

    if posts_count == 0:
        lines.append("- A conta não teve publicações identificadas no período. O principal ponto de atenção é consistência.")
    elif posts_count < 4:
        lines.append("- O volume de publicações foi baixo para uma análise mais robusta. A recomendação é aumentar a frequência com intenção estratégica.")
    else:
        lines.append("- Houve volume de conteúdo suficiente para iniciar leitura de tendência. O próximo passo é observar quais temas e formatos mais puxam alcance e interação.")

    if reach == 0:
        lines.append("- O alcance retornado pela Meta veio zerado ou indisponível. Pode ser limitação da conta, permissão ou ausência de dados no período.")
    elif interactions == 0:
        lines.append("- O conteúdo alcançou pessoas, mas teve baixa resposta de interação. Reforce CTA, salvamento, comentário e contato.")
    else:
        lines.append("- Existe sinal de resposta do público. A estratégia deve reforçar os conteúdos com melhor performance e transformar atenção em ação.")

    if current.get("best_post_caption"):
        lines.append("")
        lines.append("Melhor conteúdo identificado:")
        lines.append(f"- {current.get('best_post_caption')[:260]}")

    lines.append("")
    lines.append("Próximas ações recomendadas:")
    lines.append("- Repetir o tema ou formato do melhor conteúdo da quinzena.")
    lines.append("- Criar pelo menos uma chamada direta para contato, orçamento, agendamento ou conversa.")
    lines.append("- Reforçar stories com prova social, bastidores e CTA.")
    lines.append("- Na próxima quinzena, comparar se o crescimento veio de consistência, tema, formato ou oferta.")

    return "\n".join(lines)


@app.get("/api/acompanhamento-quinzenal/accounts")
def api_acompanhamento_quinzenal_accounts():
    accounts = _aq_get_connected_accounts()

    return {
        "ok": True,
        "accounts": accounts
    }


@app.post("/api/acompanhamento-quinzenal/snapshot")
def api_acompanhamento_quinzenal_snapshot(payload: dict):
    import sqlite3, json, datetime

    _ensure_acompanhamento_quinzenal_tables()

    account_id = payload.get("account_id")
    client_name = payload.get("client_name") or ""
    period_start = payload.get("period_start")
    period_end = payload.get("period_end")

    if not period_start or not period_end:
        today = datetime.date.today()
        period_end = today.isoformat()
        period_start = (today - datetime.timedelta(days=15)).isoformat()

    account = _aq_get_connected_account(account_id)

    token = account.get("page_access_token")
    ig_id = account.get("instagram_business_account_id")

    basic = _aq_fetch_basic_account(ig_id, token)
    insights = _aq_fetch_insights(ig_id, token, period_start, period_end)
    posts = _aq_fetch_media(ig_id, token, period_start, period_end)

    metrics_map = {}

    for metric in insights.get("data", []):
        name = metric.get("name")
        if name:
            metrics_map[name] = _aq_sum_metric(metric)

    total_likes = sum([int(p.get("like_count") or 0) for p in posts])
    total_comments = sum([int(p.get("comments_count") or 0) for p in posts])

    best_post = None
    best_score = -1

    for post in posts:
        score = int(post.get("like_count") or 0) + int(post.get("comments_count") or 0)
        if score > best_score:
            best_score = score
            best_post = post

    current = {
        "followers_count": int(basic.get("followers_count") or 0),
        "media_count": int(basic.get("media_count") or 0),
        "reach": _aq_get_metric(metrics_map, "reach"),
        "impressions": _aq_get_metric(metrics_map, "impressions"),
        "profile_views": _aq_get_metric(metrics_map, "profile_views"),
        "website_clicks": _aq_get_metric(metrics_map, "website_clicks"),
        "total_interactions": _aq_get_metric(metrics_map, "total_interactions"),
        "likes": _aq_get_metric(metrics_map, "likes"),
        "comments": _aq_get_metric(metrics_map, "comments"),
        "shares": _aq_get_metric(metrics_map, "shares"),
        "saves": _aq_get_metric(metrics_map, "saves"),
        "posts_count": len(posts),
        "best_post_id": best_post.get("id") if best_post else None,
        "best_post_caption": best_post.get("caption") if best_post else None,
        "best_post_permalink": best_post.get("permalink") if best_post else None,
        "best_post_metric": best_score if best_post else 0
    }

    # Fallback: se a Meta não retornar total_interactions, usa curtidas + comentários dos posts capturados.
    if current["total_interactions"] == 0:
        current["total_interactions"] = total_likes + total_comments

    if current["likes"] == 0:
        current["likes"] = total_likes

    if current["comments"] == 0:
        current["comments"] = total_comments

    db_path = _aq_get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        username = basic.get("username") or account.get("instagram_username") or ""

        previous = conn.execute("""
            SELECT *
            FROM acompanhamento_quinzenal
            WHERE instagram_username = ?
            ORDER BY period_end DESC, id DESC
            LIMIT 1
        """, (username,)).fetchone()

        previous_dict = dict(previous) if previous else None
        strategic_analysis = _aq_build_analysis(current, previous_dict)

        conn.execute("""
            INSERT INTO acompanhamento_quinzenal (
                account_id,
                client_name,
                page_id,
                page_name,
                instagram_business_account_id,
                instagram_username,
                period_start,
                period_end,
                followers_count,
                media_count,
                reach,
                impressions,
                profile_views,
                website_clicks,
                total_interactions,
                likes,
                comments,
                shares,
                saves,
                posts_count,
                best_post_id,
                best_post_caption,
                best_post_permalink,
                best_post_metric,
                raw_json,
                strategic_analysis
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            account.get("id"),
            client_name or account.get("client_name") or username,
            account.get("page_id"),
            account.get("page_name"),
            ig_id,
            username,
            period_start,
            period_end,
            current["followers_count"],
            current["media_count"],
            current["reach"],
            current["impressions"],
            current["profile_views"],
            current["website_clicks"],
            current["total_interactions"],
            current["likes"],
            current["comments"],
            current["shares"],
            current["saves"],
            current["posts_count"],
            current["best_post_id"],
            current["best_post_caption"],
            current["best_post_permalink"],
            current["best_post_metric"],
            json.dumps({
                "basic": basic,
                "insights": insights,
                "posts": posts
            }, ensure_ascii=False),
            strategic_analysis
        ))

        snapshot_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()

        return {
            "ok": True,
            "message": "Acompanhamento quinzenal salvo com sucesso.",
            "snapshot_id": snapshot_id,
            "account_id": account.get("id"),
            "client_name": client_name or account.get("client_name") or username,
            "instagram_username": username,
            "page_name": account.get("page_name"),
            "period_start": period_start,
            "period_end": period_end,
            "current": current,
            "previous_snapshot_found": bool(previous_dict),
            "strategic_analysis": strategic_analysis
        }

    finally:
        conn.close()


@app.get("/api/acompanhamento-quinzenal/snapshots")
def api_acompanhamento_quinzenal_snapshots(instagram_username: str | None = None):
    import sqlite3

    _ensure_acompanhamento_quinzenal_tables()

    db_path = _aq_get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        if instagram_username:
            username = instagram_username.replace("@", "")
            rows = conn.execute("""
                SELECT *
                FROM acompanhamento_quinzenal
                WHERE instagram_username = ?
                ORDER BY period_end DESC, id DESC
            """, (username,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT *
                FROM acompanhamento_quinzenal
                ORDER BY period_end DESC, id DESC
                LIMIT 80
            """).fetchall()

        return {
            "ok": True,
            "snapshots": [dict(r) for r in rows]
        }

    finally:
        conn.close()


@app.get("/api/acompanhamento-quinzenal/compare")
def api_acompanhamento_quinzenal_compare(instagram_username: str):
    import sqlite3

    _ensure_acompanhamento_quinzenal_tables()

    username = instagram_username.replace("@", "")
    db_path = _aq_get_db_path()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        rows = conn.execute("""
            SELECT *
            FROM acompanhamento_quinzenal
            WHERE instagram_username = ?
            ORDER BY period_end DESC, id DESC
            LIMIT 2
        """, (username,)).fetchall()

        if len(rows) < 2:
            return {
                "ok": False,
                "message": "Ainda não há dois acompanhamentos quinzenais para comparação.",
                "snapshots_found": len(rows)
            }

        current = dict(rows[0])
        previous = dict(rows[1])

        def build_diff(key):
            curr = current.get(key) or 0
            prev = previous.get(key) or 0
            absolute = curr - prev
            percent = None if prev == 0 else round((absolute / prev) * 100, 1)

            return {
                "current": curr,
                "previous": prev,
                "absolute": absolute,
                "percent": percent
            }

        comparison = {
            "followers_count": build_diff("followers_count"),
            "reach": build_diff("reach"),
            "impressions": build_diff("impressions"),
            "profile_views": build_diff("profile_views"),
            "website_clicks": build_diff("website_clicks"),
            "total_interactions": build_diff("total_interactions"),
            "likes": build_diff("likes"),
            "comments": build_diff("comments"),
            "shares": build_diff("shares"),
            "saves": build_diff("saves"),
            "posts_count": build_diff("posts_count")
        }

        return {
            "ok": True,
            "instagram_username": username,
            "current_period": {
                "start": current.get("period_start"),
                "end": current.get("period_end")
            },
            "previous_period": {
                "start": previous.get("period_start"),
                "end": previous.get("period_end")
            },
            "comparison": comparison,
            "current_snapshot": current,
            "previous_snapshot": previous,
            "current_analysis": current.get("strategic_analysis")
        }

    finally:
        conn.close()


ACOMPANHAMENTO_QUINZENAL_HTML = r"""
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Acompanhamento Quinzenal</title>
  <link rel="icon" type="image/png" href="/static/assets/logo-vertice-ia.png">
  <style>
    *{box-sizing:border-box}
    body{
      margin:0;
      background:#05070d;
      color:#f8fafc;
      font-family:Inter,Arial,Helvetica,sans-serif;
    }
    .wrap{
      max-width:1180px;
      margin:0 auto;
      padding:34px 20px 70px;
    }
    .hero{
      border:1px solid rgba(148,163,184,.18);
      border-radius:28px;
      padding:26px;
      background:
        radial-gradient(circle at top right, rgba(245,158,11,.18), transparent 30%),
        linear-gradient(135deg, rgba(15,23,42,.96), rgba(2,6,23,.98));
      box-shadow:0 20px 50px rgba(0,0,0,.28);
      display:flex;
      gap:22px;
      align-items:center;
      justify-content:space-between;
    }
    .brand{
      display:flex;
      gap:18px;
      align-items:center;
    }
    .brand img{
      width:86px;
      height:86px;
      object-fit:contain;
      border-radius:22px;
      background:#fff;
      padding:8px;
      box-shadow:0 12px 28px rgba(0,0,0,.25);
    }
    .eyebrow{
      color:#f5c451;
      font-size:12px;
      text-transform:uppercase;
      letter-spacing:3px;
      font-weight:900;
      margin-bottom:8px;
    }
    h1{
      margin:0;
      font-size:34px;
      line-height:1.08;
    }
    p{
      color:#94a3b8;
      line-height:1.55;
    }
    .grid{
      display:grid;
      grid-template-columns:repeat(4,minmax(0,1fr));
      gap:14px;
      margin-top:18px;
    }
    .card{
      border:1px solid rgba(148,163,184,.16);
      border-radius:22px;
      padding:20px;
      background:rgba(15,23,42,.76);
      box-shadow:0 14px 34px rgba(0,0,0,.18);
    }
    .card small{
      display:block;
      color:#94a3b8;
      margin-bottom:8px;
      font-size:12px;
    }
    .card strong{
      display:block;
      color:#fff;
      font-size:25px;
      word-break:break-word;
    }
    .panel{
      margin-top:18px;
      border:1px solid rgba(148,163,184,.16);
      border-radius:24px;
      padding:22px;
      background:rgba(2,6,23,.74);
    }
    .row{
      display:flex;
      flex-wrap:wrap;
      gap:12px;
      align-items:end;
    }
    label{
      display:block;
      color:#94a3b8;
      font-size:12px;
      margin-bottom:7px;
    }
    input,select,textarea{
      width:100%;
      border-radius:14px;
      border:1px solid rgba(148,163,184,.18);
      background:#020617;
      color:#fff;
      padding:12px;
      outline:none;
      font-family:inherit;
    }
    textarea{
      min-height:190px;
      resize:vertical;
      white-space:pre-wrap;
    }
    .field{
      flex:1;
      min-width:220px;
    }
    button{
      border:0;
      border-radius:14px;
      padding:12px 16px;
      font-weight:900;
      cursor:pointer;
      background:#f5c451;
      color:#111827;
    }
    button.ghost{
      background:transparent;
      color:#f8fafc;
      border:1px solid rgba(148,163,184,.22);
    }
    .status{
      margin-top:14px;
      padding:13px 14px;
      border-radius:16px;
      background:rgba(15,23,42,.82);
      color:#cbd5e1;
      border:1px solid rgba(148,163,184,.16);
      white-space:pre-wrap;
    }
    .status.ok{
      border-color:rgba(34,197,94,.32);
      color:#bbf7d0;
      background:rgba(34,197,94,.08);
    }
    .status.err{
      border-color:rgba(239,68,68,.32);
      color:#fecaca;
      background:rgba(239,68,68,.08);
    }
    table{
      width:100%;
      border-collapse:collapse;
      margin-top:12px;
      overflow:hidden;
      border-radius:18px;
    }
    th,td{
      padding:12px;
      border-bottom:1px solid rgba(148,163,184,.12);
      text-align:left;
      font-size:13px;
      vertical-align:top;
    }
    th{
      color:#f5c451;
      font-size:12px;
      text-transform:uppercase;
      letter-spacing:1px;
    }
    .two{
      display:grid;
      grid-template-columns:1fr 1fr;
      gap:18px;
      margin-top:18px;
    }
    .metricLine{
      display:flex;
      justify-content:space-between;
      gap:14px;
      padding:12px 0;
      border-bottom:1px solid rgba(148,163,184,.12);
    }
    .metricLine span{color:#94a3b8}
    .metricLine b{color:#fff}
    .positive{color:#86efac!important}
    .negative{color:#fca5a5!important}
    .neutral{color:#facc15!important}
    a{color:#f5c451}
    @media(max-width:900px){
      .hero,.brand{flex-direction:column;align-items:flex-start}
      .grid{grid-template-columns:1fr}
      .two{grid-template-columns:1fr}
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <div class="brand">
        <img src="/static/assets/logo-vertice-ia.png" alt="Logo">
        <div>
          <div class="eyebrow">Dashboard do cliente</div>
          <h1>Acompanhamento quinzenal</h1>
          <p>Dados reais da conta conectada pela Meta, salvos a cada 15 dias para acompanhar evolução, alcance, seguidores e interação.</p>
        </div>
      </div>
      <button class="ghost" onclick="location.href='/'">Voltar ao painel</button>
    </section>

    <section class="panel">
      <div class="eyebrow">Conta conectada</div>
      <div class="row">
        <div class="field">
          <label>Cliente conectado</label>
          <select id="accountSelect"></select>
        </div>
        <div class="field">
          <label>Nome do cliente</label>
          <input id="clientName" placeholder="Ex: Espaço TM Pilates">
        </div>
        <div class="field">
          <label>Início do período</label>
          <input id="periodStart" type="date">
        </div>
        <div class="field">
          <label>Fim do período</label>
          <input id="periodEnd" type="date">
        </div>
      </div>
      <div class="row" style="margin-top:14px;">
        <button onclick="gerarSnapshot()">Gerar análise quinzenal</button>
        <button class="ghost" onclick="carregarHistorico()">Atualizar histórico</button>
        <button class="ghost" onclick="compararQuinzenas()">Comparar últimas quinzenas</button>
      </div>
      <div id="status" class="status">Carregando contas conectadas...</div>
    </section>

    <section class="grid">
      <div class="card"><small>Contas alcançadas</small><strong id="mReach">-</strong></div>
      <div class="card"><small>Seguidores</small><strong id="mFollowers">-</strong></div>
      <div class="card"><small>Interações</small><strong id="mInteractions">-</strong></div>
      <div class="card"><small>Posts no período</small><strong id="mPosts">-</strong></div>
    </section>

    <section class="two">
      <div class="panel">
        <div class="eyebrow">Diagnóstico</div>
        <h2 style="margin-top:0;">Análise estratégica</h2>
        <textarea id="analysisBox" readonly placeholder="A análise aparecerá aqui após gerar o acompanhamento."></textarea>
      </div>

      <div class="panel">
        <div class="eyebrow">Comparativo</div>
        <h2 style="margin-top:0;">Últimas quinzenas</h2>
        <div id="compareBox" class="status">Gere pelo menos dois acompanhamentos para comparar.</div>
      </div>
    </section>

    <section class="panel">
      <div class="eyebrow">Histórico salvo</div>
      <h2 style="margin-top:0;">Acompanhamentos quinzenais</h2>
      <div id="historyBox"></div>
    </section>
  </div>

<script>
function $(id){ return document.getElementById(id); }

function setStatus(msg, ok){
  const el = $("status");
  el.textContent = msg;
  el.className = "status " + (ok === true ? "ok" : ok === false ? "err" : "");
}

function fmt(v){
  if(v === null || v === undefined || v === "") return "-";
  const n = Number(v);
  if(Number.isFinite(n)) return n.toLocaleString("pt-BR");
  return String(v);
}

function pctLabel(value){
  if(value === null || value === undefined) return "sem base";
  const cls = value > 0 ? "positive" : value < 0 ? "negative" : "neutral";
  const sign = value > 0 ? "+" : "";
  return `<b class="${cls}">${sign}${value}%</b>`;
}

function setDefaultDates(){
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - 15);

  $("periodEnd").value = end.toISOString().slice(0,10);
  $("periodStart").value = start.toISOString().slice(0,10);
}

async function loadAccounts(){
  try{
    const res = await fetch("/api/acompanhamento-quinzenal/accounts", {credentials:"same-origin"});
    const data = await res.json();

    if(!res.ok) throw new Error(data.detail || "Erro ao carregar contas.");

    const select = $("accountSelect");
    select.innerHTML = "";

    const accounts = data.accounts || [];

    if(!accounts.length){
      select.innerHTML = `<option value="">Nenhuma conta conectada</option>`;
      setStatus("Nenhuma conta Meta conectada. Conecte o cliente pela aba Conectar Cliente Meta.", false);
      return;
    }

    accounts.forEach(acc=>{
      const opt = document.createElement("option");
      opt.value = acc.id;
      opt.textContent = `@${acc.instagram_username || "sem usuário"} — ${acc.page_name || "sem página"}`;
      select.appendChild(opt);
    });

    const first = accounts[0];
    $("clientName").value = first.client_name || first.page_name || first.instagram_username || "";

    setStatus("Conta conectada carregada. Pronto para gerar acompanhamento quinzenal.", true);
    carregarHistorico();

  }catch(e){
    setStatus("Erro ao carregar contas: " + e.message, false);
  }
}

async function gerarSnapshot(){
  const accountId = $("accountSelect").value;
  if(!accountId){
    setStatus("Selecione uma conta conectada.", false);
    return;
  }

  setStatus("Gerando acompanhamento quinzenal com dados reais da Meta...", null);

  try{
    const payload = {
      account_id: Number(accountId),
      client_name: $("clientName").value || "",
      period_start: $("periodStart").value || null,
      period_end: $("periodEnd").value || null
    };

    const res = await fetch("/api/acompanhamento-quinzenal/snapshot", {
      method:"POST",
      credentials:"same-origin",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify(payload)
    });

    const data = await res.json();

    if(!res.ok) throw new Error(JSON.stringify(data.detail || data));

    $("mReach").textContent = fmt(data.current.reach);
    $("mFollowers").textContent = fmt(data.current.followers_count);
    $("mInteractions").textContent = fmt(data.current.total_interactions);
    $("mPosts").textContent = fmt(data.current.posts_count);
    $("analysisBox").value = data.strategic_analysis || "";

    setStatus("Acompanhamento salvo com sucesso. Snapshot ID: " + data.snapshot_id, true);

    await carregarHistorico();
    await compararQuinzenas();

  }catch(e){
    setStatus("Erro ao gerar acompanhamento: " + e.message, false);
  }
}

async function carregarHistorico(){
  try{
    const res = await fetch("/api/acompanhamento-quinzenal/snapshots", {credentials:"same-origin"});
    const data = await res.json();

    if(!res.ok) throw new Error(data.detail || "Erro ao carregar histórico.");

    const rows = data.snapshots || [];

    if(!rows.length){
      $("historyBox").innerHTML = `<div class="status">Ainda não há acompanhamentos salvos.</div>`;
      return;
    }

    $("historyBox").innerHTML = `
      <table>
        <thead>
          <tr>
            <th>Período</th>
            <th>Instagram</th>
            <th>Alcance</th>
            <th>Seguidores</th>
            <th>Interações</th>
            <th>Posts</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map(r=>`
            <tr>
              <td>${r.period_start || "-"} até ${r.period_end || "-"}</td>
              <td>@${r.instagram_username || "-"}</td>
              <td>${fmt(r.reach)}</td>
              <td>${fmt(r.followers_count)}</td>
              <td>${fmt(r.total_interactions)}</td>
              <td>${fmt(r.posts_count)}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    `;

  }catch(e){
    $("historyBox").innerHTML = `<div class="status err">Erro ao carregar histórico: ${e.message}</div>`;
  }
}

async function compararQuinzenas(){
  try{
    const select = $("accountSelect");
    const label = select.options[select.selectedIndex]?.textContent || "";
    const match = label.match(/@([^ —]+)/);
    const username = match ? match[1] : "";

    if(!username){
      $("compareBox").textContent = "Não foi possível identificar o Instagram selecionado.";
      return;
    }

    const res = await fetch("/api/acompanhamento-quinzenal/compare?instagram_username=" + encodeURIComponent(username), {credentials:"same-origin"});
    const data = await res.json();

    if(!data.ok){
      $("compareBox").textContent = data.message || "Ainda não há comparação disponível.";
      return;
    }

    const c = data.comparison || {};

    $("compareBox").innerHTML = `
      <div class="metricLine"><span>Período atual</span><b>${data.current_period.start} até ${data.current_period.end}</b></div>
      <div class="metricLine"><span>Período anterior</span><b>${data.previous_period.start} até ${data.previous_period.end}</b></div>
      <div class="metricLine"><span>Alcance</span>${pctLabel(c.reach.percent)}</div>
      <div class="metricLine"><span>Visualizações</span>${pctLabel(c.impressions.percent)}</div>
      <div class="metricLine"><span>Interações</span>${pctLabel(c.total_interactions.percent)}</div>
      <div class="metricLine"><span>Visitas ao perfil</span>${pctLabel(c.profile_views.percent)}</div>
      <div class="metricLine"><span>Seguidores</span><b>${c.followers_count.absolute > 0 ? "+" : ""}${fmt(c.followers_count.absolute)}</b></div>
      <div class="metricLine"><span>Posts</span><b>${c.posts_count.absolute > 0 ? "+" : ""}${fmt(c.posts_count.absolute)}</b></div>
    `;

  }catch(e){
    $("compareBox").textContent = "Erro ao comparar quinzenas: " + e.message;
  }
}

setDefaultDates();
loadAccounts();
</script>
</body>
</html>
"""


@app.get("/acompanhamento-quinzenal")
def acompanhamento_quinzenal_page():
    from fastapi.responses import HTMLResponse
    return HTMLResponse(ACOMPANHAMENTO_QUINZENAL_HTML)

# ============================================================
# FIM - ACOMPANHAMENTO QUINZENAL COMPLETO
# ============================================================

'''

if "VÉRTICE IA - ACOMPANHAMENTO QUINZENAL COMPLETO" not in s:
    s += patch
else:
    print("Patch já existia. Nenhuma duplicação feita.")

p.write_text(s, encoding="utf-8")

print("Acompanhamento Quinzenal completo instalado no backend.")
