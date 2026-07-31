from pathlib import Path
import re

app_path = Path("backend/app.py")
s = app_path.read_text(encoding="utf-8")

Path("backend/app_backup_antes_leitura_automatica_perfil.py").write_text(s, encoding="utf-8")

# Garante import re
if "import os, json, sqlite3, re" not in s and "import os, json, sqlite3" in s:
    s = s.replace("import os, json, sqlite3", "import os, json, sqlite3, re")

endpoint = r'''
# ==============================
# LEITURA AUTOMÁTICA DE PERFIL POR LINK/@ - VÉRTICE IA
# ==============================

def _vertice_clean_profile_input(value: str):
    value = (value or "").strip()

    value = value.replace("https://www.instagram.com/", "")
    value = value.replace("http://www.instagram.com/", "")
    value = value.replace("https://instagram.com/", "")
    value = value.replace("http://instagram.com/", "")
    value = value.replace("www.instagram.com/", "")
    value = value.replace("instagram.com/", "")
    value = value.replace("@", "")
    value = value.split("?")[0]
    value = value.split("/")[0]
    value = value.strip()

    return value

def _vertice_public_profile_analysis(profile, posts):
    profile = profile or {}
    posts = posts or []

    bio = profile.get("biography") or ""
    bio_l = bio.lower()

    total_likes = sum(int(p.get("like_count") or 0) for p in posts)
    total_comments = sum(int(p.get("comments_count") or 0) for p in posts)
    avg_likes = round(total_likes / len(posts), 2) if posts else 0
    avg_comments = round(total_comments / len(posts), 2) if posts else 0

    has_cta = bool(re.search(r"agende|chame|link|whatsapp|direct|contato|orçamento|orcamento|clique|reserve|compre", bio_l))
    has_positioning = len(bio.strip()) >= 70
    has_location = bool(re.search(r"sp|mg|rj|go|brasil|online|presencial|cidade|bairro|região|regiao", bio_l))
    has_offer = bool(re.search(r"serviço|servico|aula|consulta|produto|método|metodo|plano|cardápio|cardapio|tratamento|mentoria", bio_l))

    captions = " ".join([(p.get("caption") or "").lower() for p in posts])

    content_education = len(re.findall(r"dica|como|erro|passo|guia|benefício|beneficio|aprenda|entenda|motivo", captions))
    content_authority = len(re.findall(r"resultado|cliente|depoimento|feedback|antes|depois|profissional|especialista|experiência|experiencia", captions))
    content_offer = len(re.findall(r"agenda|agende|promoção|promocao|valor|preço|preco|comprar|pedido|orçamento|orcamento|vaga", captions))

    ranked = sorted(
        posts,
        key=lambda p: (int(p.get("comments_count") or 0) * 4) + int(p.get("like_count") or 0),
        reverse=True
    )

    def compact_post(p):
        cap = (p.get("caption") or "Publicação sem legenda").replace("\n", " ").strip()
        return {
            "id": p.get("id"),
            "caption": cap[:220] + ("..." if len(cap) > 220 else ""),
            "media_type": p.get("media_type"),
            "permalink": p.get("permalink"),
            "timestamp": p.get("timestamp"),
            "like_count": int(p.get("like_count") or 0),
            "comments_count": int(p.get("comments_count") or 0)
        }

    strengths = []

    if has_positioning:
        strengths.append("A bio possui volume suficiente para comunicar o posicionamento.")
    if has_cta:
        strengths.append("A bio possui chamada para ação ou caminho de contato.")
    if has_offer:
        strengths.append("A bio sinaliza serviço, produto ou oferta principal.")
    if has_location:
        strengths.append("A bio indica localização, atendimento presencial ou online.")
    if posts:
        strengths.append(f"Foram localizados {len(posts)} posts públicos recentes para leitura inicial.")
    if total_comments > 0:
        strengths.append("Existem comentários nos posts recentes, sinal de conversa e resposta do público.")
    if content_authority > 0:
        strengths.append("Há sinais de conteúdo de autoridade/prova social nas legendas.")
    if content_education > 0:
        strengths.append("Há sinais de conteúdo educativo nas legendas.")

    if not strengths:
        strengths.append("O perfil possui presença pública, mas ainda precisa fortalecer clareza e sinais estratégicos.")

    adjustments = []

    if not has_positioning:
        adjustments.append("A bio precisa deixar mais claro o que o negócio faz, para quem faz e qual transformação entrega.")
    if not has_cta:
        adjustments.append("Adicionar CTA direto na bio: chamar no WhatsApp, agendar, pedir orçamento ou acessar o link.")
    if not has_offer:
        adjustments.append("Deixar a oferta principal mais visível na bio.")
    if not has_location:
        adjustments.append("Adicionar localização, região atendida ou informação de atendimento online/presencial.")
    if not posts:
        adjustments.append("Não foi possível ler posts recentes. Verifique se o perfil é público e profissional.")
    if content_education == 0:
        adjustments.append("Criar mais posts educativos: dicas, erros comuns, passo a passo e benefícios.")
    if content_authority == 0:
        adjustments.append("Adicionar mais prova de autoridade: resultados, feedbacks, bastidores profissionais e diferenciais.")
    if content_offer == 0:
        adjustments.append("Inserir conteúdos de oferta de forma estratégica, sem transformar o perfil apenas em vitrine.")

    posts_reading = []

    posts_reading.append(f"Foram analisados {len(posts)} posts públicos recentes.")
    posts_reading.append(f"Total público observado: {total_likes} curtidas e {total_comments} comentários.")
    posts_reading.append(f"Média por post: {avg_likes} curtidas e {avg_comments} comentários.")

    if ranked:
        top = ranked[0]
        top_caption = (top.get("caption") or "Publicação sem legenda").replace("\n", " ").strip()
        posts_reading.append(f"Post com maior resposta pública: {top_caption[:180]}")

    if content_education > content_offer and content_education > content_authority:
        posts_reading.append("O perfil demonstra tendência maior para conteúdo educativo.")
    elif content_authority > content_education and content_authority > content_offer:
        posts_reading.append("O perfil demonstra tendência maior para autoridade/prova social.")
    elif content_offer > 0:
        posts_reading.append("O perfil possui sinais de conteúdo de oferta, mas precisa equilibrar com autoridade e valor.")

    recommendations = [
        "Revisar a bio para comunicar posicionamento, diferencial e CTA em poucos segundos.",
        "Manter os destaques como etapa manual/visual, pois a Meta não entrega destaques de outro perfil via link.",
        "Usar os posts com mais curtidas e comentários como base para novos conteúdos.",
        "Adicionar prints do painel profissional para complementar a leitura pública com dados internos.",
        "Transformar os melhores temas em conteúdos educativos, provas sociais e chamadas para ação."
    ]

    return {
        "profile_summary": {
            "username": profile.get("username"),
            "name": profile.get("name"),
            "biography": bio,
            "website": profile.get("website"),
            "followers_count": int(profile.get("followers_count") or 0),
            "media_count": int(profile.get("media_count") or 0)
        },
        "posts_reading": "\n".join(posts_reading),
        "strengths": strengths,
        "adjustments": adjustments,
        "recommendations": recommendations,
        "top_posts": [compact_post(p) for p in ranked[:6]],
        "manual_needed": {
            "destaques": "Destaques não são entregues automaticamente pela Meta para perfil de terceiros. Inserir manualmente ou por print.",
            "prints": "Prints do painel profissional continuam necessários para alcance, salvos, compartilhamentos e insights internos."
        }
    }

@app.get("/api/profile-public-analysis")
def api_profile_public_analysis(profile: str, limit: int = Query(12, ge=1, le=25)):
    version = os.getenv("META_API_VERSION", "v25.0").strip()
    token = os.getenv("FACEBOOK_ACCESS_TOKEN", "").strip()
    page_id = os.getenv("FACEBOOK_PAGE_ID", "").strip()

    username = _vertice_clean_profile_input(profile)

    if not username:
        raise HTTPException(status_code=400, detail="Informe o link ou @ do perfil do cliente.")

    if not token:
        raise HTTPException(status_code=400, detail="FACEBOOK_ACCESS_TOKEN não configurado.")

    if not page_id:
        raise HTTPException(status_code=400, detail="FACEBOOK_PAGE_ID não configurado.")

    page_url = f"https://graph.facebook.com/{version}/{page_id}"
    page_params = {
        "fields": "id,name,instagram_business_account{id,username,name}",
        "access_token": token
    }

    page_response = requests.get(page_url, params=page_params, timeout=25)
    page_data = page_response.json()

    if not page_response.ok:
        raise HTTPException(status_code=400, detail={
            "message": "Erro ao validar a página base da VÉRTICE IA.",
            "meta": page_data
        })

    ig_base = page_data.get("instagram_business_account")

    if not ig_base or not ig_base.get("id"):
        raise HTTPException(status_code=400, detail="A página base não possui Instagram profissional conectado.")

    ig_base_id = ig_base["id"]

    primary_fields = (
        f"business_discovery.username({username})"
        "{id,username,name,biography,website,followers_count,media_count,"
        f"media.limit({limit})"
        "{id,caption,media_type,permalink,timestamp,like_count,comments_count}}"
    )

    fallback_fields = (
        f"business_discovery.username({username})"
        "{id,username,name,followers_count,media_count,"
        f"media.limit({limit})"
        "{id,caption,media_type,permalink,timestamp,like_count,comments_count}}"
    )

    url = f"https://graph.facebook.com/{version}/{ig_base_id}"

    def call(fields):
        return requests.get(
            url,
            params={
                "fields": fields,
                "access_token": token
            },
            timeout=30
        )

    response = call(primary_fields)
    data = response.json()

    if not response.ok:
        response = call(fallback_fields)
        data = response.json()

    if not response.ok:
        raise HTTPException(status_code=400, detail={
            "message": "Não foi possível automatizar a leitura desse perfil.",
            "username": username,
            "meta": data,
            "possiveis_motivos": [
                "O perfil não é Business ou Creator.",
                "O perfil é privado.",
                "O @ foi digitado errado.",
                "A Meta não liberou esse perfil via Business Discovery.",
                "O token atual não possui permissão suficiente."
            ],
            "alternativa": "Use a análise manual e insira prints do perfil/painel profissional."
        })

    bd = data.get("business_discovery")

    if not bd:
        raise HTTPException(status_code=404, detail={
            "message": "Perfil não localizado via Meta Business Discovery.",
            "username": username,
            "alternativa": "Preencha manualmente bio, destaques e prints."
        })

    media = ((bd.get("media") or {}).get("data") or [])

    posts = []
    for m in media:
        posts.append({
            "id": m.get("id"),
            "caption": m.get("caption") or "",
            "media_type": m.get("media_type") or "",
            "permalink": m.get("permalink") or "",
            "timestamp": m.get("timestamp") or "",
            "like_count": int(m.get("like_count") or 0),
            "comments_count": int(m.get("comments_count") or 0)
        })

    profile_obj = {
        "id": bd.get("id"),
        "username": bd.get("username"),
        "name": bd.get("name"),
        "biography": bd.get("biography") or "",
        "website": bd.get("website") or "",
        "followers_count": int(bd.get("followers_count") or 0),
        "media_count": int(bd.get("media_count") or 0)
    }

    return {
        "status": "sucesso",
        "modo": "analise_publica_automatica",
        "fonte": "Meta Business Discovery",
        "aviso": "Leitura pública. Não inclui destaques, alcance, salvos, compartilhamentos ou painel profissional.",
        "profile": profile_obj,
        "posts": posts,
        "analysis": _vertice_public_profile_analysis(profile_obj, posts)
    }
'''

