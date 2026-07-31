from pathlib import Path

p = Path("backend/app.py")

if not p.exists():
    raise RuntimeError("backend/app.py não encontrado.")

s = p.read_text(encoding="utf-8")

Path("backend/app_backup_meta_comercial_pro.py").write_text(s, encoding="utf-8")

marker = "# ==== VERTICE META COMERCIAL PRO ===="

if marker in s:
    print("Meta Comercial Pro já está instalado.")
else:
    bloco = r'''

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
'''
    s = s + bloco
    p.write_text(s, encoding="utf-8")
    print("Meta Comercial Pro instalado com sucesso.")

print("Conferência final concluída.")
