from fastapi import FastAPI

from routers.auth import router as auth_router
from routers.client_discovery import router as client_router
from routers.reports import router as reports_router
from routers.snapshots import router as snapshots_router
from routers.token import router as token_router

app = FastAPI(title="VÉRTICE IA")

app.include_router(auth_router)
app.include_router(client_router)
app.include_router(reports_router)
app.include_router(snapshots_router)
app.include_router(token_router)

from datetime import datetime, timedelta
import urllib.parse
import secrets
import json
import sqlite3

import os, json, sqlite3, re, hmac, hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / 'static'
META_API_VERSION = os.getenv('META_API_VERSION','v25.0').strip()
TOKEN = os.getenv('FACEBOOK_ACCESS_TOKEN','').strip()
PAGE_ID = os.getenv('FACEBOOK_PAGE_ID','').strip()
DB_PATH = Path(os.getenv('VERTICE_DB_PATH', str(BASE_DIR/'vertice_ia_limpa.db')))

app = FastAPI(title='VÉRTICE IA', version='1.0.0')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])

def now(): return datetime.now(timezone.utc).isoformat()
def db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row; return c

def init_db():
    with db() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, source TEXT,
            facebook_page_id TEXT, facebook_page_name TEXT, instagram_account_id TEXT, instagram_username TEXT,
            total_posts INTEGER DEFAULT 0, alcance_total INTEGER DEFAULT 0, salvos_total INTEGER DEFAULT 0,
            shares_total INTEGER DEFAULT 0, comentarios_total INTEGER DEFAULT 0, curtidas_total INTEGER DEFAULT 0,
            raw_summary TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS snapshot_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, snapshot_id INTEGER NOT NULL, post_id TEXT NOT NULL,
            caption TEXT, media_type TEXT, media_product_type TEXT, permalink TEXT, timestamp TEXT,
            like_count INTEGER DEFAULT 0, comments_count INTEGER DEFAULT 0, reach INTEGER DEFAULT 0,
            saved INTEGER DEFAULT 0, shares INTEGER DEFAULT 0, engagement_rate REAL DEFAULT 0,
            potential_score REAL DEFAULT 0, raw_post TEXT)''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_snapshots_created ON snapshots(created_at)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_posts_snapshot ON snapshot_posts(snapshot_id)')
        c.commit()
@app.on_event('startup')
def startup(): init_db()

def meta_get(path:str, params:dict[str,Any]|None=None):
    if not TOKEN:
        raise HTTPException(400, detail={'message':'FACEBOOK_ACCESS_TOKEN não configurado no backend/.env.'})
    url=f'https://graph.facebook.com/{META_API_VERSION}/{path.lstrip("/")}'
    q=dict(params or {}); q['access_token']=TOKEN
    try:
        r=requests.get(url, params=q, timeout=30); p=r.json()
    except Exception as e:
        raise HTTPException(502, detail=f'Erro ao conectar na Meta: {e}')
    if r.status_code>=400 or 'error' in p:
        e=p.get('error', p)
        raise HTTPException(r.status_code if r.status_code>=400 else 400, detail={
            'message': e.get('message','Erro na Meta'), 'code': e.get('code'), 'type': e.get('type'),
            'corrigir':['Se code 190: token expirou; gere token novo.','Confira FACEBOOK_PAGE_ID.','Confira permissões pages_show_list, pages_read_engagement, instagram_basic, instagram_manage_insights.']})
    return p

def meta_safe(path, params=None):
    try: return True, meta_get(path, params)
    except HTTPException as e: return False, e.detail if isinstance(e.detail,dict) else {'message':str(e.detail)}

def resolve_account():
    if not PAGE_ID: raise HTTPException(400, detail={'message':'FACEBOOK_PAGE_ID não configurado.'})
    p=meta_get(PAGE_ID, {'fields':'id,name,instagram_business_account{id,username,name,profile_picture_url,followers_count,follows_count,media_count}'})
    ig=p.get('instagram_business_account')
    if not ig or not ig.get('id'):
        raise HTTPException(400, detail={'message':'Página encontrada, mas sem instagram_business_account conectado.','facebook_page':{'id':p.get('id'),'name':p.get('name')}})
    return {'facebook_page':{'id':p.get('id'),'name':p.get('name')}, 'instagram_account':ig, 'instagram_account_id':ig['id']}

def insights(mid):
    res={'reach':0,'saved':0,'shares':0}
    ok,p=meta_safe(f'{mid}/insights', {'metric':'reach,saved,shares'})
    if not ok: return res
    for it in p.get('data',[]):
        n=it.get('name'); vals=it.get('values') or []; v=vals[0].get('value',0) if vals else 0
        if n in res:
            try: res[n]=int(v or 0)
            except Exception: res[n]=0
    return res

def score(reach,saved,shares,likes,comments):
    if reach<=0: return 0.0
    return round(min(100, (saved/reach)*100*18 + (shares/reach)*100*12 + ((likes+comments+saved+shares)/reach)*100*2.8),2)

def norm_post(p):
    mid=str(p.get('id') or ''); ins=insights(mid)
    likes=int(p.get('like_count') or 0); comments=int(p.get('comments_count') or 0)
    reach=ins['reach']; saved=ins['saved']; shares=ins['shares']
    eng=round(((likes+comments+saved+shares)/reach)*100,2) if reach else 0
    return {'id':mid,'caption':p.get('caption') or 'Publicação sem legenda','media_type':p.get('media_type') or '',
        'media_product_type':p.get('media_product_type') or '', 'media_url':p.get('media_url') or p.get('thumbnail_url') or '',
        'thumbnail_url':p.get('thumbnail_url') or '', 'permalink':p.get('permalink') or '', 'timestamp':p.get('timestamp') or '',
        'like_count':likes,'comments_count':comments,'reach':reach,'saved':saved,'shares':shares,'engagement_rate':eng,
        'potential_score':score(reach,saved,shares,likes,comments)}

def extract_posts(limit=50):
    r=resolve_account(); ig_id=r['instagram_account_id']
    fields='id,caption,media_type,media_product_type,media_url,thumbnail_url,permalink,timestamp,like_count,comments_count'
    p=meta_get(f'{ig_id}/media', {'fields':fields,'limit':limit})
    posts=[norm_post(x) for x in p.get('data',[])]
    return {'status':'sucesso','source':'meta_graph_api','facebook_page':r['facebook_page'],'instagram_account':r['instagram_account'], 'instagram_account_id':ig_id, 'data':posts, 'paging':p.get('paging',{})}

def pint(p,k):
    try: return int(p.get(k) or 0)
    except Exception: return 0

def summarize(posts):
    s={'total_posts':len(posts),'alcance_total':sum(pint(p,'reach') for p in posts),'salvos_total':sum(pint(p,'saved') for p in posts),'shares_total':sum(pint(p,'shares') for p in posts),'comentarios_total':sum(pint(p,'comments_count') for p in posts),'curtidas_total':sum(pint(p,'like_count') for p in posts)}
    ordered=sorted(posts,key=lambda p:float(p.get('potential_score') or 0), reverse=True)
    plan=[]
    if ordered: plan.append('Repetir tema/formato do melhor conteúdo: '+(ordered[0].get('caption') or '')[:100])
    if s['salvos_total']<=0: plan.append('Criar conteúdos salváveis: checklist, tutorial, passo a passo e erros comuns.')
    if s['shares_total']<=0: plan.append('Criar conteúdos de identificação para gerar compartilhamento.')
    if ordered and float(ordered[0].get('potential_score') or 0)>=55: plan.append('Avaliar teste de tráfego pago com verba baixa no melhor conteúdo.')
    else: plan.append('Antes de impulsionar, melhorar gancho, CTA e clareza da oferta.')
    s.update({'melhor_post':ordered[0] if ordered else None,'post_mais_fraco':ordered[-1] if len(ordered)>1 else None,'plano_de_acao':plan})
    return s

def save_snapshot(payload):
    posts=payload.get('data',[]); s=summarize(posts); created=now()
    with db() as c:
        cur=c.execute('''INSERT INTO snapshots (created_at,source,facebook_page_id,facebook_page_name,instagram_account_id,instagram_username,total_posts,alcance_total,salvos_total,shares_total,comentarios_total,curtidas_total,raw_summary) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (created,'meta_graph_api',payload.get('facebook_page',{}).get('id'),payload.get('facebook_page',{}).get('name'),payload.get('instagram_account_id'),payload.get('instagram_account',{}).get('username'),s['total_posts'],s['alcance_total'],s['salvos_total'],s['shares_total'],s['comentarios_total'],s['curtidas_total'],json.dumps(s,ensure_ascii=False)))
        sid=cur.lastrowid
        for p in posts:
            c.execute('''INSERT INTO snapshot_posts (snapshot_id,post_id,caption,media_type,media_product_type,permalink,timestamp,like_count,comments_count,reach,saved,shares,engagement_rate,potential_score,raw_post) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (sid,p.get('id'),p.get('caption'),p.get('media_type'),p.get('media_product_type'),p.get('permalink'),p.get('timestamp'),pint(p,'like_count'),pint(p,'comments_count'),pint(p,'reach'),pint(p,'saved'),pint(p,'shares'),float(p.get('engagement_rate') or 0),float(p.get('potential_score') or 0),json.dumps(p,ensure_ascii=False)))
        c.commit()
    return {'id':sid,'created_at':created,**s}

def snapshot_posts(sid):
    with db() as c:
        rows=c.execute('SELECT * FROM snapshot_posts WHERE snapshot_id=? ORDER BY potential_score DESC, reach DESC',(sid,)).fetchall()
    return [dict(r) for r in rows]


def _n(v):
    try:
        return float(v or 0)
    except Exception:
        return 0.0

def _rate(part, total):
    return round((_n(part) / _n(total)) * 100, 2) if _n(total) > 0 else 0.0

def _clip(text, size=140):
    text = (text or 'Publicação sem legenda').replace('\n', ' ').strip()
    return text[:size] + ('...' if len(text) > size else '')

def _format_name(p):
    product = (p.get('media_product_type') or '').upper()
    media = (p.get('media_type') or '').upper()
    if product == 'REELS':
        return 'Reels'
    if product == 'FEED':
        return 'Feed'
    if product == 'STORY':
        return 'Stories'
    if media == 'VIDEO':
        return 'Vídeo'
    if media == 'CAROUSEL_ALBUM':
        return 'Carrossel'
    if media == 'IMAGE':
        return 'Imagem'
    return product or media or 'Outro'

def _decision_for_post(p, avg_reach):
    reach = _n(p.get('reach'))
    saved = _n(p.get('saved'))
    shares = _n(p.get('shares'))
    score_value = _n(p.get('potential_score'))
    engagement = _n(p.get('engagement_rate'))
    save_rate = _rate(saved, reach)
    share_rate = _rate(shares, reach)

    if score_value >= 65 and (saved + shares) > 0 and reach >= max(1, avg_reach * 0.45):
        return {
            'status': 'vale_testar_trafego',
            'badge': 'Vale testar tráfego',
            'priority': 1,
            'reason': 'Tem potencial alto e sinal de valor/interesse. Pode receber verba baixa para validar expansão.',
            'next_step': 'Criar variação do criativo, manter o tema principal e testar impulsionamento com verba controlada.'
        }

    if score_value >= 50 and (save_rate >= 0.4 or share_rate >= 0.2 or engagement >= 2):
        return {
            'status': 'repetir_organico',
            'badge': 'Repetir organicamente',
            'priority': 2,
            'reason': 'Mostrou resposta positiva do público, mas ainda precisa de repetição antes de escalar.',
            'next_step': 'Transformar em novo post, stories com enquete e reels com gancho mais direto.'
        }

    if reach >= avg_reach and (saved + shares) == 0:
        return {
            'status': 'alcance_sem_valor',
            'badge': 'Alcance sem profundidade',
            'priority': 3,
            'reason': 'A publicação foi vista, mas gerou pouco sinal de valor: poucos salvos e compartilhamentos.',
            'next_step': 'Reformular para formato salvável: checklist, erros comuns, passo a passo ou comparação.'
        }

    if score_value < 35:
        return {
            'status': 'nao_impulsionar',
            'badge': 'Não impulsionar agora',
            'priority': 4,
            'reason': 'Ainda não mostrou força suficiente para receber verba.',
            'next_step': 'Ajustar gancho, promessa do conteúdo, CTA e clareza da dor antes de qualquer tráfego.'
        }

    return {
        'status': 'monitorar',
        'badge': 'Monitorar',
        'priority': 5,
        'reason': 'Resultado intermediário. Não é descarte, mas ainda não é prioridade.',
        'next_step': 'Aguardar novo snapshot ou criar variação com gancho mais específico.'
    }

