
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


app.mount('/static', StaticFiles(directory=str(STATIC_DIR)), name='static')
