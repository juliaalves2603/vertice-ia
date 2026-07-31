from pathlib import Path
import re

app_path = Path("backend/app.py")
s = app_path.read_text(encoding="utf-8")

Path("backend/app_backup_antes_cliente_por_arroba.py").write_text(s, encoding="utf-8")

client_endpoint = r'''
# ==============================
# RELATÓRIO DE CLIENTE POR @ - VÉRTICE IA
# ==============================

def _clean_ig_username(value: str):
    value = (value or "").strip()
    value = value.replace("https://www.instagram.com/", "")
    value = value.replace("http://www.instagram.com/", "")
    value = value.replace("https://instagram.com/", "")
    value = value.replace("http://instagram.com/", "")
    value = value.replace("/", "")
    value = value.replace("@", "")
    return value.strip()

def _public_score(likes, comments, followers):
    likes = int(likes or 0)
    comments = int(comments or 0)
    followers = int(followers or 0)

    interaction = likes + (comments * 4)

    if followers > 0:
        rate = (interaction / followers) * 100
        score = min(100, round(rate * 12, 2))
    else:
        score = min(100, round((likes * 0.05) + (comments * 2), 2))

    return score

def _public_client_strategy(posts, profile):
    posts = posts or []
    followers = int(profile.get("followers_count") or 0)

    total_likes = sum(int(p.get("like_count") or 0) for p in posts)
    total_comments = sum(int(p.get("comments_count") or 0) for p in posts)
    total_interactions = total_likes + total_comments

    avg_likes = round(total_likes / len(posts), 2) if posts else 0
    avg_comments = round(total_comments / len(posts), 2) if posts else 0

    ranked = sorted(
        posts,
        key=lambda p: (
            float(p.get("potential_score") or 0),
            int(p.get("comments_count") or 0),
            int(p.get("like_count") or 0)
        ),
        reverse=True
    )

    def compact(p):
        caption = (p.get("caption") or "Publicação sem legenda").replace("\n", " ").strip()
        return {
            "id": p.get("id"),
            "caption": caption[:180] + ("..." if len(caption) > 180 else ""),
            "media_type": p.get("media_type"),
            "timestamp": p.get("timestamp"),
            "permalink": p.get("permalink"),
            "like_count": int(p.get("like_count") or 0),
            "comments_count": int(p.get("comments_count") or 0),
            "potential_score": float(p.get("potential_score") or 0),
            "decisao": p.get("decisao") or {}
        }

    repetir = ranked[:5]
    ajustar = sorted(
        posts,
        key=lambda p: (
            int(p.get("comments_count") or 0),
            int(p.get("like_count") or 0)
        )
    )[:5]

    formatos = {}
    for p in posts:
        fmt = p.get("media_type") or "UNKNOWN"
        formatos.setdefault(fmt, {
            "formato": fmt,
            "posts": 0,
            "curtidas": 0,
            "comentarios": 0,
            "potencial_total": 0
        })
        formatos[fmt]["posts"] += 1
        formatos[fmt]["curtidas"] += int(p.get("like_count") or 0)
        formatos[fmt]["comentarios"] += int(p.get("comments_count") or 0)
        formatos[fmt]["potencial_total"] += float(p.get("potential_score") or 0)

    formatos_lista = []
    for f in formatos.values():
        f["media_curtidas"] = round(f["curtidas"] / f["posts"], 2) if f["posts"] else 0
        f["media_comentarios"] = round(f["comentarios"] / f["posts"], 2) if f["posts"] else 0
        f["media_potencial"] = round(f["potencial_total"] / f["posts"], 2) if f["posts"] else 0
        formatos_lista.append(f)

    formatos_lista = sorted(formatos_lista, key=lambda x: x["media_potencial"], reverse=True)

    if not posts:
        resumo = "Não foi possível localizar publicações recentes para esse perfil."
        diagnostico = "Verifique se o perfil é profissional, público e se o @ foi digitado corretamente."
    elif repetir:
        resumo = "O perfil do cliente foi localizado e possui publicações públicas suficientes para uma leitura inicial."
        diagnostico = "Esta análise usa dados públicos. Para métricas completas como alcance, salvos e compartilhamentos, o cliente precisa conectar a própria conta."
    else:
        resumo = "O perfil foi localizado, mas a base pública ainda é limitada."
        diagnostico = "A análise pública serve como diagnóstico inicial, não substitui insights completos da conta."

    plano_7_dias = [
        "Dia 1: repetir o tema da publicação com maior curtida/comentário usando novo gancho.",
        "Dia 2: transformar o melhor conteúdo em stories com enquete ou caixinha.",
        "Dia 3: criar conteúdo salvável: checklist, passo a passo ou erros comuns.",
        "Dia 4: publicar prova de autoridade ou bastidor ligado ao melhor tema.",
        "Dia 5: criar uma variação em Reels com CTA mais direto.",
        "Dia 6: observar curtidas, comentários e respostas antes de decidir tráfego.",
        "Dia 7: gerar nova análise e comparar os posts mais fortes."
    ]

    texto_cliente = (
        f"Análise pública do perfil @{profile.get('username')}: foram avaliadas {len(posts)} publicações recentes, "
        f"com {total_likes} curtidas e {total_comments} comentários no total. "
        "Esta leitura identifica temas e formatos com melhor resposta pública, mas não substitui os insights internos da conta. "
        "Para uma análise completa de alcance, salvamentos, compartilhamentos e evolução real, é necessário conectar a conta profissional do cliente à VÉRTICE IA."
    )

    return {
        "modo": "cliente_por_arroba_publico",
        "aviso": "Análise pública via Business Discovery. Não inclui alcance, salvos ou compartilhamentos.",
        "resumo_executivo": resumo,
        "diagnostico": diagnostico,
        "profile": profile,
        "totais": {
            "posts": len(posts),
            "seguidores": followers,
            "media_count": int(profile.get("media_count") or 0),
            "curtidas": total_likes,
            "comentarios": total_comments,
            "interacoes_publicas": total_interactions,
            "media_curtidas": avg_likes,
            "media_comentarios": avg_comments,
            "alcance": 0,
            "salvos": 0,
            "compartilhamentos": 0,
            "media_potencial": round(sum(float(p.get("potential_score") or 0) for p in posts) / len(posts), 2) if posts else 0
        },
        "formatos": formatos_lista,
        "melhor_formato": formatos_lista[0] if formatos_lista else None,
        "melhores_por_potencial": [compact(p) for p in ranked[:8]],
        "melhores_por_alcance": [],
        "conteudos_de_valor": [compact(p) for p in ranked[:5]],
        "indicados_para_trafego": [],
        "repetir": [compact(p) for p in repetir],
        "ajustar_antes_de_impulsionar": [compact(p) for p in ajustar],
        "nao_impulsionar": [],
        "plano_7_dias": plano_7_dias,
        "texto_cliente": texto_cliente,
        "alertas": [
            "Esta análise por @ usa apenas dados públicos.",
            "Alcance, salvamentos e compartilhamentos só aparecem quando a conta do cliente estiver conectada com permissão.",
            "Use esta leitura como diagnóstico inicial ou pré-proposta."
        ]
    }

@app.get("/api/client-discovery")
def api_client_discovery(username: str, limit: int = Query(25, ge=1, le=50)):
    version = os.getenv("META_API_VERSION", "v25.0").strip()
    token = os.getenv("FACEBOOK_ACCESS_TOKEN", "").strip()
    page_id = os.getenv("FACEBOOK_PAGE_ID", "").strip()

    username = _clean_ig_username(username)

    if not username:
        raise HTTPException(status_code=400, detail="Informe o @ do cliente.")

    if not token:
        raise HTTPException(status_code=400, detail="FACEBOOK_ACCESS_TOKEN não configurado.")

    if not page_id:
        raise HTTPException(status_code=400, detail="FACEBOOK_PAGE_ID não configurado.")

    # Primeiro localiza o Instagram profissional conectado à página da Júlia.
    page_url = f"https://graph.facebook.com/{version}/{page_id}"
    page_params = {
        "fields": "id,name,instagram_business_account{id,username,name}",
        "access_token": token
    }

    page_response = requests.get(page_url, params=page_params, timeout=25)
    page_data = page_response.json()

    if not page_response.ok:
        raise HTTPException(status_code=400, detail={
            "message": "Erro ao validar página base da VÉRTICE IA.",
            "meta": page_data
        })

    ig_base = page_data.get("instagram_business_account")

    if not ig_base or not ig_base.get("id"):
        raise HTTPException(status_code=400, detail="A página base não possui Instagram profissional conectado.")

    ig_base_id = ig_base["id"]

    fields = (
        f"business_discovery.username({username})"
        "{id,username,name,profile_picture_url,followers_count,media_count,"
        f"media.limit({limit})"
        "{id,caption,media_type,media_url,permalink,timestamp,like_count,comments_count}}"
    )

    url = f"https://graph.facebook.com/{version}/{ig_base_id}"
    params = {
        "fields": fields,
        "access_token": token
    }

    r = requests.get(url, params=params, timeout=30)
    data = r.json()

    if not r.ok:
        raise HTTPException(status_code=400, detail={
            "message": "Não foi possível localizar o perfil do cliente.",
            "username": username,
            "meta": data,
            "possiveis_motivos": [
                "O perfil não é Business ou Creator.",
                "O perfil é privado.",
                "O @ foi digitado errado.",
                "A Meta limitou o acesso via Business Discovery."
            ]
        })

    bd = data.get("business_discovery")

    if not bd:
        raise HTTPException(status_code=404, detail={
            "message": "Perfil não localizado via Business Discovery.",
            "username": username,
            "possiveis_motivos": [
                "Conta pessoal não profissional.",
                "Conta privada.",
                "Username incorreto."
            ]
        })

    followers = int(bd.get("followers_count") or 0)
    media = ((bd.get("media") or {}).get("data") or [])

    posts = []

    for m in media:
        likes = int(m.get("like_count") or 0)
        comments = int(m.get("comments_count") or 0)
        score = _public_score(likes, comments, followers)

        if score >= 55:
            decisao = {
                "status": "repetir_organico",
                "badge": "Repetir tema",
                "reason": "Publicação com bom sinal público de curtidas/comentários.",
                "next_step": "Criar nova versão com gancho mais direto e CTA."
            }
        elif comments > 0:
            decisao = {
                "status": "gerou_conversa",
                "badge": "Gerou conversa",
                "reason": "A publicação recebeu comentários e pode indicar interesse do público.",
                "next_step": "Responder dúvidas e transformar o tema em conteúdo educativo."
            }
        else:
            decisao = {
                "status": "ajustar",
                "badge": "Ajustar",
                "reason": "Baixa resposta pública em curtidas/comentários.",
                "next_step": "Melhorar gancho, clareza da promessa e chamada para ação."
            }

        posts.append({
            "id": m.get("id"),
            "caption": m.get("caption") or "",
            "media_type": m.get("media_type") or "",
            "media_url": m.get("media_url") or "",
            "permalink": m.get("permalink") or "",
            "timestamp": m.get("timestamp") or "",
            "like_count": likes,
            "comments_count": comments,
            "reach": 0,
            "saved": 0,
            "shares": 0,
            "potential_score": score,
            "decisao": decisao
        })

    profile = {
        "id": bd.get("id"),
        "username": bd.get("username"),
        "name": bd.get("name"),
        "profile_picture_url": bd.get("profile_picture_url"),
        "followers_count": followers,
        "media_count": bd.get("media_count")
    }

    return {
        "status": "sucesso",
        "modo": "cliente_por_arroba_publico",
        "fonte": "Meta Business Discovery",
        "aviso": "Dados públicos. Não inclui alcance, salvos ou compartilhamentos.",
        "perfil_base": ig_base,
        "profile": profile,
        "data": posts
    }

@app.get("/api/client-advanced-report")
def api_client_advanced_report(username: str, limit: int = Query(25, ge=1, le=50)):
    discovery = api_client_discovery(username=username, limit=limit)

    return {
        "status": "sucesso",
        "modo": "cliente_por_arroba_publico",
        "fonte": "Meta Business Discovery",
        "profile": discovery.get("profile"),
        "data": discovery.get("data", []),
        "advanced_report": _public_client_strategy(
            discovery.get("data", []),
            discovery.get("profile", {})
        )
    }
'''