def strategic_analysis(posts):
    posts = posts or []
    total_posts = len(posts)
    totals = {
        'posts': total_posts,
        'alcance': sum(int(_n(p.get('reach'))) for p in posts),
        'salvos': sum(int(_n(p.get('saved'))) for p in posts),
        'compartilhamentos': sum(int(_n(p.get('shares'))) for p in posts),
        'curtidas': sum(int(_n(p.get('like_count'))) for p in posts),
        'comentarios': sum(int(_n(p.get('comments_count'))) for p in posts),
    }
    avg_reach = round(totals['alcance'] / total_posts, 2) if total_posts else 0
    avg_score = round(sum(_n(p.get('potential_score')) for p in posts) / total_posts, 2) if total_posts else 0
    totals['taxa_salvamento'] = _rate(totals['salvos'], totals['alcance'])
    totals['taxa_compartilhamento'] = _rate(totals['compartilhamentos'], totals['alcance'])
    totals['media_alcance_por_post'] = avg_reach
    totals['media_potencial'] = avg_score

    enriched = []
    for p in posts:
        item = dict(p)
        item['formato_nome'] = _format_name(p)
        item['taxa_salvamento'] = _rate(item.get('saved'), item.get('reach'))
        item['taxa_compartilhamento'] = _rate(item.get('shares'), item.get('reach'))
        item['decisao'] = _decision_for_post(item, avg_reach)
        enriched.append(item)

    ranked = sorted(enriched, key=lambda p: (_n(p.get('potential_score')), _n(p.get('saved')), _n(p.get('shares')), _n(p.get('reach'))), reverse=True)
    best_reach = sorted(enriched, key=lambda p: _n(p.get('reach')), reverse=True)[:5]
    best_value = sorted(enriched, key=lambda p: (_n(p.get('saved')) + _n(p.get('shares')), _n(p.get('potential_score'))), reverse=True)[:5]
    traffic = [p for p in ranked if p['decisao']['status'] == 'vale_testar_trafego'][:5]
    repeat = [p for p in ranked if p['decisao']['status'] in ['vale_testar_trafego','repetir_organico']][:6]
    adjust = [p for p in ranked if p['decisao']['status'] in ['alcance_sem_valor','nao_impulsionar']][:6]
    no_boost = [p for p in ranked if p['decisao']['status'] == 'nao_impulsionar'][:6]

    formats = {}
    for p in enriched:
        key = p['formato_nome']
        formats.setdefault(key, {'formato': key, 'posts': 0, 'alcance': 0, 'salvos': 0, 'compartilhamentos': 0, 'curtidas': 0, 'comentarios': 0, 'potencial_total': 0.0, 'melhor_post': None})
        f = formats[key]
        f['posts'] += 1
        f['alcance'] += int(_n(p.get('reach')))
        f['salvos'] += int(_n(p.get('saved')))
        f['compartilhamentos'] += int(_n(p.get('shares')))
        f['curtidas'] += int(_n(p.get('like_count')))
        f['comentarios'] += int(_n(p.get('comments_count')))
        f['potencial_total'] += _n(p.get('potential_score'))
        if not f['melhor_post'] or _n(p.get('potential_score')) > _n(f['melhor_post'].get('potential_score')):
            f['melhor_post'] = p

    format_list = []
    for f in formats.values():
        f['media_potencial'] = round(f['potencial_total'] / f['posts'], 2) if f['posts'] else 0
        f['media_alcance'] = round(f['alcance'] / f['posts'], 2) if f['posts'] else 0
        f['taxa_salvamento'] = _rate(f['salvos'], f['alcance'])
        f['taxa_compartilhamento'] = _rate(f['compartilhamentos'], f['alcance'])
        f['melhor_post'] = {
            'caption': _clip((f['melhor_post'] or {}).get('caption')),
            'potential_score': (f['melhor_post'] or {}).get('potential_score', 0),
            'permalink': (f['melhor_post'] or {}).get('permalink', '')
        }
        format_list.append(f)
    format_list = sorted(format_list, key=lambda f: (f['media_potencial'], f['salvos'], f['compartilhamentos']), reverse=True)

    top_words = {}
    stop = {'para','com','uma','que','não','mais','seu','sua','dos','das','por','como','você','voce','isso','esse','essa','aqui','sobre','hoje','quando','onde','porque','pela','pelo','nas','nos','sem','tem','está','esta','ser','são','sao','até','ate'}
    for p in enriched:
        caption = (p.get('caption') or '').lower()
        for word in re.findall(r'[a-záéíóúãõâêôç]{4,}', caption):
            if word not in stop:
                top_words[word] = top_words.get(word, 0) + 1
    temas = [{'tema': k, 'ocorrencias': v} for k, v in sorted(top_words.items(), key=lambda x: x[1], reverse=True)[:10]]

    def compact_post(p):
        return {
            'id': p.get('id') or p.get('post_id'),
            'caption': _clip(p.get('caption'), 180),
            'formato': p.get('formato_nome'),
            'permalink': p.get('permalink'),
            'reach': int(_n(p.get('reach'))),
            'saved': int(_n(p.get('saved'))),
            'shares': int(_n(p.get('shares'))),
            'like_count': int(_n(p.get('like_count'))),
            'comments_count': int(_n(p.get('comments_count'))),
            'engagement_rate': _n(p.get('engagement_rate')),
            'potential_score': _n(p.get('potential_score')),
            'taxa_salvamento': p.get('taxa_salvamento', 0),
            'taxa_compartilhamento': p.get('taxa_compartilhamento', 0),
            'decisao': p.get('decisao', {})
        }

    if not posts:
        resumo = 'Ainda não há publicações carregadas para análise estratégica.'
        diagnostico = 'Importe dados reais da Meta para gerar diagnóstico.'
    elif totals['salvos'] == 0 and totals['compartilhamentos'] == 0:
        resumo = 'O perfil está gerando visibilidade, mas ainda precisa criar mais conteúdo de valor e identificação.'
        diagnostico = 'Prioridade: conteúdos salváveis e compartilháveis antes de pensar em escala com tráfego.'
    elif traffic:
        resumo = 'Existem conteúdos com sinal positivo para teste controlado de tráfego.'
        diagnostico = 'Prioridade: repetir os temas vencedores e validar impulsionamento com verba baixa.'
    elif repeat:
        resumo = 'Há conteúdos com resposta orgânica boa, mas ainda é cedo para escalar.'
        diagnostico = 'Prioridade: repetir os formatos com melhor resposta e melhorar CTA.'
    else:
        resumo = 'A base ainda precisa de mais consistência para indicar impulsionamento.'
        diagnostico = 'Prioridade: melhorar ganchos, promessa do conteúdo e clareza do posicionamento.'

    plano_7_dias = [
        'Dia 1: repetir o tema do melhor conteúdo com um gancho mais direto.',
        'Dia 2: transformar o melhor conteúdo em stories com enquete ou caixinha.',
        'Dia 3: criar um conteúdo salvável: checklist, passo a passo ou erros comuns.',
        'Dia 4: publicar uma prova/autoridade ligada ao tema que teve mais resposta.',
        'Dia 5: criar uma variação do conteúdo com maior potencial para testar tráfego.',
        'Dia 6: analisar comentários, salvamentos e compartilhamentos antes de impulsionar.',
        'Dia 7: salvar novo snapshot e comparar evolução no relatório.'
    ]

    if traffic:
        plano_7_dias[4] = 'Dia 5: separar o melhor conteúdo para teste de tráfego com verba baixa e objetivo claro.'
    if totals['taxa_salvamento'] < 0.3:
        plano_7_dias[2] = 'Dia 3: publicar conteúdo altamente salvável: lista, checklist, tutorial ou antes/depois explicado.'

    texto_cliente = (
        'Análise estratégica da VÉRTICE IA: os dados mostram que a prioridade não é apenas aumentar volume de postagens, '
        f'mas entender quais conteúdos geram sinal real de interesse. Foram analisadas {total_posts} publicações, com '
        f'{totals["alcance"]} de alcance total, {totals["salvos"]} salvamentos e {totals["compartilhamentos"]} compartilhamentos. '
        f'{diagnostico} O próximo passo é repetir os temas com melhor resposta, ajustar conteúdos com baixa profundidade '
        'e só considerar tráfego pago nos conteúdos que já demonstraram potencial orgânico.'
    )

    return {
        'resumo_executivo': resumo,
        'diagnostico': diagnostico,
        'totais': totals,
        'temas_recorrentes': temas,
        'formatos': format_list,
        'melhor_formato': format_list[0] if format_list else None,
        'melhores_por_potencial': [compact_post(p) for p in ranked[:8]],
        'melhores_por_alcance': [compact_post(p) for p in best_reach],
        'conteudos_de_valor': [compact_post(p) for p in best_value],
        'indicados_para_trafego': [compact_post(p) for p in traffic],
        'repetir': [compact_post(p) for p in repeat],
        'ajustar_antes_de_impulsionar': [compact_post(p) for p in adjust],
        'nao_impulsionar': [compact_post(p) for p in no_boost],
        'plano_7_dias': plano_7_dias,
        'texto_cliente': texto_cliente,
        'alertas': [
            'Não impulsionar conteúdo apenas por estética. Priorize sinal real: salvos, compartilhamentos e resposta ao tema.',
            'Alcance sem salvamento pode indicar curiosidade, mas não necessariamente valor.',
            'Conteúdo com alto potencial deve ser repetido antes de virar uma campanha maior.'
        ]
    }


VERTICE_META_REDIRECT_FINAL = "https://appverticeia.com.br/api/facebook-login/callback"
VERTICE_META_BASE_URL_FINAL = "https://appverticeia.com.br"

# ==============================
# LOGIN VISUAL - VÉRTICE IA
# ==============================

VERTICE_AUTH_ENABLED = os.getenv("VERTICE_AUTH_ENABLED", "true").lower() == "true"
VERTICE_USER = os.getenv("VERTICE_USER", "vertice").strip()
VERTICE_PASSWORD = os.getenv("VERTICE_PASSWORD", "262817").strip()
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

    if request.url.path in [
        "/api/facebook-login/callback",
        "/api/facebook-login/config",
        "/favicon.ico"
    ]:
        return await call_next(request)
    if not VERTICE_AUTH_ENABLED:
        return await call_next(request)

    path = request.url.path

    if path in [
        "/login",
        "/api/login",
        "/api/logout",
        "/api/status",
        "/api/session-check",
        "/api/facebook-login/config",
        "/api/facebook-login/callback",
        "/favicon.ico"
    ]:
        return await call_next(request)

    if _vertice_logged(request):
        return await call_next(request)

    if path.startswith("/api/"):
        return JSONResponse({"detail": "Acesso não autorizado. Faça login na VÉRTICE IA."}, status_code=401)

    return RedirectResponse("/login")


@app.get("/api/session-check")
def api_session_check(request: Request):
    return {
        "logged": _vertice_logged(request),
        "cookies": list(request.cookies.keys()),
        "status": "ok"
    }