if "LEITURA AUTOMÁTICA DE PERFIL POR LINK/@" not in s:
    m = re.search(r'\napp\.mount\(', s)
    if not m:
        raise RuntimeError("Não encontrei ponto seguro para inserir o endpoint.")
    s = s[:m.start()] + "\n" + endpoint + "\n" + s[m.start():]

app_path.write_text(s, encoding="utf-8")


index_path = Path("backend/static/index.html")
html = index_path.read_text(encoding="utf-8")

Path("backend/static/index_backup_antes_leitura_automatica_perfil.html").write_text(html, encoding="utf-8")

auto_js = r'''
async function buscarPerfilClienteAutomatico(){
  const raw = pcGet("pcInstagram");

  if(!raw){
    show("Cole o link ou @ do perfil do cliente no campo Instagram.");
    return;
  }

  try{
    show("Buscando perfil público e lendo posts recentes...", "success");

    const data = await api(`/api/profile-public-analysis?profile=${encodeURIComponent(raw)}&limit=12`);
    const profile = data.profile || {};
    const analysis = data.analysis || {};

    pcSet("pcNome", profile.name || profile.username || "");
    pcSet("pcInstagram", profile.username ? "@" + profile.username : raw);
    pcSet("pcBio", profile.biography || "");

    if(!pcGet("pcDestaques")){
      pcSet(
        "pcDestaques",
        "Destaques não foram lidos automaticamente. Inserir manualmente ou adicionar print dos destaques."
      );
    }

    pcSet("pcPosts", analysis.posts_reading || "");

    pcSet("pcForcas", (analysis.strengths || []).map(x => "- " + x).join("\\n"));
    pcSet("pcAjustes", (analysis.adjustments || []).map(x => "- " + x).join("\\n"));
    pcSet("pcObs", (analysis.recommendations || []).map(x => "- " + x).join("\\n"));

    savePerfilCliente();

    let topPostsHtml = "";

    if((analysis.top_posts || []).length){
      topPostsHtml = `
        <div class="card">
          <div class="eyebrow">Posts lidos automaticamente</div>
          <h2>Posts com maior resposta pública</h2>
          ${(analysis.top_posts || []).map((p, i) => `
            <div class="item">
              <div class="row">
                <span class="badge gold">#${i + 1}</span>
                <span class="badge">${pcEscape(p.media_type || "")}</span>
                <span class="badge green">${fmt(p.like_count || 0)} curtidas</span>
                <span class="badge blue">${fmt(p.comments_count || 0)} comentários</span>
              </div>
              <div class="postTitle">${pcEscape(p.caption || "Publicação sem legenda")}</div>
              ${p.permalink ? `<a href="${p.permalink}" target="_blank">Abrir post</a>` : ""}
            </div>
          `).join("")}
        </div>
        <br>
      `;
    }

    const box = document.getElementById("perfilClienteResultado");

    if(box){
      box.innerHTML = `
        <div class="alert success">
          Perfil localizado automaticamente via dados públicos. A bio e os posts recentes foram preenchidos.
          Destaques e painel profissional ainda precisam ser inseridos manualmente ou por prints.
        </div>

        <div class="card gold">
          <div class="between">
            <div>
              <div class="eyebrow">Perfil localizado</div>
              <h2>@${pcEscape(profile.username || "")}</h2>
              <p class="muted">${pcEscape(profile.name || "")}</p>
            </div>
            <span class="badge gold">Leitura pública</span>
          </div>

          <div class="grid four">
            <div class="stat gold"><small>Seguidores</small><strong>${fmt(profile.followers_count || 0)}</strong></div>
            <div class="stat"><small>Total de posts</small><strong>${fmt(profile.media_count || 0)}</strong></div>
            <div class="stat"><small>Posts lidos</small><strong>${fmt((data.posts || []).length)}</strong></div>
            <div class="stat"><small>Fonte</small><strong>Meta</strong></div>
          </div>

          <div class="reportBlock">
            <h3>Limite da leitura automática</h3>
            <p>${pcEscape(data.aviso || "")}</p>
          </div>
        </div>

        <br>

        ${topPostsHtml}

        <div class="empty">
          Agora revise os campos preenchidos, adicione prints do painel profissional e clique em
          <strong>Gerar análise do perfil</strong>.
        </div>
      `;
    }

    show("Leitura automática concluída. Revise os campos e gere a análise.", "success");

  }catch(e){
    show(e.message);
  }
}
'''

if "function buscarPerfilClienteAutomatico()" not in html:
    html = html.replace("function renderPerfilCliente(){", auto_js + "\nfunction renderPerfilCliente(){")

# Adiciona botão na aba Perfil Cliente
if 'onclick="buscarPerfilClienteAutomatico()"' not in html:
    html = html.replace(
        '<button class="btn" onclick="gerarAnalisePerfilCliente()">Gerar análise do perfil</button>',
        '<button class="btn" onclick="buscarPerfilClienteAutomatico()">Buscar perfil pelo link/@</button>\n        <button class="btn secondary" onclick="gerarAnalisePerfilCliente()">Gerar análise do perfil</button>'
    )

# Ajusta placeholder do Instagram
html = html.replace(
    'placeholder="Ex: @espacotmpilates"',
    'placeholder="Ex: @espacotmpilates ou https://instagram.com/espacotmpilates"'
)

index_path.write_text(html, encoding="utf-8")

print("Leitura automática por link/@ adicionada na aba Perfil Cliente.")
print("Novo botão: Buscar perfil pelo link/@")
print("Novo endpoint: /api/profile-public-analysis")
