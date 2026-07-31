from pathlib import Path
import re

app_path = Path("backend/app.py")
s = app_path.read_text(encoding="utf-8")

Path("backend/app_backup_antes_analise_sem_achismo.py").write_text(s, encoding="utf-8")

new_function = r'''
def _vertice_public_profile_analysis(profile, posts):
    import re
    import unicodedata
    from collections import Counter

    profile = profile or {}
    posts = posts or []

    def norm(text):
        text = str(text or "").lower()
        text = unicodedata.normalize("NFD", text)
        text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
        return text

    def clean_line(text, limit=240):
        text = str(text or "").replace("\n", " ").strip()
        text = re.sub(r"\s+", " ", text)
        return text[:limit] + ("..." if len(text) > limit else "")

    def has(pattern, text):
        return bool(re.search(pattern, norm(text)))

    def find_first(pattern, text):
        m = re.search(pattern, text or "", flags=re.I)
        return clean_line(m.group(0), 180) if m else ""

    bio = profile.get("biography") or ""
    website = profile.get("website") or ""
    followers = int(profile.get("followers_count") or 0)
    media_count = int(profile.get("media_count") or 0)

    captions = [p.get("caption") or "" for p in posts]
    captions_text = "\n".join(captions)
    all_text = bio + "\n" + captions_text
    all_norm = norm(all_text)

    stop = set("""
    para como mais muito pela pelo pelas pelos essa esse isso esta este aqui voce você seus suas
    meu minha meus minhas uma umas uns aos das dos que com sem por sua seu elas eles nosso nossa
    tambem também cada onde quando sobre entre todo todos toda todas hoje agora porque ainda depois
    antes fazer feita feito ter tem sera será sao são nao não sim seu sua nos nas ser aos em de da do
    no na o a e os as um uma
    """.split())

    tokens = re.findall(r"[a-z0-9]{4,}", all_norm)
    tokens = [t for t in tokens if t not in stop and not t.isdigit()]
    top_terms = [w for w, c in Counter(tokens).most_common(12)]

    categories = {
        "educativo": r"dica|como|erro|passo|guia|aprenda|entenda|beneficio|benefício|motivo|saber|evite|cuidados|verdade|mito",
        "autoridade": r"especialista|profissional|experiencia|experiência|metodo|método|consulta|formacao|formação|certificacao|certificação|resultado|anos",
        "prova_social": r"cliente|depoimento|feedback|antes|depois|resultado|avaliacao|avaliação|transformacao|transformação",
        "oferta": r"agende|agenda|horario|horário|valor|preco|preço|promocao|promoção|orcamento|orçamento|pedido|comprar|vaga|plano|pacote|link|whatsapp",
        "bastidor": r"bastidor|rotina|equipe|dia|preparacao|preparação|atendimento|processo|por aqui",
        "relacionamento": r"comente|me conta|responda|caixinha|pergunta|duvida|dúvida|qual voce|qual você|enquete"
    }

    post_analysis = []

    for p in posts:
        caption = p.get("caption") or ""
        caption_norm = norm(caption)
        likes = int(p.get("like_count") or 0)
        comments = int(p.get("comments_count") or 0)
        score = likes + (comments * 4)

        matched = []
        for name, pattern in categories.items():
            if re.search(pattern, caption_norm):
                matched.append(name)

        has_cta_caption = bool(re.search(categories["oferta"] + "|" + categories["relacionamento"], caption_norm))
        has_question = "?" in caption

        post_analysis.append({
            "raw": p,
            "caption": caption,
            "caption_short": clean_line(caption, 220),
            "likes": likes,
            "comments": comments,
            "score": score,
            "matched": matched,
            "has_cta": has_cta_caption,
            "has_question": has_question
        })

    ranked = sorted(post_analysis, key=lambda x: x["score"], reverse=True)

    total_likes = sum(p["likes"] for p in post_analysis)
    total_comments = sum(p["comments"] for p in post_analysis)
    avg_likes = round(total_likes / len(posts), 2) if posts else 0
    avg_comments = round(total_comments / len(posts), 2) if posts else 0

    mix = Counter()
    for p in post_analysis:
        for m in p["matched"]:
            mix[m] += 1

    dominant_mix = mix.most_common()

    cta_bio = has(r"agende|chame|link|whatsapp|direct|contato|orcamento|orçamento|clique|reserve|compre", bio)
    location_bio = has(r"sp|mg|rj|go|brasil|online|presencial|cidade|bairro|regiao|região|endereco|endereço", bio)
    offer_bio = has(r"servico|serviço|aula|consulta|produto|metodo|método|plano|cardapio|cardápio|tratamento|mentoria|gestao|gestão", bio)
    audience_bio = find_first(r"(para|ajudo|atendo|especialista em|foco em)\s+[^.|,\n]{3,80}", bio)

    evidence = []

    if bio:
        evidence.append(f"Bio analisada: '{clean_line(bio, 220)}'")
    else:
        evidence.append("Bio não foi retornada pela leitura automática.")

    if website:
        evidence.append(f"Link identificado na bio: {website}")

    if ranked:
        top = ranked[0]
        evidence.append(
            f"Post com maior resposta pública: {top['likes']} curtidas e {top['comments']} comentários. Legenda: '{top['caption_short']}'"
        )

    if top_terms:
        evidence.append("Termos mais recorrentes identificados no perfil/posts: " + ", ".join(top_terms[:8]) + ".")

    if dominant_mix:
        evidence.append(
            "Tipos de conteúdo mais identificados nas legendas: " +
            ", ".join([f"{name} ({count})" for name, count in dominant_mix[:4]]) + "."
        )

    if not posts:
        evidence.append("Nenhum post público recente foi retornado para leitura.")

    # POSICIONAMENTO ATUAL
    if top_terms and posts:
        foco = ", ".join(top_terms[:5])
        posicionamento_atual = (
            f"Pela leitura pública, o perfil comunica com mais frequência os temas: {foco}. "
            f"Essa conclusão vem da recorrência desses termos na bio e nas legendas, não de suposição. "
        )
    elif bio:
        posicionamento_atual = (
            "A leitura automática encontrou bio, mas não houve volume suficiente de posts/legendas para afirmar um eixo forte de posicionamento. "
        )
    else:
        posicionamento_atual = (
            "Não há evidência textual suficiente para definir o posicionamento atual com segurança. "
        )

    if audience_bio:
        posicionamento_atual += f"O público ou foco aparece parcialmente na bio pelo trecho: '{audience_bio}'. "
    else:
        posicionamento_atual += "O público-alvo não ficou explícito de forma objetiva na bio. "

    if offer_bio:
        posicionamento_atual += "Existe sinal de oferta/serviço na bio. "
    else:
        posicionamento_atual += "A oferta principal não ficou claramente identificada na bio. "

    if cta_bio:
        posicionamento_atual += "A bio possui caminho de ação/contato. "
    else:
        posicionamento_atual += "A bio não apresentou CTA claro de conversão. "

    # FORÇAS COM EVIDÊNCIA
    strengths = []

    if bio and len(bio.strip()) >= 70:
        strengths.append("A bio possui conteúdo suficiente para análise inicial; não está completamente vazia ou rasa.")

    if cta_bio:
        strengths.append("Foi identificado CTA ou caminho de contato na bio, o que ajuda a conduzir o visitante para uma ação.")

    if offer_bio:
        strengths.append("A bio apresenta sinal de serviço, produto ou oferta, criando uma base de posicionamento comercial.")

    if location_bio:
        strengths.append("A bio apresenta sinal de localização, região ou formato de atendimento, facilitando entendimento do público.")

    if ranked:
        top = ranked[0]
        strengths.append(
            f"O post com melhor resposta pública teve {top['likes']} curtidas e {top['comments']} comentários, indicando tema com potencial de repetição estratégica."
        )

    if mix.get("educativo", 0) > 0:
        strengths.append(f"Foram encontrados {mix.get('educativo')} sinais de conteúdo educativo nas legendas, o que contribui para autoridade.")

    if mix.get("prova_social", 0) > 0:
        strengths.append(f"Foram encontrados {mix.get('prova_social')} sinais de prova social/resultado, o que fortalece confiança.")

    if total_comments > 0:
        strengths.append(f"Os posts analisados somaram {total_comments} comentários públicos, indicando alguma abertura para conversa.")

    if not strengths:
        strengths.append("O perfil foi localizado, mas os sinais estratégicos fortes ainda não apareceram com clareza na leitura pública.")

    # AJUSTES COM CRITÉRIO
    adjustments = []

    if not bio or len(bio.strip()) < 70:
        adjustments.append("A bio está curta ou pouco informativa. Precisa comunicar: o que faz, para quem faz, diferencial e ação esperada.")

    if not audience_bio:
        adjustments.append("O público-alvo não está claro. O visitante precisa entender rapidamente se aquele serviço é para ele.")

    if not offer_bio:
        adjustments.append("A oferta principal não ficou evidente. O perfil precisa deixar mais claro qual serviço, produto ou transformação vende.")

    if not cta_bio:
        adjustments.append("Falta CTA claro na bio. Recomenda-se inserir chamada direta como: agende, fale no WhatsApp, peça orçamento ou acesse o link.")

    if not location_bio:
        adjustments.append("Não foi identificado local, região ou formato de atendimento. Isso pode gerar dúvida em quem chega pelo perfil.")

    if posts and mix.get("oferta", 0) == 0:
        adjustments.append("Nos posts recentes não foram encontrados sinais fortes de oferta. O perfil pode estar informando, mas não conduzindo para venda.")

    if posts and mix.get("autoridade", 0) == 0 and mix.get("prova_social", 0) == 0:
        adjustments.append("A leitura dos posts não encontrou sinais suficientes de autoridade ou prova social. Isso reduz confiança para conversão.")

    if posts:
        cta_posts = sum(1 for p in post_analysis if p["has_cta"])
        if cta_posts / len(posts) < 0.3:
            adjustments.append(f"Apenas {cta_posts} de {len(posts)} posts analisados têm CTA ou estímulo de interação. É preciso conduzir melhor o público.")

    if len(posts) < 6:
        adjustments.append("A base de posts retornada é pequena. A conclusão deve ser tratada como leitura inicial, não como diagnóstico completo de performance.")

    # PILARES REAIS
    pillar_map = {
        "educativo": "Conteúdo educativo",
        "autoridade": "Autoridade profissional",
        "prova_social": "Prova social/resultados",
        "oferta": "Oferta e conversão",
        "bastidor": "Bastidores e relacionamento",
        "relacionamento": "Interação com audiência"
    }

    content_pillars = []

    for name, count in dominant_mix:
        content_pillars.append({
            "pillar": pillar_map.get(name, name),
            "count": count,
            "evidence": f"{count} ocorrência(s) identificada(s) nas legendas recentes."
        })

    if not content_pillars and top_terms:
        content_pillars = [
            {
                "pillar": f"Tema recorrente: {term}",
                "count": 1,
                "evidence": "Tema identificado por recorrência textual."
            }
            for term in top_terms[:4]
        ]

    # POSICIONAMENTO RECOMENDADO
    tema_base = ", ".join(top_terms[:3]) if top_terms else "o serviço principal do negócio"
    publico_base = audience_bio if audience_bio else "um público-alvo mais específico"
    acao_base = "direcionar para contato/agendamento/orçamento" if not cta_bio else "fortalecer o CTA já existente"

    recommended_positioning = (
        f"Posicionamento recomendado: organizar o perfil para comunicar {tema_base} com foco em {publico_base}. "
        f"A bio deve explicar claramente a entrega, o diferencial e {acao_base}. "
        "Os conteúdos devem equilibrar autoridade, prova social e oferta, usando os posts com maior resposta pública como base para novos temas."
    )

    # LEITURA DOS POSTS
    posts_lines = []
    posts_lines.append(f"Foram analisados {len(posts)} posts públicos recentes.")
    posts_lines.append(f"Resposta pública total observada: {total_likes} curtidas e {total_comments} comentários.")
    posts_lines.append(f"Média por post: {avg_likes} curtidas e {avg_comments} comentários.")

    if dominant_mix:
        posts_lines.append(
            "Distribuição estratégica percebida: " +
            ", ".join([f"{pillar_map.get(k,k)}: {v}" for k, v in dominant_mix]) + "."
        )
    else:
        posts_lines.append("As legendas não apresentaram padrões fortes o suficiente para classificar pilares com segurança.")

    if ranked:
        posts_lines.append("")
        posts_lines.append("Posts com maior resposta pública:")
        for idx, p in enumerate(ranked[:5], start=1):
            posts_lines.append(
                f"{idx}. {p['likes']} curtidas, {p['comments']} comentários — {p['caption_short']}"
            )

    # RECOMENDAÇÕES SEM ACHISMO
    recommendations = []

    recommendations.append(recommended_positioning)

    if ranked:
        top = ranked[0]
        recommendations.append(
            f"Repetir o tema do post com melhor resposta pública, mas com novo gancho e CTA. Base: '{top['caption_short']}'."
        )

    if not cta_bio:
        recommendations.append(
            "Reescrever a última linha da bio com CTA direto. Exemplo estrutural: 'Agende pelo WhatsApp' ou 'Peça seu orçamento no link abaixo'."
        )

    if not audience_bio:
        recommendations.append(
            "Inserir público-alvo na bio e nos conteúdos. O perfil precisa dizer para quem é a solução."
        )

    if mix.get("prova_social", 0) == 0:
        recommendations.append(
            "Criar sequência de prova social: depoimentos, bastidores de atendimento, resultados, avaliações ou antes/depois, conforme o segmento permitir."
        )

    if mix.get("oferta", 0) == 0:
        recommendations.append(
            "Criar posts de oferta com contexto, não apenas venda direta: problema do cliente, solução oferecida, benefício e chamada para ação."
        )

    recommendations.append(
        "Inserir prints do painel profissional para validar se os temas com melhor resposta pública também possuem alcance, salvamentos ou compartilhamentos."
    )

    def compact_post(item):
        p = item["raw"]
        return {
            "id": p.get("id"),
            "caption": item["caption_short"],
            "media_type": p.get("media_type"),
            "permalink": p.get("permalink"),
            "timestamp": p.get("timestamp"),
            "like_count": item["likes"],
            "comments_count": item["comments"],
            "score_publico": item["score"],
            "classificacao": item["matched"]
        }

    return {
        "profile_summary": {
            "username": profile.get("username"),
            "name": profile.get("name"),
            "biography": bio,
            "website": website,
            "followers_count": followers,
            "media_count": media_count
        },
        "no_guess_mode": True,
        "positioning_text": positioning_atual,
        "recommended_positioning": recommended_positioning,
        "evidence": evidence,
        "content_pillars": content_pillars,
        "posts_reading": "\n".join(posts_lines),
        "strengths": strengths,
        "adjustments": adjustments,
        "recommendations": recommendations,
        "top_posts": [compact_post(p) for p in ranked[:8]],
        "manual_needed": {
            "destaques": "Destaques não são entregues automaticamente pela Meta para perfil de terceiros. Inserir manualmente ou por print.",
            "prints": "Prints do painel profissional continuam necessários para alcance, salvos, compartilhamentos e insights internos."
        }
    }

'''

