from pathlib import Path
import re

app_path = Path("backend/app.py")
s = app_path.read_text(encoding="utf-8")

Path("backend/app_backup_antes_monitor_token.py").write_text(s, encoding="utf-8")

token_endpoint = r'''
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
'''

if "MONITOR DE TOKEN META - VÉRTICE IA" not in s:
    m = re.search(r'\napp\.mount\(', s)
    if not m:
        m = re.search(r'\n@app\.get\(\s*[\'"]/api/status', s)

    if not m:
        raise RuntimeError("Não encontrei ponto seguro para inserir o monitor de token.")

    s = s[:m.start()] + "\n" + token_endpoint + "\n" + s[m.start():]

app_path.write_text(s, encoding="utf-8")


index_path = Path("backend/static/index.html")
html = index_path.read_text(encoding="utf-8")

Path("backend/static/index_backup_antes_monitor_token.html").write_text(html, encoding="utf-8")

# Adiciona aba Token Meta no menu
if '["token","Token Meta","●"]' not in html:
    html = html.replace(
        '["config","Configuração","⚙"],',
        '["config","Configuração","⚙"],\n  ["token","Token Meta","●"],'
    )

# Adiciona section
if '<section id="token" class="section"></section>' not in html:
    html = html.replace(
        '<section id="metricas" class="section"></section>',
        '<section id="token" class="section"></section>\n    <section id="metricas" class="section"></section>'
    )

# Adiciona render condicional
if 'if(state.tab==="token") renderToken();' not in html:
    html = html.replace(
        'if(state.tab==="config") renderConfig();',
        'if(state.tab==="config") renderConfig();\n  if(state.tab==="token") renderToken();'
    )

token_front = r'''
function tokenBadge(status){
  if(status === "ativo" || status === "conectada" || status === "conectado") return "green";
  if(status === "invalido" || status === "erro" || status === "erro_conexao") return "red";
  return "gold";
}

function renderToken(){
  $("token").innerHTML = `
    <div class="card gold">
      <div class="between">
        <div>
          <div class="eyebrow">Monitor Meta</div>
          <h2>Controle de Token e Conexão</h2>
          <p class="muted">Verifique se o token está ativo, se a Página está acessível e se o Instagram profissional está conectado.</p>
        </div>
        <div class="row">
          <button class="btn" onclick="loadTokenMonitor()">Testar conexão Meta</button>
          <button class="btn secondary" onclick="copyTokenInstructions()">Copiar instrução</button>
        </div>
      </div>
    </div>
    <br>
    <div id="tokenContent">
      <div class="empty">Clique em <strong>Testar conexão Meta</strong> para validar o token atual.</div>
    </div>
  `;
}

async function loadTokenMonitor(){
  try{
    show("Testando token e conexão com a Meta...", "success");
    const data = await api("/api/token-monitor");
    $("tokenContent").innerHTML = tokenMonitorHtml(data);

    if(data.status === "sucesso"){
      show("Token Meta validado com sucesso.", "success");
    }else{
      show(data.diagnostico || "Token com erro.");
    }
  }catch(e){
    show(e.message);
    $("tokenContent").innerHTML = `<div class="alert">${safe(e.message)}</div>`;
  }
}

function tokenMonitorHtml(data){
  const ig = data.instagram_account || {};
  const page = data.facebook_page || {};
  const err = data.erro_meta || null;

  return `
    <div class="grid four">
      <div class="stat ${tokenBadge(data.token_status)}">
        <small>Status do token</small>
        <strong>${safe(data.token_status || "não testado")}</strong>
        <div class="hint">has_token: ${data.has_token ? "sim" : "não"}</div>
      </div>

      <div class="stat ${tokenBadge(data.page_status)}">
        <small>Página</small>
        <strong>${safe(data.page_status || "não testado")}</strong>
        <div class="hint">${safe(data.facebook_page_id || "Page ID ausente")}</div>
      </div>

      <div class="stat ${tokenBadge(data.instagram_status)}">
        <small>Instagram</small>
        <strong>${safe(data.instagram_status || "não testado")}</strong>
        <div class="hint">${ig.username ? "@" + safe(ig.username) : "Conta não localizada"}</div>
      </div>

      <div class="stat gold">
        <small>Meta API</small>
        <strong>${safe(data.meta_api_version || "")}</strong>
        <div class="hint">Último teste: ${safe(data.checked_at || "")}</div>
      </div>
    </div>

    <br>

    <div class="grid two">
      <div class="card">
        <div class="eyebrow">Diagnóstico</div>
        <h2>${data.status === "sucesso" ? "Conexão validada" : "Atenção necessária"}</h2>
        <p>${safe(data.diagnostico || "")}</p>

        <div class="reportBlock">
          <h3>Ação recomendada</h3>
          <p>${safe(data.acao_recomendada || "")}</p>
        </div>

        ${err ? `
          <div class="reportBlock">
            <h3>Erro retornado pela Meta</h3>
            <pre>${safe(JSON.stringify(err, null, 2))}</pre>
          </div>
        ` : ""}
      </div>

      <div class="card gold">
        <div class="eyebrow">Dados encontrados</div>
        <h2>Conta conectada</h2>

        <div class="item">
          <div class="between"><span>Page ID</span><strong>${safe(page.id || data.facebook_page_id || "")}</strong></div>
          <div class="between"><span>Página</span><strong>${safe(page.name || "Não localizada")}</strong></div>
          <div class="between"><span>Instagram ID</span><strong>${safe(ig.id || "Não localizado")}</strong></div>
          <div class="between"><span>Instagram</span><strong>${ig.username ? "@" + safe(ig.username) : "Não conectado"}</strong></div>
        </div>

        <div class="reportBlock">
          <h3>Quando trocar o token</h3>
          <ul>
            <li>Quando aparecer erro <strong>code 190</strong>.</li>
            <li>Quando a importação de posts parar.</li>
            <li>Quando a Meta remover permissões.</li>
            <li>Antes de uma apresentação importante.</li>
          </ul>
        </div>
      </div>
    </div>
  `;
}

async function copyTokenInstructions(){
  const text = `VÉRTICE IA — Atualização de Token Meta

1. Gere um novo token na Meta com permissões:
pages_show_list
pages_read_engagement
instagram_basic
instagram_manage_insights
business_management

2. Atualize o arquivo:
C:\\Users\\CECOMPI_NOTE\\Downloads\\VERTICE-IA-JULIA\\backend\\.env

3. Mantenha:
META_API_VERSION=v25.0
FACEBOOK_PAGE_ID=1124922614045641
FACEBOOK_ACCESS_TOKEN=COLE_AQUI_O_TOKEN_NOVO

4. Reinicie:
cd "C:\\Users\\CECOMPI_NOTE\\Downloads\\VERTICE-IA-JULIA"
.\\iniciar_vertice_ia.bat

5. No painel:
Token Meta → Testar conexão Meta`;

  await navigator.clipboard.writeText(text);
  show("Instrução de token copiada.", "success");
}
'''

if "function renderToken()" not in html:
    html = html.replace("function renderMetricas(){", token_front + "\nfunction renderMetricas(){")

index_path.write_text(html, encoding="utf-8")

print("Monitor de Token Meta aplicado com sucesso.")
print("Nova aba: Token Meta")
print("Novo endpoint: /api/token-monitor")