VERTICE_LOGIN_HTML = """
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Login — VÉRTICE IA</title>
<style>

.brand-logo-login {
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  margin: 0 0 14px 0;
}
.brand-logo-login img {
  width: 72px;
  height: 72px;
  object-fit: contain;
  border-radius: 16px;
  background: rgba(255,255,255,.96);
  padding: 7px;
  box-shadow: 0 8px 18px rgba(0,0,0,.16);
}

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
    <div class="brand-logo-login">
      <img src="/static/assets/logo-vertice-ia.png" alt="Logo">
    </div>
    <div class="login-eyebrow">Acesso restrito</div>
    <p class="login-subtitle">Entre para acessar o painel estratégico com dados reais, relatórios e análise de conteúdo.</p>

    <form id="loginForm">
      <label>Usuário</label>
      <input id="username" autocomplete="username" placeholder="Digite o usuário" required>

      <label>Senha</label>
      <input id="password" type="password" autocomplete="current-password" placeholder="Digite a senha" required>

      <button type="submit">Entrar no painel</button>
      <div class="error" id="error">Usuário ou senha incorretos.</div>
    </form>

    <div class="footer">
      Acesso protegido para demonstração e operação do painel.
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

@app.get('/', response_class=HTMLResponse)
def home(): return HTMLResponse((STATIC_DIR/'index.html').read_text(encoding='utf-8'))

@app.get('/api/status')
def status():
    init_db(); return {'status':'sucesso','app':'VÉRTICE IA','time':now(),'database':str(DB_PATH),'meta':{'api_version':META_API_VERSION,'has_token':bool(TOKEN),'facebook_page_id':PAGE_ID or None}}

@app.get('/api/debug/my-pages')
def my_pages():
    p=meta_get('me/accounts', {'fields':'id,name,instagram_business_account{id,username,name},access_token','limit':50})
    return {'status':'sucesso','pages':p.get('data',[]),'paging':p.get('paging',{})}

@app.get('/api/resolve-account')
def api_resolve(): return {'status':'sucesso', **resolve_account()}

@app.get('/api/posts')
def api_posts(limit:int=Query(50,ge=1,le=100)): return extract_posts(limit)

@app.get('/api/report')
def api_report(limit:int=Query(50,ge=1,le=100)):
    p=extract_posts(limit); return {'status':'sucesso','facebook_page':p.get('facebook_page'),'instagram_account':p.get('instagram_account'),'report':summarize(p.get('data',[]))}

@app.post('/api/snapshots/save')
def api_save(limit:int=Query(50,ge=1,le=100)):
    p=extract_posts(limit); return {'status':'sucesso','message':'Snapshot salvo com dados reais da Meta.','snapshot':save_snapshot(p)}

@app.get('/api/snapshots')
def api_snaps(limit:int=Query(30,ge=1,le=200)):
    with db() as c:
        rows=c.execute('SELECT * FROM snapshots ORDER BY datetime(created_at) DESC LIMIT ?',(limit,)).fetchall()
    return {'status':'sucesso','snapshots':[dict(r) for r in rows]}

@app.get('/api/history')
def api_history(days:int=Query(30,ge=1,le=365)):
    since=(datetime.now(timezone.utc)-timedelta(days=days)).isoformat()
    with db() as c:
        rows=c.execute('SELECT * FROM snapshots WHERE created_at>=? ORDER BY datetime(created_at) DESC',(since,)).fetchall()
    snaps=[dict(r) for r in rows]
    return {'status':'sucesso','days':days,'snapshots':snaps,'evolution':list(reversed(snaps)),'latest':snaps[0] if snaps else None}

@app.get('/api/comparative-report')
def comparative(days:int=Query(30,ge=1,le=365)):
    since=(datetime.now(timezone.utc)-timedelta(days=days)).isoformat()
    with db() as c:
        rows=c.execute('SELECT * FROM snapshots WHERE created_at>=? ORDER BY datetime(created_at) DESC LIMIT 2',(since,)).fetchall()
    snaps=[dict(r) for r in rows]
    if not snaps: return {'status':'vazio','message':'Nenhum snapshot salvo ainda.','action_plan':['Importe dados reais e salve o primeiro snapshot.']}
    latest=snaps[0]; previous=snaps[1] if len(snaps)>1 else None
    if not previous: return {'status':'primeiro_snapshot','message':'Existe apenas um snapshot salvo. Salve outro depois para comparar evolução.','latest':latest,'previous':None,'delta_totals':{},'top_gains':[],'top_losses':[],'action_plan':['Use este snapshot como linha de base.','Salve outro snapshot no dia seguinte ou após novas publicações.']}
    latest_posts=snapshot_posts(latest['id']); prev={p['post_id']:p for p in snapshot_posts(previous['id'])}
    comp=[]
    for p in latest_posts:
        old=prev.get(p['post_id'])
        if not old: continue
        comp.append({'post_id':p['post_id'],'caption':p['caption'],'permalink':p['permalink'],'delta_reach':(p['reach'] or 0)-(old['reach'] or 0),'delta_saved':(p['saved'] or 0)-(old['saved'] or 0),'delta_shares':(p['shares'] or 0)-(old['shares'] or 0),'delta_likes':(p['like_count'] or 0)-(old['like_count'] or 0),'delta_comments':(p['comments_count'] or 0)-(old['comments_count'] or 0)})
    gains=sorted(comp,key=lambda x:(x['delta_reach'],x['delta_saved']),reverse=True)[:5]
    losses=sorted(comp,key=lambda x:(x['delta_reach'],x['delta_saved']))[:5]
    delta={'alcance_total':(latest['alcance_total'] or 0)-(previous['alcance_total'] or 0),'salvos_total':(latest['salvos_total'] or 0)-(previous['salvos_total'] or 0),'shares_total':(latest['shares_total'] or 0)-(previous['shares_total'] or 0),'comentarios_total':(latest['comentarios_total'] or 0)-(previous['comentarios_total'] or 0),'curtidas_total':(latest['curtidas_total'] or 0)-(previous['curtidas_total'] or 0)}
    plan=[]
    plan.append('Alcance cresceu: repita tema/formato dos posts com maior delta.' if delta['alcance_total']>0 else 'Alcance caiu ou estagnou: revisar gancho, constância e clareza da oferta.')
    plan.append('Salvamentos cresceram: usar esses temas como base para calendário e possível tráfego.' if delta['salvos_total']>0 else 'Salvamentos não cresceram: produzir checklist, tutorial, passo a passo e erro comum.')
    if gains: plan.append('Melhor evolução: '+(gains[0]['caption'] or '')[:100]+'. Avaliar impulsionamento com verba baixa.')
    return {'status':'sucesso','message':'Comparativo gerado com os dois últimos snapshots.','latest':latest,'previous':previous,'delta_totals':delta,'top_gains':gains,'top_losses':losses,'action_plan':plan}


@app.get('/api/advanced-report')
def api_advanced_report(limit:int=Query(50,ge=1,le=100)):
    p = extract_posts(limit)
    return {
        'status': 'sucesso',
        'facebook_page': p.get('facebook_page'),
        'instagram_account': p.get('instagram_account'),
        'advanced_report': strategic_analysis(p.get('data', []))
    }

@app.get('/api/strategic-report')
def api_strategic_report(limit:int=Query(50,ge=1,le=100)):
    p = extract_posts(limit)
    return {
        'status': 'sucesso',
        'facebook_page': p.get('facebook_page'),
        'instagram_account': p.get('instagram_account'),
        'advanced_report': strategic_analysis(p.get('data', []))
    }


# ==============================
# MONITOR DE TOKEN META - VÉRTICE IA
# ==============================

@app.get("/api/token-monitor")
def api_token_monitor():
    import datetime

    version = os.getenv("META_API_VERSION", "v25.0").strip()
    token = os.getenv("FACEBOOK_ACCESS_TOKEN", "").strip()
    page_id = os.getenv("FACEBOOK_PAGE_ID", "").strip()

    now = datetime.datetime.now().isoformat(timespec="seconds")

    base = {
        "status": "erro",
        "app": "VÉRTICE IA",
        "checked_at": now,
        "meta_api_version": version,
        "facebook_page_id": page_id,
        "has_token": bool(token),
        "token_status": "nao_configurado",
        "page_status": "nao_testado",
        "instagram_status": "nao_testado",
        "facebook_page": None,
        "instagram_account": None,
        "diagnostico": "",
        "acao_recomendada": ""
    }

    if not token:
        base["diagnostico"] = "FACEBOOK_ACCESS_TOKEN não está configurado no backend/.env."
        base["acao_recomendada"] = "Abra a configuração e cole um token válido da Meta."
        return base

    if not page_id:
        base["token_status"] = "nao_testado"
        base["diagnostico"] = "FACEBOOK_PAGE_ID não está configurado no backend/.env."
        base["acao_recomendada"] = "Configure FACEBOOK_PAGE_ID=1124922614045641."
        return base

    url = f"https://graph.facebook.com/{version}/{page_id}"
    params = {
        "fields": "id,name,instagram_business_account{id,username,name}",
        "access_token": token
    }

    try:
        r = requests.get(url, params=params, timeout=25)
        data = r.json()
    except Exception as e:
        base["token_status"] = "erro_conexao"
        base["diagnostico"] = f"Falha ao conectar na Meta: {str(e)}"
        base["acao_recomendada"] = "Verifique internet, versão da API e tente novamente."
        return base

    if not r.ok:
        err = data.get("error", {}) if isinstance(data, dict) else {}
        code = err.get("code")
        message = err.get("message", "Erro desconhecido")
        err_type = err.get("type", "")
        subcode = err.get("error_subcode")

        base["token_status"] = "invalido"
        base["page_status"] = "erro"
        base["instagram_status"] = "nao_testado"
        base["erro_meta"] = {
            "message": message,
            "type": err_type,
            "code": code,
            "subcode": subcode
        }

        if code == 190:
            base["diagnostico"] = "Token expirado ou inválido."
            base["acao_recomendada"] = "Gere um novo token Meta, atualize o backend/.env e reinicie a VÉRTICE IA."
        elif code in [10, 200]:
            base["diagnostico"] = "Token sem permissão suficiente para acessar a página ou Instagram."
            base["acao_recomendada"] = "Gere token com pages_show_list, pages_read_engagement, instagram_basic e instagram_manage_insights."
        elif code == 100:
            base["diagnostico"] = "Page ID inválido ou campo não acessível com esse token."
            base["acao_recomendada"] = "Confirme o FACEBOOK_PAGE_ID e se o token pertence ao mesmo app/conta."
        else:
            base["diagnostico"] = f"Erro Meta: {message}"
            base["acao_recomendada"] = "Revise token, permissões, Page ID e conexão com Instagram profissional."

        return base

    ig = data.get("instagram_business_account")

    base["status"] = "sucesso"
    base["token_status"] = "ativo"
    base["page_status"] = "conectada"
    base["facebook_page"] = {
        "id": data.get("id"),
        "name": data.get("name")
    }

    if ig:
        base["instagram_status"] = "conectado"
        base["instagram_account"] = {
            "id": ig.get("id"),
            "username": ig.get("username"),
            "name": ig.get("name")
        }
        base["diagnostico"] = "Token ativo, página acessível e Instagram profissional conectado."
        base["acao_recomendada"] = "Tudo certo. A VÉRTICE IA pode importar dados reais."
    else:
        base["instagram_status"] = "nao_conectado"
        base["diagnostico"] = "Token e página estão acessíveis, mas nenhum Instagram profissional foi localizado nessa página."
        base["acao_recomendada"] = "Confirme se a página do Facebook está conectada ao Instagram Business/Creator correto."

    return base



# ==============================
# ATUALIZAR TOKEN META - VÉRTICE IA
# ==============================

@app.post("/api/update-token")
async def api_update_token(request: Request):
    data = await request.json()
    novo_token = str(data.get("token", "")).strip()

    if not novo_token:
        raise HTTPException(status_code=400, detail="Token vazio. Cole um token válido.")

    if len(novo_token) < 50:
        raise HTTPException(status_code=400, detail="Token muito curto. Verifique se copiou completo.")

    env_path = Path(__file__).parent / ".env"

    if env_path.exists():
        env_text = env_path.read_text(encoding="utf-8")
    else:
        env_text = ""

    if "FACEBOOK_ACCESS_TOKEN=" in env_text:
        env_text = re.sub(
            r"(?m)^FACEBOOK_ACCESS_TOKEN=.*$",
            f"FACEBOOK_ACCESS_TOKEN={novo_token}",
            env_text
        )
    else:
        env_text = env_text.rstrip() + f"\nFACEBOOK_ACCESS_TOKEN={novo_token}\n"

    env_path.write_text(env_text, encoding="utf-8")

    return {
        "status": "sucesso",
        "message": "Token salvo no backend/.env. Reinicie a VÉRTICE IA para usar o novo token.",
        "next_step": "Pare o sistema com Ctrl+C e rode iniciar_vertice_ia.bat novamente."
    }



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
        "{id,username,name,followers_count,media_count,"
        f"media.limit({limit})"
        "{id,caption,media_type,permalink,timestamp,like_count,comments_count}}"
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
        "positioning_text": posicionamento_atual,
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



# ==============================
# HISTÓRICO COMERCIAL DE CLIENTES - VÉRTICE IA
# ==============================

def _commercial_history_db_path():
    return Path(__file__).resolve().parent / "vertice_ia_limpa.db"

def _ensure_commercial_history_table():
    db = _commercial_history_db_path()
    conn = sqlite3.connect(db)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS commercial_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client TEXT,
                instagram TEXT,
                segment TEXT,
                proposal_value TEXT,
                proposal_status TEXT,
                notes TEXT,
                profile_payload TEXT,
                proposal_payload TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    finally:
        conn.close()

def _commercial_row_to_dict(row):
    if row is None:
        return None

    data = dict(row)

    for key in ["profile_payload", "proposal_payload"]:
        try:
            data[key] = json.loads(data.get(key) or "{}")
        except Exception:
            data[key] = {}

    return data

@app.post("/api/commercial-history/save")
def api_commercial_history_save(payload: dict):
    _ensure_commercial_history_table()

    client = (payload.get("client") or "").strip()
    instagram = (payload.get("instagram") or "").strip()
    segment = (payload.get("segment") or "").strip()
    proposal_value = (payload.get("proposal_value") or "").strip()
    proposal_status = (payload.get("proposal_status") or "Análise feita").strip()
    notes = (payload.get("notes") or "").strip()

    profile_payload = payload.get("profile_payload") or {}
    proposal_payload = payload.get("proposal_payload") or {}

    if not client and not instagram:
        raise HTTPException(status_code=400, detail="Informe pelo menos o nome do cliente ou o Instagram.")

    item_id = payload.get("id")

    db = _commercial_history_db_path()
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row

    try:
        if item_id:
            conn.execute("""
                UPDATE commercial_history
                   SET client = ?,
                       instagram = ?,
                       segment = ?,
                       proposal_value = ?,
                       proposal_status = ?,
                       notes = ?,
                       profile_payload = ?,
                       proposal_payload = ?,
                       updated_at = CURRENT_TIMESTAMP
                 WHERE id = ?
            """, (
                client,
                instagram,
                segment,
                proposal_value,
                proposal_status,
                notes,
                json.dumps(profile_payload, ensure_ascii=False),
                json.dumps(proposal_payload, ensure_ascii=False),
                item_id
            ))
        else:
            cur = conn.execute("""
                INSERT INTO commercial_history (
                    client,
                    instagram,
                    segment,
                    proposal_value,
                    proposal_status,
                    notes,
                    profile_payload,
                    proposal_payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                client,
                instagram,
                segment,
                proposal_value,
                proposal_status,
                notes,
                json.dumps(profile_payload, ensure_ascii=False),
                json.dumps(proposal_payload, ensure_ascii=False)
            ))
            item_id = cur.lastrowid

        conn.commit()

        row = conn.execute(
            "SELECT * FROM commercial_history WHERE id = ?",
            (item_id,)
        ).fetchone()

        return {
            "status": "sucesso",
            "message": "Histórico comercial salvo.",
            "item": _commercial_row_to_dict(row)
        }

    finally:
        conn.close()

