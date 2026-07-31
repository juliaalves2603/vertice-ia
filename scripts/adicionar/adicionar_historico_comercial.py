from pathlib import Path
import re

# =========================
# BACKEND
# =========================

app_path = Path("backend/app.py")
s = app_path.read_text(encoding="utf-8")

Path("backend/app_backup_antes_historico_comercial.py").write_text(s, encoding="utf-8")

# Garante imports necessários
if "import sqlite3" not in s:
    s = "import sqlite3\n" + s

if "import json" not in s:
    s = "import json\n" + s

if "from pathlib import Path" not in s:
    s = "from pathlib import Path\n" + s

# Garante HTTPException caso não exista
if "from fastapi import" in s:
    m = re.search(r"from fastapi import ([^\n]+)", s)
    if m and "HTTPException" not in m.group(1):
        imports = m.group(1).strip()
        s = s.replace(m.group(0), f"from fastapi import {imports}, HTTPException")
elif "HTTPException" not in s:
    s = "from fastapi import HTTPException\n" + s

backend_code = r'''
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
'''

if "HISTÓRICO COMERCIAL DE CLIENTES - VÉRTICE IA" not in s:
    m = re.search(r"\napp\.mount\(", s)
    if not m:
        raise RuntimeError("Não encontrei o ponto seguro antes do app.mount para inserir os endpoints.")
    s = s[:m.start()] + "\n" + backend_code + "\n" + s[m.start():]

app_path.write_text(s, encoding="utf-8")


# =========================
# FRONTEND
# =========================

index_path = Path("backend/static/index.html")
html = index_path.read_text(encoding="utf-8")

Path("backend/static/index_backup_antes_historico_comercial.html").write_text(html, encoding="utf-8")

# 1. Adiciona aba no menu
if '["historicoComercial","Histórico Comercial","▣"]' not in html:
    targets = [
        '["proposta","Proposta","$"],',
        '["perfilCliente","Perfil Cliente","◐"],',
        '["estrategico","Estratégico","◈"],'
    ]

    inserted = False

    for target in targets:
        if target in html:
            html = html.replace(
                target,
                target + '\n  ["historicoComercial","Histórico Comercial","▣"],'
            )
            inserted = True
            break

    if not inserted:
        raise RuntimeError("Não consegui localizar o menu de abas para inserir Histórico Comercial.")

# 2. Adiciona section
if '<section id="historicoComercial" class="section"></section>' not in html:
    html = html.replace(
        '<section id="sobre" class="section"></section>',
        '<section id="historicoComercial" class="section"></section>\n    <section id="sobre" class="section"></section>'
    )

# 3. Adiciona render da aba
if 'if(state.tab==="historicoComercial") renderHistoricoComercial();' not in html:
    if 'if(state.tab==="proposta") renderProposta();' in html:
        html = html.replace(
            'if(state.tab==="proposta") renderProposta();',
            'if(state.tab==="proposta") renderProposta();\n  if(state.tab==="historicoComercial") renderHistoricoComercial();'
        )
    else:
        html = html.replace(
            'if(state.tab==="sobre") renderSobre();',
            'if(state.tab==="historicoComercial") renderHistoricoComercial();\n  if(state.tab==="sobre") renderSobre();'
        )