if "RELATÓRIO DE CLIENTE POR @ - VÉRTICE IA" not in s:
    m = re.search(r'\napp\.mount\(', s)
    if not m:
        raise RuntimeError("Não encontrei ponto seguro para inserir o relatório por @.")
    s = s[:m.start()] + "\n" + client_endpoint + "\n" + s[m.start():]

app_path.write_text(s, encoding="utf-8")


index_path = Path("backend/static/index.html")
html = index_path.read_text(encoding="utf-8")

Path("backend/static/index_backup_antes_cliente_por_arroba.html").write_text(html, encoding="utf-8")

# Troca o botão para deixar claro que agora busca o @ do cliente quando preenchido
html = html.replace(
    '<button class="btn" onclick="loadAdvanced()">Gerar relatório estratégico</button>',
    '<button class="btn" onclick="loadAdvanced()">Gerar relatório estratégico</button>\n          <button class="btn secondary" onclick="testClientDiscovery()">Localizar @ cliente</button>'
)

client_js = r'''
function getClientUsernameForDiscovery(){
  const data = typeof getClientReportData === "function" ? getClientReportData() : {};
  let username = (data.instagram || "").trim();

  username = username
    .replace("https://www.instagram.com/", "")
    .replace("http://www.instagram.com/", "")
    .replace("https://instagram.com/", "")
    .replace("http://instagram.com/", "")
    .replaceAll("/", "")
    .replace("@", "")
    .trim();

  return username;
}

async function testClientDiscovery(){
  const username = getClientUsernameForDiscovery();

  if(!username){
    show("Preencha o Instagram do cliente nos Dados do cliente. Exemplo: @espacotmpilates");
    return;
  }

  try{
    show("Localizando perfil do cliente via Meta Business Discovery...", "success");

    const data = await api(`/api/client-discovery?username=${encodeURIComponent(username)}&limit=12`);

    const profile = data.profile || {};

    show(`Perfil localizado: @${profile.username || username}. Dados públicos carregados.`, "success");

    const content = `
      <div class="card gold">
        <div class="eyebrow">Cliente localizado</div>
        <h2>@${safe(profile.username || username)}</h2>
        <p class="muted">Fonte: ${safe(data.fonte || "Meta Business Discovery")}. ${safe(data.aviso || "")}</p>

        <div class="grid four">
          <div class="stat gold"><small>Seguidores</small><strong>${fmt(profile.followers_count || 0)}</strong></div>
          <div class="stat"><small>Total de posts</small><strong>${fmt(profile.media_count || 0)}</strong></div>
          <div class="stat"><small>Posts lidos</small><strong>${fmt((data.data || []).length)}</strong></div>
          <div class="stat"><small>Modo</small><strong>Público</strong></div>
        </div>

        <br>

        <div class="reportBlock">
          <h3>Aviso importante</h3>
          <p>Essa análise por @ usa dados públicos. Para puxar alcance, salvos e compartilhamentos reais, o cliente precisa conectar a própria conta profissional à VÉRTICE IA.</p>
        </div>
      </div>
    `;

    const box = $("advancedContent");
    if(box) box.innerHTML = content + "<br>" + box.innerHTML;

  }catch(e){
    show(e.message);
  }
}
'''