@app.get("/api/commercial-history")
def api_commercial_history_list(q: str = "", status: str = "", limit: int = 100):
    _ensure_commercial_history_table()

    try:
        limit = int(limit or 100)
    except Exception:
        limit = 100

    limit = max(1, min(limit, 300))

    q = (q or "").strip()
    status = (status or "").strip()

    where = []
    params = []

    if q:
        where.append("(client LIKE ? OR instagram LIKE ? OR segment LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like, like])

    if status:
        where.append("proposal_status = ?")
        params.append(status)

    sql = "SELECT * FROM commercial_history"

    if where:
        sql += " WHERE " + " AND ".join(where)

    sql += " ORDER BY updated_at DESC, id DESC LIMIT ?"
    params.append(limit)

    db = _commercial_history_db_path()
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row

    try:
        rows = conn.execute(sql, params).fetchall()

        return {
            "status": "sucesso",
            "total": len(rows),
            "items": [_commercial_row_to_dict(row) for row in rows]
        }

    finally:
        conn.close()

@app.get("/api/commercial-history/{item_id}")
def api_commercial_history_get(item_id: int):
    _ensure_commercial_history_table()

    db = _commercial_history_db_path()
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row

    try:
        row = conn.execute(
            "SELECT * FROM commercial_history WHERE id = ?",
            (item_id,)
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Registro não encontrado.")

        return {
            "status": "sucesso",
            "item": _commercial_row_to_dict(row)
        }

    finally:
        conn.close()

@app.delete("/api/commercial-history/{item_id}")
def api_commercial_history_delete(item_id: int):
    _ensure_commercial_history_table()

    db = _commercial_history_db_path()
    conn = sqlite3.connect(db)

    try:
        cur = conn.execute(
            "DELETE FROM commercial_history WHERE id = ?",
            (item_id,)
        )

        conn.commit()

        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Registro não encontrado.")

        return {
            "status": "sucesso",
            "message": "Registro removido do histórico comercial."
        }

    finally:
        conn.close()



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
    return "https://appverticeia.com.br/api/facebook-login/callback"

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


def _meta_graph_get(path: str, token_or_params=None, params: dict | None = None):
    """
    Função compatível com os dois formatos usados na VÉRTICE:

    1) _meta_graph_get("me", user_token, {"fields": "id,name"})
    2) _meta_graph_get("me/accounts", {"fields": "...", "access_token": token})
    """
    import os, requests

    api_version = os.getenv("META_API_VERSION", "v25.0")
    url = f"https://graph.facebook.com/{api_version}/{path.lstrip('/')}"

    # Formato antigo: path, token, params
    if isinstance(token_or_params, str):
        final_params = params.copy() if isinstance(params, dict) else {}
        final_params["access_token"] = token_or_params

    # Formato novo: path, params
    elif isinstance(token_or_params, dict):
        final_params = token_or_params.copy()

    # Sem params
    else:
        final_params = params.copy() if isinstance(params, dict) else {}

    try:
        r = requests.get(url, params=final_params, timeout=30)
        data = r.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "message": "Erro ao chamar Graph API.",
            "path": path,
            "error": str(e)
        })

    if isinstance(data, dict) and data.get("error"):
        raise HTTPException(status_code=400, detail={
            "message": "Erro retornado pela Meta.",
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


@app.get("/api/facebook-login/debug-redirect")
def api_facebook_login_debug_redirect():
    return {
        "status": "sucesso",
        "running_file": __file__,
        "redirect_function": _meta_redirect_uri(),
        "redirect_final_constant": VERTICE_META_REDIRECT_FINAL,
        "env_redirect": os.getenv("META_REDIRECT_URI", ""),
        "base_url": VERTICE_META_BASE_URL_FINAL
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
        "redirect_uri": "https://appverticeia.com.br/api/facebook-login/callback",
        "state": state,
        "response_type": "code",
        "scope": _meta_login_scopes()
    }

    login_url = f"https://www.facebook.com/{version}/dialog/oauth?" + urllib.parse.urlencode(params)

    return {
        "status": "sucesso",
        "login_url": login_url,
        "redirect_uri": "https://appverticeia.com.br/api/facebook-login/callback",
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


app.mount('/static', StaticFiles(directory=str(STATIC_DIR)), name='static')


# ==== VERTICE META COMERCIAL ISOLADO ====

VERTICE_META_COMERCIAL_HTML = r"""
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Meta Comercial | VÉRTICE IA</title>
<style>
  body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: #f4f5f7;
    color: #111827;
  }
  .wrap {
    max-width: 1120px;
    margin: 32px auto;
    padding: 0 20px 50px;
  }
  .top {
    background: #111827;
    color: white;
    border-radius: 22px;
    padding: 28px;
    margin-bottom: 22px;
  }
  .brand {
    color: #f4b400;
    letter-spacing: 4px;
    font-size: 12px;
    font-weight: 800;
  }
  h1 {
    margin: 8px 0 8px;
    font-size: 34px;
  }
  .sub {
    opacity: .8;
    max-width: 760px;
    line-height: 1.5;
  }
  .grid {
    display: grid;
    grid-template-columns: 1fr 1.4fr;
    gap: 18px;
  }
  .card {
    background: white;
    border-radius: 18px;
    padding: 20px;
    box-shadow: 0 12px 30px rgba(15,23,42,.08);
  }
  h2 {
    margin: 0 0 14px;
    font-size: 20px;
  }
  button {
    border: none;
    background: #111827;
    color: white;
    padding: 11px 15px;
    border-radius: 12px;
    cursor: pointer;
    font-weight: 700;
    margin: 4px 4px 4px 0;
  }
  button.secondary {
    background: #f4b400;
    color: #111827;
  }
  button.light {
    background: #e5e7eb;
    color: #111827;
  }
  .account {
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    padding: 14px;
    margin-bottom: 10px;
    cursor: pointer;
  }
  .account:hover {
    border-color: #f4b400;
  }
  .account.active {
    border-color: #f4b400;
    background: #fffbeb;
  }
  .muted {
    color: #6b7280;
    font-size: 13px;
  }
  .result {
    white-space: pre-wrap;
    background: #0f172a;
    color: #e5e7eb;
    border-radius: 14px;
    padding: 16px;
    max-height: 460px;
    overflow: auto;
    font-size: 12px;
  }
  .diagnosis {
    line-height: 1.55;
  }
  .diagnosis li {
    margin-bottom: 8px;
  }
  input {
    width: 100%;
    box-sizing: border-box;
    padding: 12px;
    border-radius: 12px;
    border: 1px solid #d1d5db;
    margin-bottom: 10px;
  }
  .history-item {
    border-bottom: 1px solid #e5e7eb;
    padding: 12px 0;
  }
  @media (max-width: 820px) {
    .grid { grid-template-columns: 1fr; }
  }
</style>
</head>
<body>
<div class="wrap">
  <section class="top">
    <div class="brand">VÉRTICE IA</div>
    <h1>Relatório Comercial Meta</h1>
    <div class="sub">
      Área isolada para transformar contas conectadas via Meta em diagnóstico comercial,
      histórico e material de apresentação para clientes.
    </div>
  </section>

  <div class="grid">
    <section class="card">
      <h2>1. Contas conectadas</h2>
      <button onclick="carregarContas()">Atualizar contas conectadas</button>
      <div id="accounts" class="muted" style="margin-top:12px;">Clique em atualizar para carregar.</div>
    </section>

    <section class="card">
      <h2>2. Relatório e diagnóstico</h2>
      <input id="clientName" placeholder="Nome do cliente / empresa">
      <input id="clientInstagram" placeholder="@ do Instagram do cliente">
      <button class="secondary" onclick="gerarInsights()">Gerar relatório com insights</button>
      <button onclick="salvarHistorico()">Salvar no histórico</button>
      <button class="light" onclick="abrirPdf()">Abrir versão PDF</button>
      <button class="light" onclick="copiarDiagnostico()">Copiar diagnóstico</button>

      <div id="diagnosis" class="diagnosis muted" style="margin-top:18px;">
        Gere um relatório para visualizar a análise comercial.
      </div>
    </section>
  </div>

  <section class="card" style="margin-top:18px;">
    <h2>Dados técnicos do relatório</h2>
    <div id="raw" class="result">Nenhum relatório gerado ainda.</div>
  </section>

  <section class="card" style="margin-top:18px;">
    <h2>Histórico Meta Comercial</h2>
    <button onclick="carregarHistorico()">Atualizar histórico</button>
    <div id="history" class="muted" style="margin-top:12px;">Nenhum histórico carregado.</div>
  </section>
</div>

<script>
let selectedAccount = null;
let lastReport = null;
let lastDiagnosisText = "";

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function normalizeAccounts(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data.accounts)) return data.accounts;
  if (Array.isArray(data.items)) return data.items;
  if (Array.isArray(data.data)) return data.data;
  if (Array.isArray(data.results)) return data.results;
  if (Array.isArray(data.connected_accounts)) return data.connected_accounts;
  if (data.account) return [data.account];
  return [];
}

function accountId(acc) {
  return (
    acc.id ||
    acc.account_id ||
    acc.connected_account_id ||
    acc.row_id ||
    acc.db_id ||
    acc.meta_account_id ||
    acc.instagram_business_account_id ||
    acc.ig_user_id ||
    acc.instagram_id ||
    acc.page_id
  );
}

function accountName(acc) {
  return acc.instagram_username || acc.username || acc.name || acc.page_name || acc.client_name || "Conta conectada";
}

async function carregarContas() {
  const box = document.getElementById("accounts");
  box.innerHTML = "Carregando...";

  try {
    const res = await fetch("/api/meta-connected/accounts", { credentials: "include" });
    const data = await res.json();

    if (!res.ok) {
      box.innerHTML = "Erro ao carregar contas: " + escapeHtml(JSON.stringify(data));
      return;
    }

    const accounts = normalizeAccounts(data);

    if (!accounts.length) {
      box.innerHTML = "Nenhuma conta conectada encontrada.";
      return;
    }

    box.innerHTML = accounts.map((acc, i) => {
      const id = accountId(acc);
      return `
        <div class="account" onclick="selecionarConta(${i})" id="acc-${i}">
          <strong>${escapeHtml(accountName(acc))}</strong>
          <div class="muted">ID interno: ${escapeHtml(id || "não identificado")}</div>
        </div>
      `;
    }).join("");

    window.__accounts = accounts;
  } catch (e) {
    box.innerHTML = "Erro: " + escapeHtml(e.message);
  }
}

function selecionarConta(i) {
  selectedAccount = window.__accounts[i];

  document.querySelectorAll(".account").forEach(el => el.classList.remove("active"));
  const el = document.getElementById("acc-" + i);
  if (el) el.classList.add("active");

  document.getElementById("clientInstagram").value = accountName(selectedAccount);
}

function gerarDiagnostico(report) {
  const text = JSON.stringify(report || {}).toLowerCase();

  const pontos = [];
  const ajustes = [];
  const recomendacoes = [];

  if (text.includes("reach") || text.includes("alcance")) {
    pontos.push("A conta possui dados de alcance disponíveis, permitindo analisar visibilidade real.");
  }

  if (text.includes("impression") || text.includes("impress")) {
    pontos.push("Existem dados de impressões, úteis para medir exposição e repetição da marca.");
  }

  if (text.includes("follower") || text.includes("seguidor")) {
    pontos.push("A base de seguidores pode ser acompanhada para medir evolução do perfil.");
  }

  if (text.includes("engagement") || text.includes("like") || text.includes("comment")) {
    pontos.push("Há dados de interação que ajudam a avaliar força de conteúdo e relacionamento.");
  }

  if (!pontos.length) {
    pontos.push("A conta retornou dados autorizados pela Meta, mas a leitura precisa ser acompanhada com histórico.");
  }

  ajustes.push("Criar rotina mensal de comparação para identificar crescimento, queda ou estagnação.");
  ajustes.push("Transformar métricas em decisões de conteúdo, não apenas em números soltos.");
  ajustes.push("Separar conteúdos por pilares: autoridade, relacionamento, prova social e oferta.");

  recomendacoes.push("Usar os insights para definir os formatos com maior potencial de entrega.");
  recomendacoes.push("Gerar relatório comercial mensal para demonstrar evolução ao cliente.");
  recomendacoes.push("Conectar análise de dados com proposta de gestão, posicionamento e tráfego pago.");

  lastDiagnosisText =
`DIAGNÓSTICO COMERCIAL VÉRTICE IA

Pontos identificados:
${pontos.map(x => "- " + x).join("\n")}

Ajustes necessários:
${ajustes.map(x => "- " + x).join("\n")}

Recomendações:
${recomendacoes.map(x => "- " + x).join("\n")}

Conclusão:
A conta já pode ser analisada com base em dados reais. O próximo avanço é usar essas informações para justificar estratégia, constância e posicionamento comercial.`;

  return `
    <h3>Diagnóstico comercial</h3>
    <h4>Pontos identificados</h4>
    <ul>${pontos.map(x => `<li>${escapeHtml(x)}</li>`).join("")}</ul>
    <h4>Ajustes necessários</h4>
    <ul>${ajustes.map(x => `<li>${escapeHtml(x)}</li>`).join("")}</ul>
    <h4>Recomendações</h4>
    <ul>${recomendacoes.map(x => `<li>${escapeHtml(x)}</li>`).join("")}</ul>
  `;
}

async function gerarInsights() {
  if (!selectedAccount) {
    alert("Selecione uma conta conectada primeiro.");
    return;
  }

  const id = accountId(selectedAccount);

  if (!id) {
    document.getElementById("diagnosis").innerHTML = "Não localizei o ID interno da conta conectada.";
    document.getElementById("raw").textContent = JSON.stringify(selectedAccount, null, 2);
    alert("Não localizei o ID interno da conta conectada. Veja os dados técnicos na tela.");
    return;
  }

  document.getElementById("diagnosis").innerHTML = "Gerando relatório...";
  document.getElementById("raw").textContent = "Carregando dados...";

  try {
    const url = `/api/meta-connected/accounts/${encodeURIComponent(id)}/insights`;

    const res = await fetch(url, {
      credentials: "include"
    });

    const data = await res.json();

    if (!res.ok) {
      document.getElementById("diagnosis").innerHTML = "Erro ao gerar insights. Veja os dados técnicos abaixo.";
      document.getElementById("raw").textContent = JSON.stringify({
        endpoint_usado: url,
        id_usado: id,
        conta_selecionada: selectedAccount,
        erro: data
      }, null, 2);
      return;
    }

    lastReport = data;
    document.getElementById("diagnosis").innerHTML = gerarDiagnostico(data);
    document.getElementById("raw").textContent = JSON.stringify(data, null, 2);
  } catch (e) {
    document.getElementById("diagnosis").innerHTML = "Erro: " + escapeHtml(e.message);
  }
}

async function salvarHistorico() {
  if (!lastReport) {
    alert("Gere o relatório antes de salvar.");
    return;
  }

  const payload = {
    client_name: document.getElementById("clientName").value.trim(),
    instagram_username: document.getElementById("clientInstagram").value.trim(),
    account: selectedAccount,
    report: lastReport,
    diagnosis_text: lastDiagnosisText
  };

  const res = await fetch("/api/meta-commercial/save", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  const data = await res.json();

  if (!res.ok) {
    alert("Erro ao salvar: " + JSON.stringify(data));
    return;
  }

  alert("Relatório salvo no histórico Meta Comercial.");
  carregarHistorico();
}

async function carregarHistorico() {
  const box = document.getElementById("history");
  box.innerHTML = "Carregando...";

  const res = await fetch("/api/meta-commercial/history", { credentials: "include" });
  const data = await res.json();

  const items = Array.isArray(data.items) ? data.items : [];

  if (!items.length) {
    box.innerHTML = "Nenhum item salvo ainda.";
    return;
  }

  box.innerHTML = items.map(item => `
    <div class="history-item">
      <strong>${escapeHtml(item.client_name || "Cliente sem nome")}</strong>
      <div class="muted">${escapeHtml(item.instagram_username || "")}</div>
      <div class="muted">Salvo em: ${escapeHtml(item.created_at)}</div>
    </div>
  `).join("");
}

function abrirPdf() {
  if (!lastReport) {
    alert("Gere o relatório antes.");
    return;
  }

  const cliente = document.getElementById("clientName").value.trim() || "Cliente";
  const insta = document.getElementById("clientInstagram").value.trim() || accountName(selectedAccount || {});

  const html = `
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Relatório Comercial Meta - VÉRTICE IA</title>
<style>
  body { font-family: Arial, sans-serif; margin: 0; color: #111827; background: #f4f5f7; }
  .page { max-width: 900px; margin: 30px auto; background: white; padding: 42px; border-radius: 18px; }
  .brand { letter-spacing: 4px; font-size: 12px; color: #f4b400; font-weight: 800; }
  h1 { font-size: 32px; margin: 8px 0 12px; }
  h2 { border-bottom: 1px solid #ddd; padding-bottom: 8px; margin-top: 28px; }
  pre { white-space: pre-wrap; background: #111827; color: white; padding: 16px; border-radius: 12px; font-size: 12px; }
  li { margin-bottom: 8px; line-height: 1.5; }
  @media print { body { background: white; } .page { margin: 0; border-radius: 0; } }
</style>
</head>
<body>
<div class="page">
  <div class="brand">VÉRTICE IA</div>
  <h1>Relatório Comercial Meta</h1>
  <p><strong>Cliente:</strong> ${escapeHtml(cliente)}</p>
  <p><strong>Instagram:</strong> ${escapeHtml(insta)}</p>
  <h2>Diagnóstico</h2>
  <pre>${escapeHtml(lastDiagnosisText)}</pre>
  <h2>Dados técnicos</h2>
  <pre>${escapeHtml(JSON.stringify(lastReport, null, 2))}</pre>
</div>
</body>
</html>`;

  const w = window.open("", "_blank");
  w.document.open();
  w.document.write(html);
  w.document.close();
  setTimeout(() => {
    w.focus();
    w.print();
  }, 500);
}

async function copiarDiagnostico() {
  if (!lastDiagnosisText) {
    alert("Gere o relatório antes.");
    return;
  }

  await navigator.clipboard.writeText(lastDiagnosisText);
  alert("Diagnóstico copiado.");
}
</script>
</body>
</html>
"""

def _vertice_meta_commercial_db_path():
    import os
    from pathlib import Path

    try:
        return _meta_client_db_path()
    except Exception:
        db_name = os.getenv("VERTICE_DB_PATH", "vertice_ia_limpa.db")
        return str(Path(__file__).with_name(db_name))

def _ensure_meta_commercial_table():
    import sqlite3

    db = _vertice_meta_commercial_db_path()
    conn = sqlite3.connect(db)

    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS meta_commercial_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                client_name TEXT,
                instagram_username TEXT,
                account_json TEXT,
                report_json TEXT,
                diagnosis_text TEXT
            )
        """)
        conn.commit()
    finally:
        conn.close()

@app.get("/meta-comercial")
def meta_comercial_page():
    from fastapi.responses import HTMLResponse
    return HTMLResponse(VERTICE_META_COMERCIAL_HTML)

@app.post("/api/meta-commercial/save")
async def api_meta_commercial_save(request: Request):
    import json
    import sqlite3
    from datetime import datetime

    _ensure_meta_commercial_table()

    payload = await request.json()

    client_name = (payload.get("client_name") or "").strip()
    instagram_username = (payload.get("instagram_username") or "").strip()
    account = payload.get("account") or {}
    report = payload.get("report") or {}
    diagnosis_text = payload.get("diagnosis_text") or ""

    db = _vertice_meta_commercial_db_path()
    conn = sqlite3.connect(db)

    try:
        cur = conn.execute(
            """
            INSERT INTO meta_commercial_reports
            (created_at, client_name, instagram_username, account_json, report_json, diagnosis_text)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().isoformat(timespec="seconds"),
                client_name,
                instagram_username,
                json.dumps(account, ensure_ascii=False),
                json.dumps(report, ensure_ascii=False),
                diagnosis_text
            )
        )
        conn.commit()
        item_id = cur.lastrowid
    finally:
        conn.close()

    return {
        "status": "salvo",
        "id": item_id,
        "message": "Relatório Meta Comercial salvo com sucesso."
    }