pattern = r'def _vertice_public_profile_analysis\(profile, posts\):[\s\S]*?\n@app.get\("/api/profile-public-analysis"\)'

if re.search(pattern, s):
    s = re.sub(pattern, lambda m: new_function + '\n@app.get("/api/profile-public-analysis")', s, count=1)
else:
    raise RuntimeError("Não encontrei a função _vertice_public_profile_analysis para substituir.")

app_path.write_text(s, encoding="utf-8")


index_path = Path("backend/static/index.html")
html = index_path.read_text(encoding="utf-8")

Path("backend/static/index_backup_antes_front_sem_achismo.html").write_text(html, encoding="utf-8")

old_block = '''    pcSet("pcPosts", analysis.posts_reading || "");

    pcSet("pcForcas", (analysis.strengths || []).map(x => "- " + x).join("\\\\n"));
    pcSet("pcAjustes", (analysis.adjustments || []).map(x => "- " + x).join("\\\\n"));
    pcSet("pcObs", (analysis.recommendations || []).map(x => "- " + x).join("\\\\n"));'''

new_block = '''    const evidencias = (analysis.evidence || []).map(x => "- " + x).join("\\\\n");
    const pilares = (analysis.content_pillars || []).map(x => `- ${x.pillar}: ${x.evidence}`).join("\\\\n");

    pcSet("pcPosts", [
      "POSICIONAMENTO IDENTIFICADO SEM ACHISMO",
      analysis.positioning_text || "",
      "",
      "LEITURA DOS POSTS",
      analysis.posts_reading || "",
      "",
      "EVIDÊNCIAS USADAS",
      evidencias || "Nenhuma evidência suficiente retornada.",
      "",
      "PILARES IDENTIFICADOS",
      pilares || "Nenhum pilar forte identificado com segurança."
    ].join("\\\\n"));

    pcSet("pcForcas", (analysis.strengths || []).map(x => "- " + x).join("\\\\n"));
    pcSet("pcAjustes", (analysis.adjustments || []).map(x => "- " + x).join("\\\\n"));

    pcSet("pcObs", [
      "POSICIONAMENTO RECOMENDADO",
      analysis.recommended_positioning || "",
      "",
      "RECOMENDAÇÕES COM BASE NAS EVIDÊNCIAS",
      (analysis.recommendations || []).map(x => "- " + x).join("\\\\n")
    ].join("\\\\n"));'''