if "function getClientUsernameForDiscovery()" not in html:
    html = html.replace("function postListHtml(list, emptyMsg){", client_js + "\nfunction postListHtml(list, emptyMsg){")

# Substitui loadAdvanced para usar o @ quando estiver preenchido
new_load_advanced = r'''
async function loadAdvanced(){
  try{
    const username = getClientUsernameForDiscovery();

    if(username){
      show(`Gerando relatório estratégico público para @${username}...`, "success");
      const data = await api(`/api/client-advanced-report?username=${encodeURIComponent(username)}&limit=25`);
      state.advanced = data.advanced_report;

      if(typeof saveClientReportData === "function"){
        saveClientReportData();
      }

      $("advancedContent").innerHTML = advancedHtml(state.advanced);

      show(`Relatório do cliente @${username} gerado. Atenção: análise pública, sem alcance/salvos/shares.`, "success");
      return;
    }

    show("Gerando relatório estratégico com dados reais da conta conectada...", "success");
    const data = await api("/api/advanced-report?limit=50");
    state.advanced = data.advanced_report;
    $("advancedContent").innerHTML = advancedHtml(state.advanced);
    show("Relatório estratégico gerado.", "success");

  }catch(e){
    show(e.message);
  }
}
'''

html = re.sub(
    r'async function loadAdvanced\(\)\{[\s\S]*?\n\}',
    new_load_advanced,
    html,
    count=1
)

