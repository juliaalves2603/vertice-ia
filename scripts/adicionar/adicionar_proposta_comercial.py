from pathlib import Path
import re

p = Path("backend/static/index.html")
html = p.read_text(encoding="utf-8")

Path("backend/static/index_backup_antes_proposta_comercial.html").write_text(html, encoding="utf-8")

# 1. Adiciona aba no menu
if '["proposta","Proposta","$"]' not in html:
    if '["perfilCliente","Perfil Cliente","◐"],' in html:
        html = html.replace(
            '["perfilCliente","Perfil Cliente","◐"],',
            '["perfilCliente","Perfil Cliente","◐"],\n  ["proposta","Proposta","$"],'
        )
    else:
        html = html.replace(
            '["estrategico","Estratégico","◈"],',
            '["estrategico","Estratégico","◈"],\n  ["proposta","Proposta","$"],'
        )

# 2. Adiciona section
if '<section id="proposta" class="section"></section>' not in html:
    html = html.replace(
        '<section id="sobre" class="section"></section>',
        '<section id="proposta" class="section"></section>\n    <section id="sobre" class="section"></section>'
    )

# 3. Adiciona render
if 'if(state.tab==="proposta") renderProposta();' not in html:
    html = html.replace(
        'if(state.tab==="perfilCliente") renderPerfilCliente();',
        'if(state.tab==="perfilCliente") renderPerfilCliente();\n  if(state.tab==="proposta") renderProposta();'
    )