frontend_code = r'''
// ==============================
// HISTÓRICO COMERCIAL DE CLIENTES
// ==============================

function histComEscape(text){
  return String(text || "")
    .replaceAll("&","&amp;")
    .replaceAll("<","&lt;")
    .replaceAll(">","&gt;")
    .replaceAll('"',"&quot;")
    .replaceAll("'","&#039;");
}

function histComGet(id){
  const el = document.getElementById(id);
  return el ? el.value.trim() : "";
}

function histComSet(id, value){
  const el = document.getElementById(id);
  if(el) el.value = value || "";
}

async function histComApi(url, options={}){
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
    const detail = data.detail || data.message || "Erro no histórico comercial.";
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }

  return data;
}

function histComProfilePayload(){
  const ids = [
    "pcNome","pcInstagram","pcSegmento","pcObjetivo",
    "pcBio","pcDestaques","pcPosts","pcForcas","pcAjustes","pcObs"
  ];

  const payload = {};

  ids.forEach(id => {
    payload[id] = localStorage.getItem("vertice_perfil_cliente_" + id) || "";
  });

  return payload;
}

function histComProposalPayload(){
  const ids = [
    "propCliente","propInstagram","propSegmento","propObjetivo",
    "propServico","propPlano","propValor","propCondicao",
    "propPrazo","propEntregas","propObs","propResponsavel"
  ];

  const payload = {};

  ids.forEach(id => {
    payload[id] = localStorage.getItem("vertice_proposta_" + id) || "";
  });

  return payload;
}

function histComFillFromCurrent(){
  const perfil = histComProfilePayload();
  const proposta = histComProposalPayload();

  histComSet("histClient", proposta.propCliente || perfil.pcNome || "");
  histComSet("histInstagram", proposta.propInstagram || perfil.pcInstagram || "");
  histComSet("histSegment", proposta.propSegmento || perfil.pcSegmento || "");
  histComSet("histValue", proposta.propValor || "");
  histComSet("histNotes", proposta.propObs || perfil.pcObs || "");

  show("Dados atuais da análise/proposta puxados para o histórico.", "success");
}

async function histComSave(){
  try{
    const payload = {
      client: histComGet("histClient"),
      instagram: histComGet("histInstagram"),
      segment: histComGet("histSegment"),
      proposal_value: histComGet("histValue"),
      proposal_status: histComGet("histStatus"),
      notes: histComGet("histNotes"),
      profile_payload: histComProfilePayload(),
      proposal_payload: histComProposalPayload()
    };

    const data = await histComApi("/api/commercial-history/save", {
      method: "POST",
      body: JSON.stringify(payload)
    });

    show("Cliente salvo no histórico comercial.", "success");

    await histComList();

    return data;

  }catch(e){
    show(e.message);
  }
}

async function histComList(){
  try{
    const q = histComGet("histSearch");
    const status = histComGet("histFilterStatus");

    const params = new URLSearchParams();

    if(q) params.set("q", q);
    if(status) params.set("status", status);

    const data = await histComApi(`/api/commercial-history?${params.toString()}`);

    const box = document.getElementById("histComList");

    if(!box) return;

    const items = data.items || [];

    if(!items.length){
      box.innerHTML = `<div class="empty">Nenhum cliente salvo ainda.</div>`;
      return;
    }

    box.innerHTML = `
      <div class="grid two">
        ${items.map(item => `
          <div class="card">
            <div class="between">
              <div>
                <div class="eyebrow">Cliente #${item.id}</div>
                <h2>${histComEscape(item.client || "Sem nome")}</h2>
                <p class="muted">${histComEscape(item.instagram || "")} • ${histComEscape(item.segment || "Sem segmento")}</p>
              </div>
              <span class="badge gold">${histComEscape(item.proposal_status || "Sem status")}</span>
            </div>

            <div class="grid two">
              <div class="stat gold">
                <small>Valor</small>
                <strong>${histComEscape(item.proposal_value || "A definir")}</strong>
                <div class="hint">Proposta</div>
              </div>

              <div class="stat">
                <small>Atualizado</small>
                <strong style="font-size:18px">${histComEscape((item.updated_at || "").replace("T"," ").slice(0,16))}</strong>
                <div class="hint">Histórico</div>
              </div>
            </div>

            <div class="reportBlock">
              <h3>Observações</h3>
              <p>${histComEscape(item.notes || "Sem observações.")}</p>
            </div>

            <div class="row">
              <button class="btn secondary" onclick="histComLoad(${item.id})">Carregar dados</button>
              <button class="btn ghost" onclick="histComDelete(${item.id})">Excluir</button>
            </div>
          </div>
        `).join("")}
      </div>
    `;

  }catch(e){
    show(e.message);
  }
}

async function histComLoad(id){
  try{
    const data = await histComApi(`/api/commercial-history/${id}`);
    const item = data.item || {};

    const profile = item.profile_payload || {};
    const proposal = item.proposal_payload || {};

    Object.keys(profile).forEach(key => {
      localStorage.setItem("vertice_perfil_cliente_" + key, profile[key] || "");
    });

    Object.keys(proposal).forEach(key => {
      localStorage.setItem("vertice_proposta_" + key, proposal[key] || "");
    });

    histComSet("histClient", item.client || "");
    histComSet("histInstagram", item.instagram || "");
    histComSet("histSegment", item.segment || "");
    histComSet("histValue", item.proposal_value || "");
    histComSet("histStatus", item.proposal_status || "");
    histComSet("histNotes", item.notes || "");

    show("Dados carregados. Abra Perfil Cliente ou Proposta para revisar.", "success");

  }catch(e){
    show(e.message);
  }
}

async function histComDelete(id){
  const ok = confirm("Deseja excluir este registro do histórico comercial?");

  if(!ok) return;

  try{
    await histComApi(`/api/commercial-history/${id}`, {
      method: "DELETE"
    });

    show("Registro excluído.", "success");

    await histComList();

  }catch(e){
    show(e.message);
  }
}

function renderHistoricoComercial(){
  $("historicoComercial").innerHTML = `
    <div class="card gold">
      <div class="between">
        <div>
          <div class="eyebrow">Base comercial</div>
          <h2>Histórico Comercial de Clientes</h2>
          <p class="muted">
            Salve análises, propostas, valores e status de negociação para acompanhar seus clientes dentro da VÉRTICE IA.
          </p>
        </div>
        <span class="badge gold">SQLite</span>
      </div>
    </div>

    <br>

    <div class="card">
      <div class="eyebrow">Novo registro</div>
      <h2>Salvar cliente no histórico</h2>

      <div class="grid two">
        <div>
          <label class="muted">Cliente</label>
          <input id="histClient" placeholder="Nome do cliente" style="width:100%;border-radius:14px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:12px;margin-top:6px;">
        </div>

        <div>
          <label class="muted">Instagram</label>
          <input id="histInstagram" placeholder="@cliente" style="width:100%;border-radius:14px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:12px;margin-top:6px;">
        </div>

        <div>
          <label class="muted">Segmento</label>
          <input id="histSegment" placeholder="Ex: Pilates, estética, alimentação..." style="width:100%;border-radius:14px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:12px;margin-top:6px;">
        </div>

        <div>
          <label class="muted">Valor da proposta</label>
          <input id="histValue" placeholder="Ex: R$ 500,00" style="width:100%;border-radius:14px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:12px;margin-top:6px;">
        </div>
      </div>

      <br>

      <div class="grid two">
        <div>
          <label class="muted">Status comercial</label>
          <select id="histStatus" style="width:100%;border-radius:14px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:12px;margin-top:6px;">
            <option>Análise feita</option>
            <option>Proposta enviada</option>
            <option>Em negociação</option>
            <option>Aprovado</option>
            <option>Recusado</option>
            <option>Retomar depois</option>
          </select>
        </div>

        <div>
          <label class="muted">Ação recomendada</label>
          <input placeholder="Ex: chamar no WhatsApp amanhã" style="width:100%;border-radius:14px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:12px;margin-top:6px;">
        </div>
      </div>

      <br>

      <label class="muted">Observações comerciais</label>
      <textarea id="histNotes" placeholder="Ex: cliente demonstrou interesse no plano prata, pediu retorno na próxima semana..." style="width:100%;min-height:120px;border-radius:16px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:14px;font-family:inherit;resize:vertical;margin-top:6px;"></textarea>

      <br><br>

      <div class="row">
        <button class="btn secondary" onclick="histComFillFromCurrent()">Puxar análise/proposta atual</button>
        <button class="btn" onclick="histComSave()">Salvar no histórico</button>
      </div>
    </div>

    <br>

    <div class="card">
      <div class="between">
        <div>
          <div class="eyebrow">Consulta</div>
          <h2>Clientes salvos</h2>
        </div>
        <button class="btn secondary" onclick="histComList()">Atualizar lista</button>
      </div>

      <div class="grid two">
        <div>
          <label class="muted">Buscar cliente</label>
          <input id="histSearch" placeholder="Nome, @ ou segmento" oninput="histComList()" style="width:100%;border-radius:14px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:12px;margin-top:6px;">
        </div>

        <div>
          <label class="muted">Filtrar por status</label>
          <select id="histFilterStatus" onchange="histComList()" style="width:100%;border-radius:14px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:12px;margin-top:6px;">
            <option value="">Todos</option>
            <option>Análise feita</option>
            <option>Proposta enviada</option>
            <option>Em negociação</option>
            <option>Aprovado</option>
            <option>Recusado</option>
            <option>Retomar depois</option>
          </select>
        </div>
      </div>

      <br>

      <div id="histComList">
        <div class="empty">Clique em <strong>Atualizar lista</strong> para ver os clientes salvos.</div>
      </div>
    </div>
  `;

  setTimeout(histComList, 80);
}
'''

if "function renderHistoricoComercial()" not in html:
    html = html.replace("function renderSobre(){", frontend_code + "\nfunction renderSobre(){")

index_path.write_text(html, encoding="utf-8")

print("Histórico Comercial de Clientes adicionado com sucesso.")
print("Nova aba: Histórico Comercial")
print("Novos endpoints:")
print("- POST /api/commercial-history/save")
print("- GET /api/commercial-history")
print("- GET /api/commercial-history/{id}")
print("- DELETE /api/commercial-history/{id}")