@app.get("/api/meta-commercial/history")
def api_meta_commercial_history():
    import sqlite3

    _ensure_meta_commercial_table()

    db = _vertice_meta_commercial_db_path()
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row

    try:
        rows = conn.execute(
            """
            SELECT id, created_at, client_name, instagram_username, diagnosis_text
            FROM meta_commercial_reports
            ORDER BY id DESC
            LIMIT 50
            """
        ).fetchall()
    finally:
        conn.close()

    return {
        "status": "sucesso",
        "items": [dict(row) for row in rows]
    }

# ==== FIM VERTICE META COMERCIAL ISOLADO ====


# ==== VERTICE META COMERCIAL PRO ====

VERTICE_META_COMERCIAL_PRO_HTML = r"""
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Meta Comercial Pro | VÉRTICE IA</title>
<style>
  body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: #f3f4f6;
    color: #111827;
  }

  .wrap {
    max-width: 1180px;
    margin: 28px auto;
    padding: 0 20px 50px;
  }

  .hero {
    background: linear-gradient(135deg, #111827, #1f2937);
    color: white;
    border-radius: 24px;
    padding: 32px;
    margin-bottom: 20px;
  }

  .brand {
    color: #f4b400;
    font-size: 12px;
    letter-spacing: 4px;
    font-weight: 800;
    text-transform: uppercase;
  }

  h1 {
    margin: 10px 0;
    font-size: 36px;
  }

  .hero p {
    max-width: 760px;
    color: #d1d5db;
    line-height: 1.5;
  }

  .grid {
    display: grid;
    grid-template-columns: 380px 1fr;
    gap: 18px;
  }

  .card {
    background: white;
    border-radius: 20px;
    padding: 22px;
    box-shadow: 0 14px 34px rgba(15, 23, 42, .08);
  }

  h2 {
    margin: 0 0 14px;
    font-size: 20px;
  }

  label {
    display: block;
    font-size: 13px;
    font-weight: 700;
    margin-bottom: 6px;
    color: #374151;
  }

  input, textarea {
    width: 100%;
    box-sizing: border-box;
    border: 1px solid #d1d5db;
    border-radius: 12px;
    padding: 12px;
    margin-bottom: 12px;
    font-family: Arial, sans-serif;
  }

  textarea {
    min-height: 88px;
  }

  button {
    border: none;
    background: #111827;
    color: white;
    padding: 11px 15px;
    border-radius: 12px;
    cursor: pointer;
    font-weight: 700;
    margin: 4px 4px 4px 0;
  }

  button.gold {
    background: #f4b400;
    color: #111827;
  }

  button.light {
    background: #e5e7eb;
    color: #111827;
  }

  .account {
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    padding: 14px;
    margin-bottom: 10px;
    cursor: pointer;
  }

  .account.active {
    background: #fffbeb;
    border-color: #f4b400;
  }

  .muted {
    color: #6b7280;
    font-size: 13px;
    line-height: 1.45;
  }

  .report {
    margin-top: 18px;
    border-top: 1px solid #e5e7eb;
    padding-top: 18px;
  }

  .kpis {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
    margin: 16px 0;
  }

  .kpi {
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    padding: 14px;
  }

  .kpi small {
    display: block;
    color: #6b7280;
    margin-bottom: 6px;
  }

  .kpi strong {
    font-size: 20px;
  }

  li {
    margin-bottom: 8px;
    line-height: 1.5;
  }

  pre {
    background: #0f172a;
    color: #e5e7eb;
    padding: 16px;
    border-radius: 14px;
    white-space: pre-wrap;
    max-height: 380px;
    overflow: auto;
    font-size: 12px;
  }

  .history-item {
    border-bottom: 1px solid #e5e7eb;
    padding: 12px 0;
  }

  @media (max-width: 900px) {
    .grid { grid-template-columns: 1fr; }
    .kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  }
</style>
</head>
<body>
<div class="wrap">
  <section class="hero">
    <div class="brand">VÉRTICE IA</div>
    <h1>Meta Comercial Pro</h1>
    <p>
      Gere um diagnóstico comercial com dados reais da Meta, salve histórico e abra uma versão pronta para PDF.
      Esta área é isolada para não interferir no painel principal da VÉRTICE.
    </p>
  </section>

  <div class="grid">
    <section class="card">
      <h2>Contas conectadas</h2>
      <button onclick="carregarContas()">Atualizar contas</button>
      <div id="accounts" class="muted" style="margin-top:12px;">Clique em atualizar para carregar as contas conectadas.</div>

      <hr style="border:none;border-top:1px solid #e5e7eb;margin:22px 0;">

      <h2>Dados comerciais</h2>

      <label>Nome do cliente / empresa</label>
      <input id="clientName" placeholder="Ex: Espaço TM Pilates">

      <label>Instagram</label>
      <input id="clientInstagram" placeholder="@cliente">

      <label>Objetivo comercial</label>
      <textarea id="clientObjective" placeholder="Ex: fortalecer posicionamento, aumentar visibilidade e acompanhar evolução mensal."></textarea>

      <button class="gold" onclick="gerarInsights()">Gerar diagnóstico</button>
      <button onclick="salvarHistorico()">Salvar histórico</button>
      <button class="light" onclick="abrirPdf()">Abrir PDF</button>
      <button class="light" onclick="copiarDiagnostico()">Copiar texto</button>
    </section>

    <section class="card">
      <h2>Relatório Comercial</h2>
      <div id="reportArea" class="muted">
        Selecione uma conta conectada e clique em gerar diagnóstico.
      </div>
    </section>
  </div>

  <section class="card" style="margin-top:18px;">
    <h2>Histórico Meta Comercial</h2>
    <button onclick="carregarHistorico()">Atualizar histórico</button>
    <div id="history" class="muted" style="margin-top:12px;">Nenhum histórico carregado.</div>
  </section>

  <section class="card" style="margin-top:18px;">
    <h2>Dados técnicos</h2>
    <pre id="raw">Nenhum relatório gerado ainda.</pre>
  </section>
</div>

<script>
let selectedAccount = null;
let lastReport = null;
let lastDiagnosis = "";

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function normalizeAccounts(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data.accounts)) return data.accounts;
  if (Array.isArray(data.items)) return data.items;
  if (Array.isArray(data.data)) return data.data;
  if (Array.isArray(data.connected_accounts)) return data.connected_accounts;
  if (data.account) return [data.account];
  return [];
}

function accountId(acc) {
  return acc.id || acc.account_id || acc.connected_account_id || acc.row_id || acc.db_id || acc.instagram_business_account_id || acc.ig_user_id;
}

function accountName(acc) {
  return acc.instagram_username || acc.username || acc.name || acc.page_name || acc.client_name || "Conta conectada";
}

function extractMetric(report, names) {
  const found = [];

  function walk(value) {
    if (!value || typeof value !== "object") return;

    if (Array.isArray(value)) {
      value.forEach(walk);
      return;
    }

    for (const [k, v] of Object.entries(value)) {
      const key = String(k).toLowerCase();

      for (const name of names) {
        if (key.includes(name.toLowerCase())) {
          if (typeof v === "number" || typeof v === "string") found.push(v);
        }
      }

      walk(v);
    }
  }

  walk(report);
  return found[0] ?? "—";
}

async function carregarContas() {
  const box = document.getElementById("accounts");
  box.innerHTML = "Carregando...";

  try {
    const res = await fetch("/api/meta-connected/accounts", { credentials: "include" });
    const data = await res.json();

    if (!res.ok) {
      box.innerHTML = "Erro ao carregar contas: " + escapeHtml(JSON.stringify(data));
      return;
    }

    const accounts = normalizeAccounts(data);
    window.__metaAccounts = accounts;

    if (!accounts.length) {
      box.innerHTML = "Nenhuma conta conectada encontrada.";
      return;
    }

    box.innerHTML = accounts.map((acc, i) => {
      return `
        <div class="account" id="account-${i}" onclick="selecionarConta(${i})">
          <strong>${escapeHtml(accountName(acc))}</strong>
          <div class="muted">ID: ${escapeHtml(accountId(acc) || "não identificado")}</div>
        </div>
      `;
    }).join("");
  } catch (e) {
    box.innerHTML = "Erro: " + escapeHtml(e.message);
  }
}

function selecionarConta(i) {
  selectedAccount = window.__metaAccounts[i];

  document.querySelectorAll(".account").forEach(el => el.classList.remove("active"));
  const el = document.getElementById("account-" + i);
  if (el) el.classList.add("active");

  const insta = accountName(selectedAccount);
  document.getElementById("clientInstagram").value = insta;
}

function montarDiagnostico(report) {
  const cliente = document.getElementById("clientName").value.trim() || "Cliente";
  const instagram = document.getElementById("clientInstagram").value.trim() || accountName(selectedAccount || {});
  const objetivo = document.getElementById("clientObjective").value.trim() || "fortalecer presença digital, posicionamento e leitura estratégica dos dados.";

  const texto = JSON.stringify(report || {}).toLowerCase();

  const alcance = extractMetric(report, ["reach", "alcance"]);
  const impressoes = extractMetric(report, ["impressions", "impress"]);
  const seguidores = extractMetric(report, ["followers", "seguidor"]);
  const engajamento = extractMetric(report, ["engagement", "engaj"]);

  const pontos = [];
  const ajustes = [];
  const recomendacoes = [];

  if (texto.includes("reach") || texto.includes("alcance")) {
    pontos.push("A conta apresenta dados de alcance, permitindo avaliar a visibilidade real do perfil.");
  }

  if (texto.includes("impression") || texto.includes("impress")) {
    pontos.push("Existem dados de impressões, o que ajuda a entender a frequência de exposição da marca.");
  }

  if (texto.includes("follower") || texto.includes("seguidor")) {
    pontos.push("A base de seguidores pode ser monitorada para identificar evolução, estagnação ou queda.");
  }

  if (texto.includes("engagement") || texto.includes("like") || texto.includes("comment")) {
    pontos.push("Há dados de interação que podem orientar conteúdos mais fortes e relacionais.");
  }

  if (!pontos.length) {
    pontos.push("A conta possui conexão ativa, mas precisa de acompanhamento histórico para gerar leitura mais profunda.");
  }

  ajustes.push("Transformar métricas em decisões práticas de conteúdo.");
  ajustes.push("Definir pilares editoriais claros: autoridade, relacionamento, prova social e oferta.");
  ajustes.push("Acompanhar evolução mensal para evitar decisões baseadas em achismo.");
  ajustes.push("Usar os dados da Meta para justificar frequência, formatos e campanhas.");

  recomendacoes.push("Criar relatório mensal para mostrar evolução ao cliente.");
  recomendacoes.push("Organizar calendário de conteúdo com base no comportamento real do perfil.");
  recomendacoes.push("Usar os dados como base para proposta de gestão, posicionamento e tráfego.");
  recomendacoes.push("Construir comunicação com mais autoridade e menos conteúdo genérico.");

  lastDiagnosis =
`RELATÓRIO COMERCIAL - VÉRTICE IA

Cliente: ${cliente}
Instagram: ${instagram}
Objetivo: ${objetivo}

Resumo das métricas identificadas:
- Alcance: ${alcance}
- Impressões: ${impressoes}
- Seguidores: ${seguidores}
- Engajamento: ${engajamento}

Pontos identificados:
${pontos.map(x => "- " + x).join("\n")}

Ajustes necessários:
${ajustes.map(x => "- " + x).join("\n")}

Recomendações:
${recomendacoes.map(x => "- " + x).join("\n")}

Conclusão:
A conta já pode ser analisada com dados reais. A VÉRTICE IA transforma esses dados em leitura comercial para demonstrar valor, organizar estratégia e fortalecer o posicionamento digital do cliente.`;

  return {
    cliente,
    instagram,
    objetivo,
    alcance,
    impressoes,
    seguidores,
    engajamento,
    pontos,
    ajustes,
    recomendacoes
  };
}

function renderReport(report) {
  const d = montarDiagnostico(report);

  document.getElementById("reportArea").innerHTML = `
    <div class="kpis">
      <div class="kpi"><small>Alcance</small><strong>${escapeHtml(d.alcance)}</strong></div>
      <div class="kpi"><small>Impressões</small><strong>${escapeHtml(d.impressoes)}</strong></div>
      <div class="kpi"><small>Seguidores</small><strong>${escapeHtml(d.seguidores)}</strong></div>
      <div class="kpi"><small>Engajamento</small><strong>${escapeHtml(d.engajamento)}</strong></div>
    </div>

    <div class="report">
      <h3>${escapeHtml(d.cliente)}</h3>
      <p><strong>Instagram:</strong> ${escapeHtml(d.instagram)}</p>
      <p><strong>Objetivo:</strong> ${escapeHtml(d.objetivo)}</p>

      <h3>Pontos identificados</h3>
      <ul>${d.pontos.map(x => `<li>${escapeHtml(x)}</li>`).join("")}</ul>

      <h3>Ajustes necessários</h3>
      <ul>${d.ajustes.map(x => `<li>${escapeHtml(x)}</li>`).join("")}</ul>

      <h3>Recomendações</h3>
      <ul>${d.recomendacoes.map(x => `<li>${escapeHtml(x)}</li>`).join("")}</ul>
    </div>
  `;
}

async function gerarInsights() {
  if (!selectedAccount) {
    alert("Selecione uma conta conectada primeiro.");
    return;
  }

  const id = accountId(selectedAccount);

  if (!id) {
    document.getElementById("raw").textContent = JSON.stringify(selectedAccount, null, 2);
    alert("Não localizei o ID da conta conectada.");
    return;
  }

  document.getElementById("reportArea").innerHTML = "Gerando diagnóstico...";
  document.getElementById("raw").textContent = "Carregando...";

  try {
    const res = await fetch(`/api/meta-connected/accounts/${encodeURIComponent(id)}/insights`, {
      credentials: "include"
    });

    const data = await res.json();

    if (!res.ok) {
      document.getElementById("reportArea").innerHTML = "Erro ao gerar relatório.";
      document.getElementById("raw").textContent = JSON.stringify(data, null, 2);
      return;
    }

    lastReport = data;
    renderReport(data);
    document.getElementById("raw").textContent = JSON.stringify(data, null, 2);
  } catch (e) {
    document.getElementById("reportArea").innerHTML = "Erro: " + escapeHtml(e.message);
  }
}

async function salvarHistorico() {
  if (!lastReport) {
    alert("Gere o diagnóstico antes de salvar.");
    return;
  }

  const payload = {
    client_name: document.getElementById("clientName").value.trim(),
    instagram_username: document.getElementById("clientInstagram").value.trim(),
    account: selectedAccount,
    report: lastReport,
    diagnosis_text: lastDiagnosis
  };

  const res = await fetch("/api/meta-commercial/save", {
    method: "POST",
    credentials: "include",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  });

  const data = await res.json();

  if (!res.ok) {
    alert("Erro ao salvar: " + JSON.stringify(data));
    return;
  }

  alert("Relatório salvo no histórico.");
  carregarHistorico();
}

async function carregarHistorico() {
  const box = document.getElementById("history");
  box.innerHTML = "Carregando...";

  const res = await fetch("/api/meta-commercial/history", { credentials: "include" });
  const data = await res.json();

  const items = Array.isArray(data.items) ? data.items : [];

  if (!items.length) {
    box.innerHTML = "Nenhum relatório salvo ainda.";
    return;
  }

  box.innerHTML = items.map(item => `
    <div class="history-item">
      <strong>${escapeHtml(item.client_name || "Cliente sem nome")}</strong>
      <div class="muted">${escapeHtml(item.instagram_username || "")}</div>
      <div class="muted">Salvo em: ${escapeHtml(item.created_at || "")}</div>
    </div>
  `).join("");
}

function abrirPdf() {
  if (!lastDiagnosis) {
    alert("Gere o diagnóstico antes.");
    return;
  }

  const html = `
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Relatório Comercial VÉRTICE IA</title>
<style>
  body { font-family: Arial, sans-serif; margin: 0; background: #f3f4f6; color: #111827; }
  .page { max-width: 900px; margin: 30px auto; background: white; padding: 42px; border-radius: 20px; }
  .brand { color: #f4b400; font-size: 12px; letter-spacing: 4px; font-weight: 800; }
  h1 { font-size: 34px; margin: 8px 0 18px; }
  pre { white-space: pre-wrap; background: #111827; color: white; padding: 18px; border-radius: 14px; line-height: 1.5; }
  .footer { color: #6b7280; font-size: 12px; margin-top: 30px; border-top: 1px solid #e5e7eb; padding-top: 18px; }
  @media print { body { background: white; } .page { margin: 0; border-radius: 0; } }
</style>
</head>
<body>
<div class="page">
  <div class="brand">VÉRTICE IA</div>
  <h1>Relatório Comercial Meta</h1>
  <pre>${escapeHtml(lastDiagnosis)}</pre>
  <div class="footer">Relatório gerado pela VÉRTICE IA com base em dados autorizados via Meta.</div>
</div>
</body>
</html>`;

  const w = window.open("", "_blank");
  w.document.open();
  w.document.write(html);
  w.document.close();

  setTimeout(() => {
    w.focus();
    w.print();
  }, 500);
}

async function copiarDiagnostico() {
  if (!lastDiagnosis) {
    alert("Gere o diagnóstico antes.");
    return;
  }

  await navigator.clipboard.writeText(lastDiagnosis);
  alert("Diagnóstico copiado.");
}
</script>
</body>
</html>
"""

