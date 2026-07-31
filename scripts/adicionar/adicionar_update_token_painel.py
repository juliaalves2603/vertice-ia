from pathlib import Path
import re

app_path = Path("backend/app.py")
s = app_path.read_text(encoding="utf-8")

Path("backend/app_backup_antes_update_token.py").write_text(s, encoding="utf-8")

# Garante Request
m = re.search(r"from fastapi import ([^\n]+)", s)
if m:
    nomes = [x.strip() for x in m.group(1).split(",")]
    if "Request" not in nomes:
        nomes.append("Request")
    s = s[:m.start()] + "from fastapi import " + ", ".join(nomes) + s[m.end():]

update_endpoint = r'''
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
'''

if "ATUALIZAR TOKEN META - VÉRTICE IA" not in s:
    m = re.search(r'\napp\.mount\(', s)
    if not m:
        raise RuntimeError("Não encontrei ponto seguro para inserir o endpoint.")
    s = s[:m.start()] + "\n" + update_endpoint + "\n" + s[m.start():]

app_path.write_text(s, encoding="utf-8")


index_path = Path("backend/static/index.html")
html = index_path.read_text(encoding="utf-8")

Path("backend/static/index_backup_antes_update_token.html").write_text(html, encoding="utf-8")

# Adiciona área visual para atualizar token dentro da aba Token Meta
old = '''
    <div id="tokenContent">
      <div class="empty">Clique em <strong>Testar conexão Meta</strong> para validar o token atual.</div>
    </div>
  `;
}
'''

new = '''
    <div id="tokenContent">
      <div class="empty">Clique em <strong>Testar conexão Meta</strong> para validar o token atual.</div>
    </div>

    <br>

    <div class="card">
      <div class="eyebrow">Atualização de token</div>
      <h2>Trocar Token Meta</h2>
      <p class="muted">Cole aqui o novo token gerado na Meta. Depois de salvar, reinicie a VÉRTICE IA.</p>

      <textarea id="newMetaToken" placeholder="Cole aqui o novo FACEBOOK_ACCESS_TOKEN" style="width:100%;min-height:120px;border-radius:16px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:14px;font-family:inherit;font-size:13px;resize:vertical;"></textarea>

      <br><br>

      <div class="row">
        <button class="btn" onclick="saveNewMetaToken()">Salvar novo token</button>
        <button class="btn secondary" onclick="clearNewMetaToken()">Limpar campo</button>
      </div>

      <div class="reportBlock">
        <h3>Depois de salvar</h3>
        <ul>
          <li>Pare a VÉRTICE IA com <strong>Ctrl + C</strong>.</li>
          <li>Rode novamente <strong>iniciar_vertice_ia.bat</strong>.</li>
          <li>Volte em <strong>Token Meta → Testar conexão Meta</strong>.</li>
        </ul>
      </div>
    </div>
  `;
}
'''

if old in html:
    html = html.replace(old, new)

token_save_js = r'''
async function saveNewMetaToken(){
  const field = $("newMetaToken");
  const token = field ? field.value.trim() : "";

  if(!token){
    show("Cole o novo token antes de salvar.");
    return;
  }

  if(token.length < 50){
    show("Esse token parece curto demais. Verifique se copiou completo.");
    return;
  }

  try{
    const data = await api("/api/update-token", {
      method:"POST",
      body:JSON.stringify({token})
    });

    field.value = "";
    show(data.message || "Token salvo. Reinicie a VÉRTICE IA.", "success");
  }catch(e){
    show(e.message);
  }
}

function clearNewMetaToken(){
  const field = $("newMetaToken");
  if(field) field.value = "";
  show("Campo limpo.", "success");
}
'''

if "function saveNewMetaToken()" not in html:
    html = html.replace("function renderMetricas(){", token_save_js + "\nfunction renderMetricas(){")

index_path.write_text(html, encoding="utf-8")

print("Atualização de token pelo painel aplicada com sucesso.")
print("Novo endpoint: /api/update-token")
print("Aba atualizada: Token Meta")
