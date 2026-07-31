from pathlib import Path
import re

p = Path("backend/static/index.html")
html = p.read_text(encoding="utf-8")

Path("backend/static/index_backup_antes_dados_cliente.html").write_text(html, encoding="utf-8")

client_functions = r'''
function getClientReportData(){
  const get = (id, fallback="") => {
    const el = document.getElementById(id);
    if(el) return el.value.trim();
    return localStorage.getItem("vertice_report_" + id) || fallback;
  };

  return {
    nome: get("clientName"),
    instagram: get("clientInstagram"),
    segmento: get("clientSegment"),
    objetivo: get("clientGoal"),
    responsavel: get("clientResponsible", "VÉRTICE IA"),
    observacoes: get("clientNotes")
  };
}

function saveClientReportData(){
  const fields = ["clientName","clientInstagram","clientSegment","clientGoal","clientResponsible","clientNotes"];

  fields.forEach(id => {
    const el = document.getElementById(id);
    if(el) localStorage.setItem("vertice_report_" + id, el.value.trim());
  });

  show("Dados do cliente salvos para o relatório.", "success");
}

function fillClientReportData(){
  const fields = ["clientName","clientInstagram","clientSegment","clientGoal","clientResponsible","clientNotes"];

  fields.forEach(id => {
    const el = document.getElementById(id);
    const saved = localStorage.getItem("vertice_report_" + id);
    if(el && saved !== null) el.value = saved;
  });
}

function clearClientReportData(){
  const fields = ["clientName","clientInstagram","clientSegment","clientGoal","clientResponsible","clientNotes"];

  fields.forEach(id => {
    localStorage.removeItem("vertice_report_" + id);
    const el = document.getElementById(id);
    if(el) el.value = "";
  });

  show("Dados do cliente limpos.", "success");
}
'''

if "function getClientReportData()" not in html:
    html = html.replace("function escapeReportHtml(text){", client_functions + "\nfunction escapeReportHtml(text){")

client_card = r'''
    <div class="card">
      <div class="eyebrow">Dados do cliente</div>
      <h2>Personalização do relatório</h2>
      <p class="muted">Preencha antes de baixar ou salvar em PDF. Esses dados aparecerão no relatório exportado.</p>

      <div class="grid two">
        <div>
          <label class="muted">Nome do cliente</label>
          <input id="clientName" placeholder="Ex: Espaço TM Pilates" style="width:100%;border-radius:14px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:12px;margin-top:6px;">
        </div>

        <div>
          <label class="muted">Instagram analisado</label>
          <input id="clientInstagram" placeholder="Ex: @espacotmpilates" style="width:100%;border-radius:14px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:12px;margin-top:6px;">
        </div>

        <div>
          <label class="muted">Segmento</label>
          <input id="clientSegment" placeholder="Ex: Pilates, estética, alimentação..." style="width:100%;border-radius:14px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:12px;margin-top:6px;">
        </div>

        <div>
          <label class="muted">Responsável pela análise</label>
          <input id="clientResponsible" placeholder="Ex: Júlia Alves / VÉRTICE IA" style="width:100%;border-radius:14px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:12px;margin-top:6px;">
        </div>
      </div>

      <br>

      <label class="muted">Objetivo da análise</label>
      <input id="clientGoal" placeholder="Ex: entender conteúdos com maior potencial e melhorar posicionamento" style="width:100%;border-radius:14px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:12px;margin-top:6px;">

      <br><br>

      <label class="muted">Observações estratégicas</label>
      <textarea id="clientNotes" placeholder="Ex: foco em autoridade, aumento de alcance qualificado e conteúdos para captação" style="width:100%;min-height:100px;border-radius:14px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:12px;margin-top:6px;font-family:inherit;resize:vertical;"></textarea>

      <br><br>

      <div class="row">
        <button class="btn" onclick="saveClientReportData()">Salvar dados do cliente</button>
        <button class="btn secondary" onclick="clearClientReportData()">Limpar</button>
      </div>
    </div>

    <br>
'''

marker = '<div id="advancedContent">${state.advanced ? advancedHtml(state.advanced) : `<div class="empty">Clique em <strong>Gerar relatório estratégico</strong> para analisar os dados reais atuais.</div>`}</div>'

if "clientName" not in html:
    html = html.replace(marker, client_card + marker)

# Faz os dados salvos reaparecerem quando abrir a aba Estratégico
if "setTimeout(fillClientReportData" not in html:
    html = re.sub(
        r'(function renderEstrategico\(\)\{[\s\S]*?\n\s*`;\n)(\})',
        r'\1  setTimeout(fillClientReportData, 50);\n\2',
        html,
        count=1
    )

# Faz o relatório exportado ler os dados do cliente
if "const client = getClientReportData();" not in html:
    html = html.replace(
        'const hoje = new Date().toLocaleDateString("pt-BR");',
        'const hoje = new Date().toLocaleDateString("pt-BR");\n  const client = getClientReportData();'
    )

# CSS do relatório exportado
if ".client-box" not in html:
    html = html.replace(
        ".box{border:1px solid var(--line);border-left:5px solid var(--gold);border-radius:14px;padding:18px;background:#fffaf0;margin:18px 0}",
        ".box{border:1px solid var(--line);border-left:5px solid var(--gold);border-radius:14px;padding:18px;background:#fffaf0;margin:18px 0}\n  .client-box{margin-top:22px;border:1px solid rgba(251,191,36,.38);border-radius:16px;padding:16px;background:rgba(15,23,42,.72)}\n  .client-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;font-size:13px;color:#e2e8f0}\n  .client-grid strong{color:#fde68a}"
    )

# Dados na capa do relatório exportado
cover_marker = '  <p><strong>Data:</strong> ${hoje}</p>'
cover_insert = '''  <p><strong>Data:</strong> ${hoje}</p>
  <div class="client-box">
    <div class="client-grid">
      <div><strong>Cliente:</strong><br>${escapeReportHtml(client.nome || "Não informado")}</div>
      <div><strong>Instagram:</strong><br>${escapeReportHtml(client.instagram || "Não informado")}</div>
      <div><strong>Segmento:</strong><br>${escapeReportHtml(client.segmento || "Não informado")}</div>
      <div><strong>Responsável:</strong><br>${escapeReportHtml(client.responsavel || "VÉRTICE IA")}</div>
    </div>
  </div>'''

if cover_insert not in html:
    html = html.replace(cover_marker, cover_insert)

# Dados também no corpo do relatório
body_marker = "  <h2>Resumo executivo</h2>"
body_insert = '''  <h2>Dados da entrega</h2>
  <div class="box">
    <p><strong>Cliente:</strong> ${escapeReportHtml(client.nome || "Não informado")}</p>
    <p><strong>Instagram analisado:</strong> ${escapeReportHtml(client.instagram || "Não informado")}</p>
    <p><strong>Segmento:</strong> ${escapeReportHtml(client.segmento || "Não informado")}</p>
    <p><strong>Objetivo da análise:</strong> ${escapeReportHtml(client.objetivo || "Não informado")}</p>
    <p><strong>Responsável:</strong> ${escapeReportHtml(client.responsavel || "VÉRTICE IA")}</p>
    <p><strong>Observações estratégicas:</strong> ${escapeReportHtml(client.observacoes || "Sem observações adicionais.")}</p>
  </div>

  <h2>Resumo executivo</h2>'''

if body_insert not in html:
    html = html.replace(body_marker, body_insert)

p.write_text(html, encoding="utf-8")

print("Dados do cliente adicionados ao relatório com sucesso.")
print("Aba afetada: Estratégico")
print("Arquivo alterado: backend/static/index.html")