@app.get("/meta-comercial-pro")
def meta_comercial_pro_page():
    from fastapi.responses import HTMLResponse
    return HTMLResponse(VERTICE_META_COMERCIAL_PRO_HTML)

# ==== FIM VERTICE META COMERCIAL PRO ====


# ==== VERTICE PAGINAS LEGAIS META ====

VERTICE_LEGAL_STYLE = """
<style>
  body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: #f4f5f7;
    color: #111827;
    line-height: 1.65;
  }
  .page {
    max-width: 920px;
    margin: 36px auto;
    background: #fff;
    padding: 42px;
    border-radius: 22px;
    box-shadow: 0 14px 34px rgba(15,23,42,.08);
  }
  .brand {
    color: #f4b400;
    font-size: 12px;
    letter-spacing: 4px;
    font-weight: 800;
    text-transform: uppercase;
  }
  h1 {
    font-size: 34px;
    margin: 10px 0 18px;
  }
  h2 {
    margin-top: 28px;
    font-size: 20px;
    border-bottom: 1px solid #e5e7eb;
    padding-bottom: 8px;
  }
  p, li {
    font-size: 15px;
  }
  .muted {
    color: #6b7280;
    font-size: 13px;
  }
  .box {
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    padding: 16px;
    border-radius: 14px;
  }
  a {
    color: #111827;
    font-weight: 700;
  }
</style>
"""

