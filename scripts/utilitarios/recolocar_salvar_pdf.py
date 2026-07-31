from pathlib import Path
import re

p = Path("backend/static/index.html")
html = p.read_text(encoding="utf-8")

Path("backend/static/index_backup_recolocar_pdf.html").write_text(html, encoding="utf-8")

# 1. Recoloca os botões na aba Estratégico
if 'onclick="printAdvancedReport()"' not in html:
    html = html.replace(
        '<button class="btn secondary" onclick="copyAdvanced()">Copiar análise</button>',
        '<button class="btn secondary" onclick="copyAdvanced()">Copiar análise</button>\n          <button class="btn secondary" onclick="downloadAdvancedHtml()">Baixar relatório</button>\n          <button class="btn ghost" onclick="printAdvancedReport()">Salvar em PDF</button>'
    )

# 2. Garante funções de exportação/PDF
pdf_functions = r'''
function escapeReportHtml(text){
  return String(text || "")
    .replaceAll("&","&amp;")
    .replaceAll("<","&lt;")
    .replaceAll(">","&gt;")
    .replaceAll('"',"&quot;")
    .replaceAll("'","&#039;");
}

function getClientReportDataSafe(){
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

function advancedClientHtmlSimple(){
  if(!state.advanced) return "";

  const r = state.advanced;
  const t = r.totais || {};
  const client = typeof getClientReportData === "function" ? getClientReportData() : getClientReportDataSafe();
  const hoje = new Date().toLocaleDateString("pt-BR");

  const trafego = (r.indicados_para_trafego || []).map(p => `
    <li><strong>${escapeReportHtml(p.caption)}</strong><br>
    Potencial: ${p.potential_score || 0}/100 • Alcance: ${fmt(p.reach)} • Salvos: ${fmt(p.saved)} • Compartilhamentos: ${fmt(p.shares)}<br>
    <em>${escapeReportHtml(p.decisao?.next_step || "")}</em></li>
  `).join("");

  const repetir = (r.repetir || []).map(p => `
    <li><strong>${escapeReportHtml(p.caption)}</strong><br>
    ${escapeReportHtml(p.decisao?.next_step || "")}</li>
  `).join("");

  const nao = (r.nao_impulsionar || []).map(p => `
    <li><strong>${escapeReportHtml(p.caption)}</strong><br>
    Motivo: ${escapeReportHtml(p.decisao?.reason || "")}</li>
  `).join("");

  const plano = (r.plano_7_dias || []).map(x => `<li>${escapeReportHtml(x)}</li>`).join("");

  return `<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Relatório Estratégico — VÉRTICE IA</title>
<style>
  *{box-sizing:border-box}
  body{margin:0;background:#f8fafc;color:#111827;font-family:Arial,Helvetica,sans-serif;line-height:1.55}
  .cover{background:linear-gradient(135deg,#020617,#0f172a);color:white;padding:52px 42px;border-bottom:8px solid #fbbf24}
  .cover h1{font-size:36px;margin:0 0 12px;letter-spacing:-.03em}
  .cover p{color:#cbd5e1}
  main{padding:34px 42px;max-width:980px;margin:auto;background:white}
  h2{font-size:22px;margin:30px 0 12px;border-bottom:2px solid #e5e7eb;padding-bottom:8px}
  .box{border:1px solid #e5e7eb;border-left:5px solid #fbbf24;border-radius:14px;padding:18px;background:#fffaf0;margin:18px 0}
  .grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0}
  .card{border:1px solid #e5e7eb;border-radius:14px;padding:16px;background:#f8fafc}
  .card small{display:block;color:#475569;text-transform:uppercase;font-size:10px;font-weight:700;letter-spacing:.1em}
  .card strong{display:block;font-size:24px;margin-top:6px}
  li{margin-bottom:10px}
  .footer{margin-top:36px;padding-top:18px;border-top:1px solid #e5e7eb;color:#475569;font-size:12px}
  @media print{
    body{background:white}
    main{padding:24px 32px}
    .cover{padding:42px 32px}
    .box,.card,li{break-inside:avoid}
  }
</style>
</head>
<body>
<section class="cover">
  <h1>Relatório Estratégico — VÉRTICE IA</h1>
  <p>Leitura baseada em dados reais do Instagram para orientar posicionamento, conteúdo e tráfego.</p>
  <p><strong>Data:</strong> ${hoje}</p>
</section>

<main>
  <h2>Dados da entrega</h2>
  <div class="box">
    <p><strong>Cliente:</strong> ${escapeReportHtml(client.nome || "Não informado")}</p>
    <p><strong>Instagram analisado:</strong> ${escapeReportHtml(client.instagram || "Não informado")}</p>
    <p><strong>Segmento:</strong> ${escapeReportHtml(client.segmento || "Não informado")}</p>
    <p><strong>Objetivo:</strong> ${escapeReportHtml(client.objetivo || "Não informado")}</p>
    <p><strong>Responsável:</strong> ${escapeReportHtml(client.responsavel || "VÉRTICE IA")}</p>
    <p><strong>Observações:</strong> ${escapeReportHtml(client.observacoes || "Sem observações adicionais.")}</p>
  </div>

  <h2>Resumo executivo</h2>
  <div class="box">
    <h3>${escapeReportHtml(r.resumo_executivo || "")}</h3>
    <p>${escapeReportHtml(r.diagnostico || "")}</p>
  </div>

  <div class="grid">
    <div class="card"><small>Posts</small><strong>${fmt(t.posts)}</strong></div>
    <div class="card"><small>Alcance</small><strong>${fmt(t.alcance)}</strong></div>
    <div class="card"><small>Salvos</small><strong>${fmt(t.salvos)}</strong></div>
    <div class="card"><small>Potencial</small><strong>${t.media_potencial || 0}</strong></div>
  </div>

  <h2>O que pode virar tráfego</h2>
  <ul>${trafego || "<li>Nenhum conteúdo pronto para tráfego neste momento.</li>"}</ul>

  <h2>O que repetir</h2>
  <ul>${repetir || "<li>Ainda não há conteúdo forte suficiente para repetir com segurança.</li>"}</ul>

  <h2>O que não impulsionar agora</h2>
  <ul>${nao || "<li>Nenhum bloqueio crítico identificado.</li>"}</ul>

  <h2>Plano de ação para 7 dias</h2>
  <ul>${plano}</ul>

  <h2>Texto comercial</h2>
  <p>${escapeReportHtml(r.texto_cliente || "")}</p>

  <div class="footer">
    Relatório gerado pela VÉRTICE IA. A análise orienta posicionamento, consistência e decisões baseadas em dados reais.
  </div>
</main>
</body>
</html>`;
}

function downloadAdvancedHtml(){
  if(!state.advanced){
    show("Gere o relatório estratégico primeiro.");
    return;
  }

  const html = advancedClientHtmlSimple();
  const blob = new Blob([html], {type:"text/html;charset=utf-8"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  const date = new Date().toISOString().slice(0,10);

  a.href = url;
  a.download = `relatorio-estrategico-vertice-ia-${date}.html`;
  document.body.appendChild(a);
  a.click();
  a.remove();

  URL.revokeObjectURL(url);
  show("Relatório baixado em HTML. Abra o arquivo e use Ctrl+P para salvar em PDF.", "success");
}

function printAdvancedReport(){
  if(!state.advanced){
    show("Gere o relatório estratégico primeiro.");
    return;
  }

  const reportWindow = window.open("", "_blank");
  reportWindow.document.open();
  reportWindow.document.write(advancedClientHtmlSimple());
  reportWindow.document.close();
  reportWindow.focus();

  setTimeout(() => {
    reportWindow.print();
  }, 700);
}
'''

if "function printAdvancedReport()" not in html:
    html = html.replace("function renderSobre(){", pdf_functions + "\nfunction renderSobre(){")

p.write_text(html, encoding="utf-8")

print("Botões de exportação recolocados com sucesso.")
print("Agora devem aparecer: Baixar relatório e Salvar em PDF.")
