from pathlib import Path

p = Path("backend/app.py")

if not p.exists():
    raise RuntimeError("backend/app.py não encontrado.")

s = p.read_text(encoding="utf-8")

Path("backend/app_backup_meta_comercial_isolado.py").write_text(s, encoding="utf-8")

marker = "# ==== VERTICE META COMERCIAL ISOLADO ===="

if marker in s:
    print("Meta Comercial isolado já está instalado.")
else:
    bloco = r'''

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
  if (Array.isArray(data.data)) return data.data;
  if (Array.isArray(data.connected_accounts)) return data.connected_accounts;
  if (data.account) return [data.account];
  return [];
}

function accountId(acc) {
  return acc.id || acc.account_id || acc.connected_account_id || acc.row_id || acc.db_id;
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
    alert("Não localizei o ID interno da conta conectada.");
    return;
  }

  document.getElementById("diagnosis").innerHTML = "Gerando relatório...";
  document.getElementById("raw").textContent = "Carregando dados...";

  try {
    const res = await fetch(`/api/meta-connected/accounts/${encodeURIComponent(id)}/insights`, {
      credentials: "include"
    });

    const data = await res.json();

    if (!res.ok) {
      document.getElementById("diagnosis").innerHTML = "Erro ao gerar insights.";
      document.getElementById("raw").textContent = JSON.stringify(data, null, 2);
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
'''
    s = s + bloco
    p.write_text(s, encoding="utf-8")
    print("Meta Comercial isolado instalado com sucesso.")

print("Conferindo app.py...")