VERTICE_POLITICA_PRIVACIDADE_HTML = f"""
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Política de Privacidade | VÉRTICE IA</title>
{VERTICE_LEGAL_STYLE}
</head>
<body>
<div class="page">
  <div class="brand">VÉRTICE IA</div>
  <h1>Política de Privacidade</h1>
  <p class="muted">Última atualização: 19/07/2026</p>

  <p>
    A VÉRTICE IA é uma plataforma de análise estratégica de presença digital, criada para apoiar
    empresas e profissionais na leitura de métricas, conteúdos, posicionamento e resultados em canais conectados à Meta.
  </p>

  <h2>1. Dados que podemos coletar</h2>
  <p>
    Quando uma conta é conectada à VÉRTICE IA por meio do Facebook Login/Meta, podemos acessar dados autorizados pelo próprio usuário,
    de acordo com as permissões concedidas no momento da conexão.
  </p>
  <ul>
    <li>Informações básicas da Página do Facebook conectada.</li>
    <li>Informações da conta profissional do Instagram vinculada à Página.</li>
    <li>Nome de usuário, identificação da conta e dados públicos do perfil.</li>
    <li>Métricas e insights de desempenho, como alcance, impressões, interações e dados relacionados ao conteúdo.</li>
    <li>Dados de posts, mídia e indicadores usados para análise estratégica.</li>
  </ul>

  <h2>2. Como usamos os dados</h2>
  <p>
    Os dados são utilizados exclusivamente para gerar análises, relatórios estratégicos, diagnósticos comerciais,
    acompanhamento de evolução e recomendações de conteúdo e posicionamento.
  </p>
  <p>
    A VÉRTICE IA não vende dados pessoais, não promete resultados comerciais garantidos e não usa os dados para fins
    diferentes daqueles relacionados à análise e gestão estratégica autorizada pelo usuário.
  </p>

  <h2>3. Compartilhamento de dados</h2>
  <p>
    Os dados acessados pela VÉRTICE IA não são vendidos a terceiros. As informações podem ser utilizadas internamente
    para gerar relatórios, propostas, históricos comerciais e materiais estratégicos para o próprio cliente conectado.
  </p>

  <h2>4. Armazenamento e segurança</h2>
  <p>
    Algumas informações podem ser armazenadas em banco de dados local ou ambiente controlado da VÉRTICE IA para permitir
    histórico, comparação de evolução e geração de relatórios. Aplicamos medidas razoáveis de proteção para evitar acesso indevido.
  </p>

  <h2>5. Controle do usuário</h2>
  <p>
    O usuário pode solicitar a exclusão dos dados associados à sua conta conectada. As instruções estão disponíveis na página:
  </p>
  <p>
    <a href="/exclusao-dados">https://appverticeia.com.br/exclusao-dados</a>
  </p>

  <h2>6. Revogação de acesso</h2>
  <p>
    O usuário também pode revogar o acesso da VÉRTICE IA diretamente nas configurações da sua conta Meta/Facebook,
    na seção de aplicativos e sites conectados.
  </p>

  <h2>7. Contato</h2>
  <div class="box">
    <p>
      Para dúvidas sobre privacidade ou solicitação de exclusão de dados, entre em contato:
    </p>
    <p>
      <strong>E-mail:</strong> jujujulia.gomes757@gmail.com
    </p>
    <p>
      <strong>Responsável:</strong> Júlia Gomes Alves
    </p>
  </div>
</div>
</body>
</html>
"""

VERTICE_EXCLUSAO_DADOS_HTML = f"""
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Exclusão de Dados | VÉRTICE IA</title>
{VERTICE_LEGAL_STYLE}
</head>
<body>
<div class="page">
  <div class="brand">VÉRTICE IA</div>
  <h1>Instruções para Exclusão de Dados</h1>
  <p class="muted">Última atualização: 19/07/2026</p>

  <p>
    Esta página explica como usuários conectados à VÉRTICE IA podem solicitar a exclusão dos dados associados à sua conta Meta/Facebook/Instagram.
  </p>

  <h2>1. Como solicitar exclusão</h2>
  <p>
    Para solicitar a exclusão dos dados armazenados pela VÉRTICE IA, envie um e-mail com o assunto
    <strong>“Exclusão de Dados - VÉRTICE IA”</strong> para:
  </p>

  <div class="box">
    <p><strong>E-mail:</strong> jujujulia.gomes757@gmail.com</p>
  </div>

  <p>No corpo do e-mail, informe:</p>
  <ul>
    <li>Nome completo ou nome da empresa.</li>
    <li>Instagram conectado.</li>
    <li>Página do Facebook vinculada, se souber.</li>
    <li>Solicitação clara de exclusão dos dados da VÉRTICE IA.</li>
  </ul>

  <h2>2. Prazo de atendimento</h2>
  <p>
    Após o recebimento da solicitação, a VÉRTICE IA analisará e removerá os dados associados à conta conectada
    em prazo razoável, salvo quando houver necessidade de retenção por obrigação legal, segurança ou prevenção de fraude.
  </p>

  <h2>3. Revogar acesso pela Meta</h2>
  <p>
    Além de solicitar exclusão à VÉRTICE IA, o usuário pode remover o acesso do aplicativo diretamente em sua conta Meta/Facebook:
  </p>
  <ul>
    <li>Acesse Facebook ou Instagram.</li>
    <li>Entre em Configurações.</li>
    <li>Procure por Aplicativos e Sites.</li>
    <li>Localize VÉRTICE IA.</li>
    <li>Remova ou revogue o acesso.</li>
  </ul>

  <h2>4. Dados removidos</h2>
  <p>
    A solicitação de exclusão pode incluir dados de conexão, identificadores da conta, relatórios salvos,
    histórico de análise e informações armazenadas para fins de diagnóstico comercial.
  </p>

  <h2>5. Contato</h2>
  <div class="box">
    <p><strong>Responsável:</strong> Júlia Gomes Alves</p>
    <p><strong>E-mail:</strong> jujujulia.gomes757@gmail.com</p>
  </div>
</div>
</body>
</html>
"""

@app.get("/politica-privacidade")
def vertice_politica_privacidade():
    from fastapi.responses import HTMLResponse
    return HTMLResponse(VERTICE_POLITICA_PRIVACIDADE_HTML)