# Ajusta advancedHtml para mostrar aviso do modo público
html = html.replace(
    '<div class="grid four">\n      <div class="stat gold"><small>Posts analisados</small><strong>${fmt(t.posts)}</strong><div class="hint">Base atual</div></div>',
    '''${r.modo === "cliente_por_arroba_publico" ? `
      <div class="alert success">
        Relatório gerado por @ do cliente via dados públicos. Não inclui alcance, salvos ou compartilhamentos.
      </div>
      <br>
    ` : ""}

    <div class="grid four">
      <div class="stat gold"><small>Posts analisados</small><strong>${fmt(t.posts)}</strong><div class="hint">Base atual</div></div>'''
)

# Ajusta exportação para não quebrar se totals usar seguidores/interações
html = html.replace(
    '<div class="card"><small>Alcance</small><strong>${fmt(t.alcance)}</strong></div>',
    '<div class="card"><small>${t.seguidores ? "Seguidores" : "Alcance"}</small><strong>${fmt(t.seguidores || t.alcance || 0)}</strong></div>'
)

html = html.replace(
    '<div class="card"><small>Salvos</small><strong>${fmt(t.salvos)}</strong></div>',
    '<div class="card"><small>${t.interacoes_publicas ? "Interações" : "Salvos"}</small><strong>${fmt(t.interacoes_publicas || t.salvos || 0)}</strong></div>'
)

index_path.write_text(html, encoding="utf-8")

print("Busca de relatório por @ do cliente adicionada.")
print("Novos endpoints:")
print("- /api/client-discovery?username=cliente")
print("- /api/client-advanced-report?username=cliente")