proposta_js = r'''
// ==============================
// PROPOSTA COMERCIAL AUTOMÁTICA
// ==============================

function propEscape(text){
  return String(text || "")
    .replaceAll("&","&amp;")
    .replaceAll("<","&lt;")
    .replaceAll(">","&gt;")
    .replaceAll('"',"&quot;")
    .replaceAll("'","&#039;");
}

function propGet(id){
  const el = document.getElementById(id);
  return el ? el.value.trim() : "";
}

function propSet(id, value){
  const el = document.getElementById(id);
  if(el) el.value = value || "";
}

function propostaDadosPerfil(){
  const getPerfil = (id) => {
    return localStorage.getItem("vertice_perfil_cliente_" + id) || "";
  };

  return {
    nome: getPerfil("pcNome"),
    instagram: getPerfil("pcInstagram"),
    segmento: getPerfil("pcSegmento"),
    objetivo: getPerfil("pcObjetivo"),
    bio: getPerfil("pcBio"),
    posts: getPerfil("pcPosts"),
    forcas: getPerfil("pcForcas"),
    ajustes: getPerfil("pcAjustes"),
    obs: getPerfil("pcObs")
  };
}

function saveProposta(){
  const ids = [
    "propCliente","propInstagram","propSegmento","propObjetivo",
    "propServico","propPlano","propValor","propCondicao",
    "propPrazo","propEntregas","propObs","propResponsavel"
  ];

  ids.forEach(id => {
    localStorage.setItem("vertice_proposta_" + id, propGet(id));
  });

  show("Proposta salva.", "success");
}

function loadProposta(){
  const perfil = propostaDadosPerfil();

  const defaults = {
    propCliente: perfil.nome,
    propInstagram: perfil.instagram,
    propSegmento: perfil.segmento,
    propObjetivo: perfil.objetivo || "Melhorar posicionamento digital, organizar o perfil e criar uma estratégia de conteúdo mais clara.",
    propServico: "Gestão estratégica de Instagram e posicionamento digital",
    propPlano: "Plano recomendado",
    propValor: "R$ 500,00",
    propCondicao: "Pagamento quinzenal ou mensal, conforme combinado.",
    propPrazo: "30 dias de acompanhamento inicial",
    propEntregas: "Análise do perfil, ajuste de bio, organização de destaques, direcionamento de conteúdo, calendário estratégico, acompanhamento de métricas e relatório de evolução.",
    propObs: "A proposta não promete clientes automaticamente. O objetivo é melhorar presença digital, clareza de posicionamento e tomada de decisão com base em dados.",
    propResponsavel: "VÉRTICE IA"
  };

  Object.keys(defaults).forEach(id => {
    const saved = localStorage.getItem("vertice_proposta_" + id);
    propSet(id, saved !== null ? saved : defaults[id]);
  });
}

function clearProposta(){
  const ids = [
    "propCliente","propInstagram","propSegmento","propObjetivo",
    "propServico","propPlano","propValor","propCondicao",
    "propPrazo","propEntregas","propObs","propResponsavel"
  ];

  ids.forEach(id => {
    localStorage.removeItem("vertice_proposta_" + id);
    propSet(id, "");
  });

  const box = document.getElementById("propostaResultado");
  if(box) box.innerHTML = `<div class="empty">Preencha os campos e clique em <strong>Gerar proposta</strong>.</div>`;

  show("Proposta limpa.", "success");
}

function getPropostaData(){
  return {
    cliente: propGet("propCliente"),
    instagram: propGet("propInstagram"),
    segmento: propGet("propSegmento"),
    objetivo: propGet("propObjetivo"),
    servico: propGet("propServico"),
    plano: propGet("propPlano"),
    valor: propGet("propValor"),
    condicao: propGet("propCondicao"),
    prazo: propGet("propPrazo"),
    entregas: propGet("propEntregas"),
    obs: propGet("propObs"),
    responsavel: propGet("propResponsavel")
  };
}

function gerarTextoDiagnosticoProposta(){
  const perfil = propostaDadosPerfil();

  const ajustes = perfil.ajustes || "O perfil precisa de ajustes de posicionamento, clareza de comunicação e organização estratégica.";
  const forcas = perfil.forcas || "O perfil possui potencial de desenvolvimento, mas precisa de direção estratégica para transformar presença em autoridade.";
  const posts = perfil.posts || "A leitura dos posts indica oportunidade de melhorar consistência, clareza dos conteúdos e chamadas para ação.";

  return {
    forcas,
    ajustes,
    posts
  };
}

function gerarProposta(){
  saveProposta();

  const d = getPropostaData();
  const diag = gerarTextoDiagnosticoProposta();

  const html = `
    <div class="card gold">
      <div class="between">
        <div>
          <div class="eyebrow">Proposta comercial</div>
          <h2>${propEscape(d.cliente || "Cliente não informado")}</h2>
          <p class="muted">${propEscape(d.instagram || "")} • ${propEscape(d.segmento || "Segmento não informado")}</p>
        </div>
        <span class="badge gold">${propEscape(d.valor || "Valor a definir")}</span>
      </div>

      <div class="reportBlock">
        <h3>Resumo da oportunidade</h3>
        <p>
          A proposta foi criada com base na análise do perfil, leitura dos conteúdos e necessidade de melhorar
          posicionamento digital, clareza da comunicação e consistência estratégica.
        </p>
      </div>
    </div>

    <br>

    <div class="grid two">
      <div class="card">
        <div class="eyebrow">Diagnóstico</div>
        <h2>O que foi identificado</h2>

        <div class="reportBlock">
          <h3>Pontos fortes</h3>
          <p>${propEscape(diag.forcas)}</p>
        </div>

        <div class="reportBlock">
          <h3>Pontos de ajuste</h3>
          <p>${propEscape(diag.ajustes)}</p>
        </div>

        <div class="reportBlock">
          <h3>Leitura dos conteúdos</h3>
          <p>${propEscape(diag.posts)}</p>
        </div>
      </div>

      <div class="card">
        <div class="eyebrow">Solução</div>
        <h2>Serviço recomendado</h2>

        <div class="reportBlock">
          <h3>${propEscape(d.servico || "Serviço não informado")}</h3>
          <p><strong>Plano:</strong> ${propEscape(d.plano || "A definir")}</p>
          <p><strong>Objetivo:</strong> ${propEscape(d.objetivo || "A definir")}</p>
          <p><strong>Prazo:</strong> ${propEscape(d.prazo || "A definir")}</p>
        </div>

        <div class="reportBlock">
          <h3>Entregas previstas</h3>
          <p>${propEscape(d.entregas || "Entregas não informadas.")}</p>
        </div>
      </div>
    </div>

    <br>

    <div class="card gold">
      <div class="eyebrow">Investimento</div>
      <h2>Condição comercial</h2>

      <div class="grid three">
        <div class="stat gold">
          <small>Valor</small>
          <strong>${propEscape(d.valor || "A definir")}</strong>
          <div class="hint">Investimento recomendado</div>
        </div>

        <div class="stat">
          <small>Prazo</small>
          <strong>${propEscape(d.prazo || "30 dias")}</strong>
          <div class="hint">Ciclo inicial</div>
        </div>

        <div class="stat">
          <small>Responsável</small>
          <strong>${propEscape(d.responsavel || "VÉRTICE IA")}</strong>
          <div class="hint">Análise e condução</div>
        </div>
      </div>

      <div class="reportBlock">
        <h3>Condição</h3>
        <p>${propEscape(d.condicao || "A definir")}</p>
      </div>

      <div class="reportBlock">
        <h3>Observação importante</h3>
        <p>${propEscape(d.obs || "A proposta não promete clientes automaticamente. O objetivo é melhorar posicionamento, clareza estratégica e consistência digital.")}</p>
      </div>
    </div>

    <br>

    <div class="card">
      <div class="eyebrow">Próximos passos</div>
      <h2>Como iniciar</h2>
      <div class="reportBlock">
        <ul>
          <li>Aprovação da proposta.</li>
          <li>Alinhamento de objetivo e prioridades do negócio.</li>
          <li>Organização do perfil: bio, destaques e leitura visual.</li>
          <li>Definição do calendário estratégico inicial.</li>
          <li>Acompanhamento dos dados e ajustes de conteúdo.</li>
        </ul>
      </div>
    </div>
  `;

  const box = document.getElementById("propostaResultado");
  if(box) box.innerHTML = html;

  show("Proposta gerada.", "success");
}

function propostaHtmlExport(){
  const d = getPropostaData();
  const diag = gerarTextoDiagnosticoProposta();
  const hoje = new Date().toLocaleDateString("pt-BR");

  return `<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Proposta Comercial — VÉRTICE IA</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#f8fafc;color:#111827;font-family:Arial,Helvetica,sans-serif;line-height:1.55}
.cover{background:linear-gradient(135deg,#020617,#0f172a);color:white;padding:54px 42px;border-bottom:8px solid #fbbf24}
.cover h1{font-size:38px;margin:0 0 12px;letter-spacing:-.03em}
.cover p{color:#cbd5e1}
main{padding:34px 42px;max-width:980px;margin:auto;background:white}
h2{font-size:22px;margin:30px 0 12px;border-bottom:2px solid #e5e7eb;padding-bottom:8px}
.box{border:1px solid #e5e7eb;border-left:5px solid #fbbf24;border-radius:14px;padding:18px;background:#fffaf0;margin:18px 0}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:18px 0}
.card{border:1px solid #e5e7eb;border-radius:14px;padding:16px;background:#f8fafc}
.card small{display:block;color:#475569;text-transform:uppercase;font-size:10px;font-weight:700;letter-spacing:.1em}
.card strong{display:block;font-size:22px;margin-top:6px}
li{margin-bottom:8px}
.footer{margin-top:36px;padding-top:18px;border-top:1px solid #e5e7eb;color:#475569;font-size:12px}
@media print{
  body{background:white}
  main{padding:24px 32px}
  .cover{padding:42px 32px}
  .box,.card{break-inside:avoid}
}
</style>
</head>
<body>
<section class="cover">
  <h1>Proposta Comercial — VÉRTICE IA</h1>
  <p>Estratégia de posicionamento digital baseada na análise do perfil e oportunidades identificadas.</p>
  <p><strong>Data:</strong> ${hoje}</p>
</section>

<main>
  <h2>Cliente</h2>
  <div class="box">
    <p><strong>Cliente:</strong> ${propEscape(d.cliente || "Não informado")}</p>
    <p><strong>Instagram:</strong> ${propEscape(d.instagram || "Não informado")}</p>
    <p><strong>Segmento:</strong> ${propEscape(d.segmento || "Não informado")}</p>
    <p><strong>Objetivo:</strong> ${propEscape(d.objetivo || "Não informado")}</p>
  </div>

  <h2>Diagnóstico</h2>
  <div class="box">
    <h3>Pontos fortes</h3>
    <p>${propEscape(diag.forcas)}</p>

    <h3>Pontos de ajuste</h3>
    <p>${propEscape(diag.ajustes)}</p>

    <h3>Leitura dos conteúdos</h3>
    <p>${propEscape(diag.posts)}</p>
  </div>

  <h2>Serviço recomendado</h2>
  <div class="box">
    <p><strong>Serviço:</strong> ${propEscape(d.servico || "Não informado")}</p>
    <p><strong>Plano:</strong> ${propEscape(d.plano || "Não informado")}</p>
    <p><strong>Prazo:</strong> ${propEscape(d.prazo || "Não informado")}</p>
    <p><strong>Entregas:</strong> ${propEscape(d.entregas || "Não informado")}</p>
  </div>

  <h2>Investimento</h2>
  <div class="grid">
    <div class="card"><small>Valor</small><strong>${propEscape(d.valor || "A definir")}</strong></div>
    <div class="card"><small>Prazo</small><strong>${propEscape(d.prazo || "30 dias")}</strong></div>
    <div class="card"><small>Responsável</small><strong>${propEscape(d.responsavel || "VÉRTICE IA")}</strong></div>
  </div>

  <div class="box">
    <p><strong>Condição:</strong> ${propEscape(d.condicao || "A definir")}</p>
    <p><strong>Observação:</strong> ${propEscape(d.obs || "A proposta não promete clientes automaticamente. O objetivo é melhorar posicionamento, clareza estratégica e consistência digital.")}</p>
  </div>

  <h2>Próximos passos</h2>
  <div class="box">
    <ul>
      <li>Aprovação da proposta.</li>
      <li>Alinhamento de objetivo e prioridades.</li>
      <li>Organização de bio, destaques e comunicação do perfil.</li>
      <li>Construção do calendário estratégico inicial.</li>
      <li>Acompanhamento de dados e ajustes de conteúdo.</li>
    </ul>
  </div>

  <div class="footer">
    Proposta gerada pela VÉRTICE IA. Esta entrega não promete clientes automaticamente; ela orienta posicionamento, estratégia e consistência digital.
  </div>
</main>
</body>
</html>`;
}

function baixarProposta(){
  const html = propostaHtmlExport();
  const blob = new Blob([html], {type:"text/html;charset=utf-8"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  const date = new Date().toISOString().slice(0,10);

  a.href = url;
  a.download = `proposta-comercial-vertice-ia-${date}.html`;
  document.body.appendChild(a);
  a.click();
  a.remove();

  URL.revokeObjectURL(url);
  show("Proposta baixada em HTML.", "success");
}

function salvarPropostaPdf(){
  const html = propostaHtmlExport();
  const w = window.open("", "_blank");
  w.document.open();
  w.document.write(html);
  w.document.close();
  w.focus();

  setTimeout(() => {
    w.print();
  }, 700);
}

async function copiarPropostaTexto(){
  const d = getPropostaData();
  const diag = gerarTextoDiagnosticoProposta();

  const text = `PROPOSTA COMERCIAL — VÉRTICE IA

Cliente: ${d.cliente}
Instagram: ${d.instagram}
Segmento: ${d.segmento}

Diagnóstico:
${diag.ajustes}

Serviço recomendado:
${d.servico}

Plano:
${d.plano}

Entregas:
${d.entregas}

Investimento:
${d.valor}

Condição:
${d.condicao}

Prazo:
${d.prazo}

Observação:
${d.obs}

Próximos passos:
Aprovação da proposta, alinhamento de objetivo, organização do perfil e início da estratégia de conteúdo.`;

  await navigator.clipboard.writeText(text);
  show("Texto da proposta copiado.", "success");
}

function renderProposta(){
  $("proposta").innerHTML = `
    <div class="card gold">
      <div class="between">
        <div>
          <div class="eyebrow">Comercial</div>
          <h2>Proposta Comercial Automática</h2>
          <p class="muted">
            Gere uma proposta com base na análise do perfil do cliente, transformando diagnóstico em oferta de serviço.
          </p>
        </div>
        <span class="badge gold">Venda estratégica</span>
      </div>
    </div>

    <br>

    <div class="card">
      <div class="eyebrow">Dados comerciais</div>
      <h2>Informações da proposta</h2>

      <div class="grid two">
        <div>
          <label class="muted">Cliente</label>
          <input id="propCliente" placeholder="Nome do cliente" style="width:100%;border-radius:14px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:12px;margin-top:6px;">
        </div>

        <div>
          <label class="muted">Instagram</label>
          <input id="propInstagram" placeholder="@cliente" style="width:100%;border-radius:14px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:12px;margin-top:6px;">
        </div>

        <div>
          <label class="muted">Segmento</label>
          <input id="propSegmento" placeholder="Ex: Pilates, estética, alimentação..." style="width:100%;border-radius:14px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:12px;margin-top:6px;">
        </div>

        <div>
          <label class="muted">Responsável</label>
          <input id="propResponsavel" placeholder="VÉRTICE IA / Júlia Alves" style="width:100%;border-radius:14px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:12px;margin-top:6px;">
        </div>
      </div>

      <br>

      <label class="muted">Objetivo da proposta</label>
      <input id="propObjetivo" placeholder="Objetivo da análise e do serviço" style="width:100%;border-radius:14px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:12px;margin-top:6px;">
    </div>

    <br>

    <div class="grid two">
      <div class="card">
        <div class="eyebrow">Serviço</div>
        <h2>Oferta recomendada</h2>

        <label class="muted">Serviço recomendado</label>
        <input id="propServico" placeholder="Ex: Gestão estratégica de Instagram" style="width:100%;border-radius:14px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:12px;margin-top:6px;">

        <br><br>

        <label class="muted">Plano</label>
        <input id="propPlano" placeholder="Ex: Plano Prata" style="width:100%;border-radius:14px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:12px;margin-top:6px;">

        <br><br>

        <label class="muted">Entregas</label>
        <textarea id="propEntregas" placeholder="Descreva as entregas do serviço..." style="width:100%;min-height:150px;border-radius:16px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:14px;font-family:inherit;resize:vertical;"></textarea>
      </div>

      <div class="card">
        <div class="eyebrow">Investimento</div>
        <h2>Condição comercial</h2>

        <label class="muted">Valor</label>
        <input id="propValor" placeholder="Ex: R$ 500,00" style="width:100%;border-radius:14px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:12px;margin-top:6px;">

        <br><br>

        <label class="muted">Prazo</label>
        <input id="propPrazo" placeholder="Ex: 30 dias" style="width:100%;border-radius:14px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:12px;margin-top:6px;">

        <br><br>

        <label class="muted">Condição de pagamento</label>
        <input id="propCondicao" placeholder="Ex: pagamento quinzenal ou mensal" style="width:100%;border-radius:14px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:12px;margin-top:6px;">

        <br><br>

        <label class="muted">Observações</label>
        <textarea id="propObs" placeholder="Observações importantes da proposta..." style="width:100%;min-height:110px;border-radius:16px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:14px;font-family:inherit;resize:vertical;"></textarea>
      </div>
    </div>

    <br>

    <div class="card">
      <div class="row">
        <button class="btn" onclick="gerarProposta()">Gerar proposta</button>
        <button class="btn secondary" onclick="saveProposta()">Salvar proposta</button>
        <button class="btn secondary" onclick="baixarProposta()">Baixar proposta</button>
        <button class="btn ghost" onclick="salvarPropostaPdf()">Salvar em PDF</button>
        <button class="btn ghost" onclick="copiarPropostaTexto()">Copiar texto</button>
        <button class="btn ghost" onclick="clearProposta()">Limpar</button>
      </div>
    </div>

    <br>

    <div id="propostaResultado">
      <div class="empty">Preencha os campos e clique em <strong>Gerar proposta</strong>.</div>
    </div>
  `;

  setTimeout(loadProposta, 50);
}
'''

if "function renderProposta()" not in html:
    html = html.replace("function renderSobre(){", proposta_js + "\nfunction renderSobre(){")

p.write_text(html, encoding="utf-8")

print("Proposta Comercial Automática adicionada com sucesso.")
print("Nova aba: Proposta")