@app.get("/exclusao-dados")
def vertice_exclusao_dados():
    from fastapi.responses import HTMLResponse
    return HTMLResponse(VERTICE_EXCLUSAO_DADOS_HTML)

# ==== FIM VERTICE PAGINAS LEGAIS META ====


# ============================================================
# VÉRTICE IA - TOKEN LONGO + PAGE ACCESS TOKEN
# ============================================================


def _meta_graph_get(path: str, token_or_params=None, params: dict | None = None):
    """
    Função compatível com os dois formatos usados na VÉRTICE:

    1) _meta_graph_get("me", user_token, {"fields": "id,name"})
    2) _meta_graph_get("me/accounts", {"fields": "...", "access_token": token})
    """
    import os, requests

    api_version = os.getenv("META_API_VERSION", "v25.0")
    url = f"https://graph.facebook.com/{api_version}/{path.lstrip('/')}"

    # Formato antigo: path, token, params
    if isinstance(token_or_params, str):
        final_params = params.copy() if isinstance(params, dict) else {}
        final_params["access_token"] = token_or_params

    # Formato novo: path, params
    elif isinstance(token_or_params, dict):
        final_params = token_or_params.copy()

    # Sem params
    else:
        final_params = params.copy() if isinstance(params, dict) else {}

    try:
        r = requests.get(url, params=final_params, timeout=30)
        data = r.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "message": "Erro ao chamar Graph API.",
            "path": path,
            "error": str(e)
        })

    if isinstance(data, dict) and data.get("error"):
        raise HTTPException(status_code=400, detail={
            "message": "Erro retornado pela Meta.",
            "path": path,
            "meta": data
        })

    return data


def _exchange_to_long_lived_token(short_token: str):
    import os, requests

    app_id = os.getenv("META_APP_ID")
    app_secret = os.getenv("META_APP_SECRET")

    if not app_id or not app_secret:
        raise HTTPException(status_code=500, detail="META_APP_ID ou META_APP_SECRET não configurado no .env.")

    url = "https://graph.facebook.com/oauth/access_token"

    params = {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": short_token
    }

    try:
        r = requests.get(url, params=params, timeout=30)
        data = r.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "message": "Erro ao trocar token curto por token longo.",
            "error": str(e)
        })

    if isinstance(data, dict) and data.get("error"):
        raise HTTPException(status_code=400, detail={
            "message": "A Meta recusou a troca do token.",
            "meta": data
        })

    token = data.get("access_token")
    if not token:
        raise HTTPException(status_code=400, detail={
            "message": "A Meta não retornou access_token longo.",
            "response": data
        })

    return {
        "access_token": token,
        "token_type": data.get("token_type"),
        "expires_in": data.get("expires_in")
    }


def _debug_token(token: str):
    import os, requests

    app_id = os.getenv("META_APP_ID")
    app_secret = os.getenv("META_APP_SECRET")

    if not app_id or not app_secret:
        raise HTTPException(status_code=500, detail="META_APP_ID ou META_APP_SECRET não configurado no .env.")

    app_token = f"{app_id}|{app_secret}"

    try:
        r = requests.get(
            "https://graph.facebook.com/debug_token",
            params={
                "input_token": token,
                "access_token": app_token
            },
            timeout=30
        )
        data = r.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "message": "Erro ao validar token.",
            "error": str(e)
        })

    return data


def _ensure_meta_token_columns():
    import sqlite3
    from pathlib import Path

    db_path = Path("backend") / "vertice_ia_limpa.db"
    if not db_path.exists():
        db_path = Path("vertice_ia_limpa.db")

    conn = sqlite3.connect(db_path)
    try:
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        names = {t[0] for t in tables}

        if "meta_connected_accounts" not in names:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS meta_connected_accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_name TEXT,
                    user_id TEXT,
                    user_name TEXT,
                    user_access_token TEXT,
                    page_id TEXT,
                    page_name TEXT,
                    page_access_token TEXT,
                    instagram_business_account_id TEXT,
                    instagram_username TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

        existing = conn.execute("PRAGMA table_info(meta_connected_accounts)").fetchall()
        cols = {c[1] for c in existing}

        add_cols = {
            "long_lived_user_token": "TEXT",
            "page_token_status": "TEXT",
            "token_expires_in": "INTEGER",
            "token_checked_at": "TEXT",
            "last_token_error": "TEXT"
        }

        for col, typ in add_cols.items():
            if col not in cols:
                conn.execute(f"ALTER TABLE meta_connected_accounts ADD COLUMN {col} {typ}")

        conn.commit()
    finally:
        conn.close()


@app.post("/api/meta-token/upgrade-connected")
def upgrade_connected_meta_tokens():
    """
    Converte tokens salvos em token longo de usuário,
    busca Page Access Token e salva no banco.
    """
    import sqlite3, datetime
    from pathlib import Path

    _ensure_meta_token_columns()

    db_path = Path("backend") / "vertice_ia_limpa.db"
    if not db_path.exists():
        db_path = Path("vertice_ia_limpa.db")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    resultados = []

    try:
        rows = conn.execute("""
            SELECT *
            FROM meta_connected_accounts
            ORDER BY id DESC
        """).fetchall()

        for row in rows:
            item = dict(row)
            account_id = item.get("id")
            short_or_old_token = item.get("user_access_token") or item.get("long_lived_user_token")

            if not short_or_old_token:
                resultados.append({
                    "id": account_id,
                    "status": "sem_token",
                    "message": "Conta sem user_access_token salvo."
                })
                continue

            try:
                long_data = _exchange_to_long_lived_token(short_or_old_token)
                long_token = long_data["access_token"]

                pages = _meta_graph_get("me/accounts", {
                    "fields": "id,name,access_token,instagram_business_account{id,username}",
                    "access_token": long_token
                })

                page_data = None
                ig_data = None

                for pg in pages.get("data", []):
                    if pg.get("instagram_business_account"):
                        page_data = pg
                        ig_data = pg.get("instagram_business_account")
                        break

                if not page_data and pages.get("data"):
                    page_data = pages["data"][0]
                    ig_data = page_data.get("instagram_business_account")

                if not page_data:
                    raise Exception("Nenhuma Página retornada em /me/accounts.")

                page_token = page_data.get("access_token")
                if not page_token:
                    raise Exception("A Página foi encontrada, mas sem page access token.")

                debug = _debug_token(page_token)
                is_valid = bool(debug.get("data", {}).get("is_valid"))

                now = datetime.datetime.now().isoformat(timespec="seconds")

                conn.execute("""
                    UPDATE meta_connected_accounts
                    SET
                        long_lived_user_token = ?,
                        page_id = COALESCE(?, page_id),
                        page_name = COALESCE(?, page_name),
                        page_access_token = ?,
                        instagram_business_account_id = COALESCE(?, instagram_business_account_id),
                        instagram_username = COALESCE(?, instagram_username),
                        page_token_status = ?,
                        token_expires_in = ?,
                        token_checked_at = ?,
                        last_token_error = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    long_token,
                    page_data.get("id"),
                    page_data.get("name"),
                    page_token,
                    ig_data.get("id") if isinstance(ig_data, dict) else None,
                    ig_data.get("username") if isinstance(ig_data, dict) else None,
                    "ativo" if is_valid else "verificar",
                    long_data.get("expires_in"),
                    now,
                    account_id
                ))

                resultados.append({
                    "id": account_id,
                    "client_name": item.get("client_name"),
                    "status": "atualizado",
                    "page": page_data.get("name"),
                    "page_id": page_data.get("id"),
                    "instagram": ig_data.get("username") if isinstance(ig_data, dict) else None,
                    "page_token_valid": is_valid,
                    "expires_in": long_data.get("expires_in")
                })

            except Exception as e:
                now = datetime.datetime.now().isoformat(timespec="seconds")
                conn.execute("""
                    UPDATE meta_connected_accounts
                    SET
                        page_token_status = ?,
                        token_checked_at = ?,
                        last_token_error = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    "precisa_reconectar",
                    now,
                    str(e),
                    account_id
                ))

                resultados.append({
                    "id": account_id,
                    "client_name": item.get("client_name"),
                    "status": "erro",
                    "message": str(e)
                })

        conn.commit()

    finally:
        conn.close()

    return {
        "ok": True,
        "message": "Processo de upgrade de token executado.",
        "resultados": resultados
    }


@app.get("/api/meta-token/status")
def meta_token_status():
    import sqlite3
    from pathlib import Path

    _ensure_meta_token_columns()

    db_path = Path("backend") / "vertice_ia_limpa.db"
    if not db_path.exists():
        db_path = Path("vertice_ia_limpa.db")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        rows = conn.execute("""
            SELECT
                id,
                client_name,
                page_id,
                page_name,
                instagram_business_account_id,
                instagram_username,
                page_token_status,
                token_expires_in,
                token_checked_at,
                last_token_error,
                created_at,
                updated_at,
                page_access_token
            FROM meta_connected_accounts
            ORDER BY id DESC
        """).fetchall()

        data = []
        for r in rows:
            item = dict(r)
            token = item.pop("page_access_token", None)
            item["has_page_access_token"] = bool(token)
            data.append(item)

        return {
            "ok": True,
            "accounts": data
        }

    finally:
        conn.close()


@app.post("/api/meta-token/check")
def check_connected_meta_tokens():
    import sqlite3, datetime
    from pathlib import Path

    _ensure_meta_token_columns()

    db_path = Path("backend") / "vertice_ia_limpa.db"
    if not db_path.exists():
        db_path = Path("vertice_ia_limpa.db")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    resultados = []

    try:
        rows = conn.execute("""
            SELECT id, client_name, page_access_token
            FROM meta_connected_accounts
            ORDER BY id DESC
        """).fetchall()

        for row in rows:
            token = row["page_access_token"]
            now = datetime.datetime.now().isoformat(timespec="seconds")

            if not token:
                conn.execute("""
                    UPDATE meta_connected_accounts
                    SET page_token_status = ?, token_checked_at = ?, last_token_error = ?
                    WHERE id = ?
                """, ("precisa_reconectar", now, "Sem Page Access Token salvo.", row["id"]))

                resultados.append({
                    "id": row["id"],
                    "client_name": row["client_name"],
                    "status": "precisa_reconectar",
                    "message": "Sem Page Access Token salvo."
                })
                continue

            debug = _debug_token(token)
            is_valid = bool(debug.get("data", {}).get("is_valid"))

            status = "ativo" if is_valid else "precisa_reconectar"
            error_msg = None if is_valid else str(debug)

            conn.execute("""
                UPDATE meta_connected_accounts
                SET page_token_status = ?, token_checked_at = ?, last_token_error = ?
                WHERE id = ?
            """, (status, now, error_msg, row["id"]))

            resultados.append({
                "id": row["id"],
                "client_name": row["client_name"],
                "status": status,
                "debug": debug.get("data", {})
            })

        conn.commit()

    finally:
        conn.close()

    return {
        "ok": True,
        "message": "Verificação de tokens concluída.",
        "resultados": resultados
    }

# ============================================================
# FIM - TOKEN LONGO + PAGE ACCESS TOKEN
# ============================================================



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

from routers.auth import router as auth_router
from routers.client_discovery import router as client_router
from routers.reports import router as reports_router
from routers.snapshots import router as snapshots_router
from routers.token import router as token_router

app.include_router(auth_router)
app.include_router(client_router)
app.include_router(reports_router)
app.include_router(snapshots_router)
app.include_router(token_router)
from fastapi.responses import HTMLResponse

@app.get("/termos", response_class=HTMLResponse)
def termos():
    return """
    <html>
    <head><title>Termos de Serviço - Vértice IA</title></head>
    <body>
        <h1>Termos de Serviço</h1>
        <p>Ao utilizar a plataforma Vértice IA, você concorda com estes termos de uso.</p>
        <p>A plataforma coleta e processa dados autorizados pelo usuário por meio das APIs da Meta exclusivamente para fornecer análises, relatórios e funcionalidades contratadas.</p>
        <p>Os dados não são comercializados e são tratados conforme a Política de Privacidade da plataforma.</p>
    </body>
    </html>
    """