if old_block in html:
    html = html.replace(old_block, new_block)
else:
    print("Bloco antigo do frontend não encontrado. Tentando substituição por regex...")
    html = re.sub(
        r'pcSet\("pcPosts", analysis\.posts_reading \|\| ""\);\s*pcSet\("pcForcas", \(analysis\.strengths \|\| \[\]\)\.map\(x => "- " \+ x\)\.join\("\\\\n"\)\);\s*pcSet\("pcAjustes", \(analysis\.adjustments \|\| \[\]\)\.map\(x => "- " \+ x\)\.join\("\\\\n"\)\);\s*pcSet\("pcObs", \(analysis\.recommendations \|\| \[\]\)\.map\(x => "- " \+ x\)\.join\("\\\\n"\)\);',
        lambda m: new_block,
        html,
        count=1
    )

# Ajusta mensagem de sucesso para deixar claro o novo padrão
html = html.replace(
    "Perfil localizado automaticamente via dados públicos. A bio e os posts recentes foram preenchidos.",
    "Perfil localizado automaticamente. A análise agora usa evidências reais da bio, legendas, curtidas e comentários públicos — sem achismo."
)

html = html.replace(
    "Leitura automática concluída. Revise os campos e gere a análise.",
    "Leitura estratégica concluída. Revise as evidências, complemente os destaques/prints e gere a análise."
)

index_path.write_text(html, encoding="utf-8")

print("Análise estratégica sem achismo aplicada com sucesso.")
print("Agora a VÉRTICE usa evidências reais: bio, legendas, termos recorrentes, curtidas, comentários e CTA.")
