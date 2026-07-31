from pathlib import Path
import re

p = Path("backend/static/index.html")
html = p.read_text(encoding="utf-8")

Path("backend/static/index_backup_antes_perfil_cliente.html").write_text(html, encoding="utf-8")

# 1. Adiciona aba no menu
if '["perfilCliente","Perfil Cliente","◐"]' not in html:
    if '["estrategico","Estratégico","◈"],' in html:
        html = html.replace(
            '["estrategico","Estratégico","◈"],',
            '["estrategico","Estratégico","◈"],\n  ["perfilCliente","Perfil Cliente","◐"],'
        )
    else:
        html = html.replace(
            '["relatorio","Relatório","◎"],',
            '["relatorio","Relatório","◎"],\n  ["perfilCliente","Perfil Cliente","◐"],'
        )

# 2. Adiciona section
if '<section id="perfilCliente" class="section"></section>' not in html:
    html = html.replace(
        '<section id="sobre" class="section"></section>',
        '<section id="perfilCliente" class="section"></section>\n    <section id="sobre" class="section"></section>'
    )

# 3. Adiciona chamada render
if 'if(state.tab==="perfilCliente") renderPerfilCliente();' not in html:
    html = html.replace(
        'if(state.tab==="sobre") renderSobre();',
        'if(state.tab==="perfilCliente") renderPerfilCliente();\n  if(state.tab==="sobre") renderSobre();'
    )

perfil_cliente_js = r'''
// ==============================
// ANÁLISE MANUAL DO PERFIL DO CLIENTE
// ==============================

function pcEscape(text){
  return String(text || "")
    .replaceAll("&","&amp;")
    .replaceAll("<","&lt;")
    .replaceAll(">","&gt;")
    .replaceAll('"',"&quot;")
    .replaceAll("'","&#039;");
}

function pcGet(id){
  const el = document.getElementById(id);
  return el ? el.value.trim() : "";
}

function pcSet(id, value){
  const el = document.getElementById(id);
  if(el) el.value = value || "";
}

function savePerfilCliente(){
  const ids = [
    "pcNome","pcInstagram","pcSegmento","pcObjetivo",
    "pcBio","pcDestaques","pcPosts","pcForcas","pcAjustes","pcObs"
  ];

  ids.forEach(id => {
    localStorage.setItem("vertice_perfil_cliente_" + id, pcGet(id));
  });

  show("Análise do perfil do cliente salva.", "success");
}

function loadPerfilCliente(){
  const ids = [
    "pcNome","pcInstagram","pcSegmento","pcObjetivo",
    "pcBio","pcDestaques","pcPosts","pcForcas","pcAjustes","pcObs"
  ];

  ids.forEach(id => {
    pcSet(id, localStorage.getItem("vertice_perfil_cliente_" + id) || "");
  });

  renderPrintPreview();
}

function clearPerfilCliente(){
  const ids = [
    "pcNome","pcInstagram","pcSegmento","pcObjetivo",
    "pcBio","pcDestaques","pcPosts","pcForcas","pcAjustes","pcObs"
  ];

  ids.forEach(id => {
    localStorage.removeItem("vertice_perfil_cliente_" + id);
    pcSet(id, "");
  });

  state.perfilClientePrints = [];
  renderPrintPreview();
  const box = document.getElementById("perfilClienteResultado");
  if(box) box.innerHTML = `<div class="empty">Preencha os campos e clique em <strong>Gerar análise do perfil</strong>.</div>`;

  show("Campos limpos.", "success");
}

function getPerfilClienteData(){
  return {
    nome: pcGet("pcNome"),
    instagram: pcGet("pcInstagram"),
    segmento: pcGet("pcSegmento"),
    objetivo: pcGet("pcObjetivo"),
    bio: pcGet("pcBio"),
    destaques: pcGet("pcDestaques"),
    posts: pcGet("pcPosts"),
    forcas: pcGet("pcForcas"),
    ajustes: pcGet("pcAjustes"),
    obs: pcGet("pcObs")
  };
}

function analisarBioTexto(bio){
  const b = (bio || "").toLowerCase();

  const checks = [
    {
      nome: "Clareza de posicionamento",
      ok: b.length >= 80,
      sim: "A bio possui volume suficiente para comunicar posicionamento.",
      nao: "A bio parece curta. Precisa deixar mais claro o que a empresa faz, para quem faz e por que seguir."
    },
    {
      nome: "Chamada para ação",
      ok: /agende|chame|clique|link|whatsapp|direct|contato|orçamento|orcamento/.test(b),
      sim: "Existe chamada para ação.",
      nao: "Falta uma chamada direta para ação: agendar, chamar no WhatsApp, pedir orçamento ou acessar o link."
    },
    {
      nome: "Proposta de valor",
      ok: /especialista|resultado|transform|solução|solucao|experiência|experiencia|estratégia|estrategia|saúde|saude|beleza|pilates|consultoria|personalizado/.test(b),
      sim: "A bio sinaliza proposta de valor.",
      nao: "A proposta de valor ainda precisa ficar mais forte. O visitante precisa entender rapidamente o benefício."
    },
    {
      nome: "Localização ou área de atuação",
      ok: /sp|mg|rj|go|brasil|online|presencial|cidade|região|regiao|bairro/.test(b),
      sim: "Existe sinal de localização ou área de atuação.",
      nao: "Considere adicionar cidade, bairro, região ou atendimento online/presencial."
    }
  ];

  return checks;
}

function analisarDestaquesTexto(destaques){
  const d = (destaques || "").toLowerCase();

  const essenciais = [
    ["Serviços", /servi|proced|aulas|planos|cardápio|cardapio|produtos/],
    ["Depoimentos", /depo|feedback|cliente|resultado|antes|depois/],
    ["Localização", /local|endereço|endereco|onde|rota|mapa/],
    ["Agenda/Contato", /agenda|horário|horario|whatsapp|contato|marcar/],
    ["Dúvidas", /dúvida|duvida|faq|perguntas/],
    ["Bastidores/Autoridade", /bastidor|sobre|equipe|profissional|autoridade/]
  ];

  return essenciais.map(([nome, regex]) => ({
    nome,
    ok: regex.test(d),
    sim: `${nome} aparece nos destaques.`,
    nao: `Criar ou melhorar destaque de ${nome}.`
  }));
}

function gerarAnalisePerfilCliente(){
  const data = getPerfilClienteData();
  savePerfilCliente();

  const bioChecks = analisarBioTexto(data.bio);
  const destaqueChecks = analisarDestaquesTexto(data.destaques);

  const bioOk = bioChecks.filter(x => x.ok).length;
  const destaqueOk = destaqueChecks.filter(x => x.ok).length;

  let nivel = "Precisa de ajuste";
  let badge = "red";

  if(bioOk >= 3 && destaqueOk >= 4){
    nivel = "Perfil bem estruturado";
    badge = "green";
  }else if(bioOk >= 2 && destaqueOk >= 2){
    nivel = "Perfil com boa base";
    badge = "gold";
  }

  const html = `
    <div class="card gold">
      <div class="between">
        <div>
          <div class="eyebrow">Diagnóstico do perfil</div>
          <h2>${pcEscape(data.nome || "Cliente não informado")}</h2>
          <p class="muted">${pcEscape(data.instagram || "")} • ${pcEscape(data.segmento || "Segmento não informado")}</p>
        </div>
        <span class="badge ${badge}">${nivel}</span>
      </div>

      <div class="reportBlock">
        <h3>Resumo executivo</h3>
        <p>
          A análise do perfil mostra a estrutura atual da presença digital do cliente considerando bio,
          destaques, leitura visual do feed/posts e prints do painel profissional. O objetivo é identificar
          o que já comunica valor e o que precisa ser ajustado para melhorar posicionamento.
        </p>
      </div>
    </div>

    <br>

    <div class="grid two">
      <div class="card">
        <div class="eyebrow">Bio</div>
        <h2>Análise da bio</h2>
        ${bioChecks.map(x => `
          <div class="item">
            <span class="badge ${x.ok ? "green" : "red"}">${x.ok ? "OK" : "Ajustar"}</span>
            <h3 style="margin-top:10px">${pcEscape(x.nome)}</h3>
            <p>${pcEscape(x.ok ? x.sim : x.nao)}</p>
          </div>
        `).join("")}
      </div>

      <div class="card">
        <div class="eyebrow">Destaques</div>
        <h2>Análise dos destaques</h2>
        ${destaqueChecks.map(x => `
          <div class="item">
            <span class="badge ${x.ok ? "green" : "gold"}">${x.ok ? "Presente" : "Criar/Melhorar"}</span>
            <h3 style="margin-top:10px">${pcEscape(x.nome)}</h3>
            <p>${pcEscape(x.ok ? x.sim : x.nao)}</p>
          </div>
        `).join("")}
      </div>
    </div>

    <br>

    <div class="grid two">
      <div class="card">
        <div class="eyebrow">Feed e posts</div>
        <h2>Leitura dos conteúdos</h2>
        <div class="reportBlock">
          <h3>Observação registrada</h3>
          <p>${pcEscape(data.posts || "Nenhuma observação sobre posts foi preenchida.")}</p>
        </div>

        <div class="reportBlock">
          <h3>Pontos fortes</h3>
          <p>${pcEscape(data.forcas || "Nenhum ponto forte preenchido.")}</p>
        </div>
      </div>

      <div class="card">
        <div class="eyebrow">Ajustes</div>
        <h2>Recomendações estratégicas</h2>
        <div class="reportBlock">
          <h3>Pontos de ajuste</h3>
          <p>${pcEscape(data.ajustes || "Nenhum ponto de ajuste preenchido.")}</p>
        </div>

        <div class="reportBlock">
          <h3>Observações adicionais</h3>
          <p>${pcEscape(data.obs || "Sem observações adicionais.")}</p>
        </div>
      </div>
    </div>

    <br>

    <div class="card gold">
      <div class="eyebrow">Plano sugerido</div>
      <h2>Plano de ação inicial</h2>
      <div class="reportBlock">
        <ul>
          <li>Ajustar a bio para comunicar: o que faz, para quem faz, diferencial e chamada para ação.</li>
          <li>Organizar destaques essenciais: serviços, depoimentos, localização, dúvidas e contato.</li>
          <li>Revisar os 9 primeiros posts para garantir clareza visual e posicionamento.</li>
          <li>Transformar prints do painel profissional em diagnóstico de performance.</li>
          <li>Definir próximos conteúdos com base nos pontos fortes e nos ajustes identificados.</li>
        </ul>
      </div>
    </div>
  `;

  const box = document.getElementById("perfilClienteResultado");
  if(box) box.innerHTML = html;

  show("Análise do perfil gerada.", "success");
}

function handlePerfilPrints(input){
  const files = Array.from(input.files || []);
  if(!files.length) return;

  state.perfilClientePrints = state.perfilClientePrints || [];

  files.forEach(file => {
    const reader = new FileReader();

    reader.onload = function(e){
      state.perfilClientePrints.push({
        name: file.name,
        data: e.target.result
      });

      renderPrintPreview();
    };

    reader.readAsDataURL(file);
  });

  input.value = "";
}

function renderPrintPreview(){
  const box = document.getElementById("perfilPrintPreview");
  if(!box) return;

  const prints = state.perfilClientePrints || [];

  if(!prints.length){
    box.innerHTML = `<div class="empty">Nenhum print inserido ainda.</div>`;
    return;
  }

  box.innerHTML = `
    <div class="grid two">
      ${prints.map((img, i) => `
        <div class="item">
          <div class="between">
            <span class="badge gold">Print ${i + 1}</span>
            <button class="btn ghost" onclick="removePerfilPrint(${i})">Remover</button>
          </div>
          <br>
          <img src="${img.data}" style="width:100%;border-radius:16px;border:1px solid rgba(148,163,184,.18);">
          <p class="muted">${pcEscape(img.name)}</p>
        </div>
      `).join("")}
    </div>
  `;
}

function removePerfilPrint(index){
  state.perfilClientePrints = state.perfilClientePrints || [];
  state.perfilClientePrints.splice(index, 1);
  renderPrintPreview();
}

function clearPerfilPrints(){
  state.perfilClientePrints = [];
  renderPrintPreview();
  show("Prints removidos.", "success");
}

function perfilClienteReportHtml(){
  const data = getPerfilClienteData();
  const hoje = new Date().toLocaleDateString("pt-BR");
  const prints = state.perfilClientePrints || [];
  const bioChecks = analisarBioTexto(data.bio);
  const destaqueChecks = analisarDestaquesTexto(data.destaques);

  return `<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Análise de Perfil — VÉRTICE IA</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#f8fafc;color:#111827;font-family:Arial,Helvetica,sans-serif;line-height:1.55}
.cover{background:linear-gradient(135deg,#020617,#0f172a);color:white;padding:52px 42px;border-bottom:8px solid #fbbf24}
.cover h1{font-size:36px;margin:0 0 12px;letter-spacing:-.03em}
.cover p{color:#cbd5e1}
main{padding:34px 42px;max-width:980px;margin:auto;background:white}
h2{font-size:22px;margin:30px 0 12px;border-bottom:2px solid #e5e7eb;padding-bottom:8px}
.box{border:1px solid #e5e7eb;border-left:5px solid #fbbf24;border-radius:14px;padding:18px;background:#fffaf0;margin:18px 0}
.card{border:1px solid #e5e7eb;border-radius:14px;padding:16px;background:#f8fafc;margin:12px 0}
.badge{display:inline-block;border-radius:999px;padding:5px 9px;font-size:11px;font-weight:700;background:#fef3c7;color:#92400e}
.badge.green{background:#dcfce7;color:#166534}
.badge.red{background:#ffe4e6;color:#9f1239}
img{max-width:100%;border-radius:14px;border:1px solid #e5e7eb;margin:12px 0}
li{margin-bottom:8px}
.footer{margin-top:36px;padding-top:18px;border-top:1px solid #e5e7eb;color:#475569;font-size:12px}
@media print{
  body{background:white}
  main{padding:24px 32px}
  .cover{padding:42px 32px}
  .box,.card,img{break-inside:avoid}
}
</style>
</head>
<body>
<section class="cover">
  <h1>Análise de Perfil — VÉRTICE IA</h1>
  <p>Diagnóstico manual de bio, destaques, posts e prints do painel profissional.</p>
  <p><strong>Data:</strong> ${hoje}</p>
</section>

<main>
  <h2>Dados do cliente</h2>
  <div class="box">
    <p><strong>Cliente:</strong> ${pcEscape(data.nome || "Não informado")}</p>
    <p><strong>Instagram:</strong> ${pcEscape(data.instagram || "Não informado")}</p>
    <p><strong>Segmento:</strong> ${pcEscape(data.segmento || "Não informado")}</p>
    <p><strong>Objetivo:</strong> ${pcEscape(data.objetivo || "Não informado")}</p>
  </div>

  <h2>Bio atual</h2>
  <div class="box">
    <p>${pcEscape(data.bio || "Bio não preenchida.")}</p>
  </div>

  <h2>Análise da bio</h2>
  ${bioChecks.map(x => `
    <div class="card">
      <span class="badge ${x.ok ? "green" : "red"}">${x.ok ? "OK" : "Ajustar"}</span>
      <h3>${pcEscape(x.nome)}</h3>
      <p>${pcEscape(x.ok ? x.sim : x.nao)}</p>
    </div>
  `).join("")}

  <h2>Destaques</h2>
  <div class="box">
    <p>${pcEscape(data.destaques || "Destaques não preenchidos.")}</p>
  </div>

  <h2>Análise dos destaques</h2>
  ${destaqueChecks.map(x => `
    <div class="card">
      <span class="badge ${x.ok ? "green" : ""}">${x.ok ? "Presente" : "Criar/Melhorar"}</span>
      <h3>${pcEscape(x.nome)}</h3>
      <p>${pcEscape(x.ok ? x.sim : x.nao)}</p>
    </div>
  `).join("")}

  <h2>Feed e posts</h2>
  <div class="box"><p>${pcEscape(data.posts || "Nenhuma observação preenchida.")}</p></div>

  <h2>Pontos fortes</h2>
  <div class="box"><p>${pcEscape(data.forcas || "Nenhum ponto forte preenchido.")}</p></div>

  <h2>Pontos de ajuste</h2>
  <div class="box"><p>${pcEscape(data.ajustes || "Nenhum ponto de ajuste preenchido.")}</p></div>

  <h2>Observações estratégicas</h2>
  <div class="box"><p>${pcEscape(data.obs || "Sem observações adicionais.")}</p></div>

  <h2>Prints do painel profissional</h2>
  ${prints.length ? prints.map((img, i) => `
    <div class="card">
      <h3>Print ${i + 1}</h3>
      <img src="${img.data}">
    </div>
  `).join("") : `<div class="box"><p>Nenhum print foi inserido.</p></div>`}

  <h2>Plano de ação inicial</h2>
  <div class="box">
    <ul>
      <li>Ajustar a bio com posicionamento, diferencial e CTA claro.</li>
      <li>Organizar destaques essenciais para facilitar decisão do visitante.</li>
      <li>Revisar feed e posts para fortalecer autoridade e clareza visual.</li>
      <li>Usar os prints do painel profissional para complementar a análise de performance.</li>
      <li>Definir próximos conteúdos com base nos pontos fortes e ajustes encontrados.</li>
    </ul>
  </div>

  <div class="footer">
    Relatório gerado pela VÉRTICE IA. Esta análise é manual e estratégica, baseada nas informações e prints inseridos.
  </div>
</main>
</body>
</html>`;
}

function baixarPerfilClienteHtml(){
  const html = perfilClienteReportHtml();
  const blob = new Blob([html], {type:"text/html;charset=utf-8"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  const date = new Date().toISOString().slice(0,10);

  a.href = url;
  a.download = `analise-perfil-cliente-vertice-ia-${date}.html`;
  document.body.appendChild(a);
  a.click();
  a.remove();

  URL.revokeObjectURL(url);
  show("Análise baixada em HTML.", "success");
}

function imprimirPerfilClientePdf(){
  const html = perfilClienteReportHtml();
  const w = window.open("", "_blank");
  w.document.open();
  w.document.write(html);
  w.document.close();
  w.focus();

  setTimeout(() => {
    w.print();
  }, 700);
}

function renderPerfilCliente(){
  $("perfilCliente").innerHTML = `
    <div class="card gold">
      <div class="between">
        <div>
          <div class="eyebrow">Análise manual</div>
          <h2>Análise do Perfil do Cliente</h2>
          <p class="muted">
            Use esta área quando o cliente ainda não conectou a conta Meta. A análise será feita com base na bio,
            destaques, posts observados e prints do painel profissional.
          </p>
        </div>
        <span class="badge gold">Não depende da API do cliente</span>
      </div>
    </div>

    <br>

    <div class="card">
      <div class="eyebrow">Dados do perfil</div>
      <h2>Informações do cliente</h2>

      <div class="grid two">
        <div>
          <label class="muted">Nome do cliente</label>
          <input id="pcNome" placeholder="Ex: Espaço TM Pilates" style="width:100%;border-radius:14px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:12px;margin-top:6px;">
        </div>

        <div>
          <label class="muted">Instagram</label>
          <input id="pcInstagram" placeholder="Ex: @espacotmpilates" style="width:100%;border-radius:14px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:12px;margin-top:6px;">
        </div>

        <div>
          <label class="muted">Segmento</label>
          <input id="pcSegmento" placeholder="Ex: Pilates, estética, alimentação..." style="width:100%;border-radius:14px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:12px;margin-top:6px;">
        </div>

        <div>
          <label class="muted">Objetivo da análise</label>
          <input id="pcObjetivo" placeholder="Ex: melhorar posicionamento e identificar ajustes do perfil" style="width:100%;border-radius:14px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:12px;margin-top:6px;">
        </div>
      </div>
    </div>

    <br>

    <div class="grid two">
      <div class="card">
        <div class="eyebrow">Bio</div>
        <h2>Bio atual</h2>
        <textarea id="pcBio" placeholder="Cole aqui a bio atual do cliente..." style="width:100%;min-height:150px;border-radius:16px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:14px;font-family:inherit;resize:vertical;"></textarea>
      </div>

      <div class="card">
        <div class="eyebrow">Destaques</div>
        <h2>Destaques atuais</h2>
        <textarea id="pcDestaques" placeholder="Liste os destaques atuais. Ex: Sobre, Serviços, Depoimentos, Localização..." style="width:100%;min-height:150px;border-radius:16px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:14px;font-family:inherit;resize:vertical;"></textarea>
      </div>
    </div>

    <br>

    <div class="grid two">
      <div class="card">
        <div class="eyebrow">Feed e posts</div>
        <h2>Leitura dos posts</h2>
        <textarea id="pcPosts" placeholder="Descreva como está o feed: frequência, tipos de post, clareza visual, conteúdo de autoridade, ofertas..." style="width:100%;min-height:150px;border-radius:16px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:14px;font-family:inherit;resize:vertical;"></textarea>
      </div>

      <div class="card">
        <div class="eyebrow">Diagnóstico</div>
        <h2>Pontos fortes</h2>
        <textarea id="pcForcas" placeholder="Ex: boa identidade visual, autoridade, frequência, provas sociais..." style="width:100%;min-height:150px;border-radius:16px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:14px;font-family:inherit;resize:vertical;"></textarea>
      </div>
    </div>

    <br>

    <div class="grid two">
      <div class="card">
        <div class="eyebrow">Ajustes</div>
        <h2>Pontos de ajuste</h2>
        <textarea id="pcAjustes" placeholder="Ex: bio sem CTA, destaques desorganizados, posts sem direção estratégica..." style="width:100%;min-height:150px;border-radius:16px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:14px;font-family:inherit;resize:vertical;"></textarea>
      </div>

      <div class="card">
        <div class="eyebrow">Observações</div>
        <h2>Observações estratégicas</h2>
        <textarea id="pcObs" placeholder="Anotações livres para complementar a análise..." style="width:100%;min-height:150px;border-radius:16px;border:1px solid rgba(148,163,184,.18);background:#020617;color:white;padding:14px;font-family:inherit;resize:vertical;"></textarea>
      </div>
    </div>

    <br>

    <div class="card gold">
      <div class="eyebrow">Painel profissional</div>
      <h2>Inserir prints do painel profissional</h2>
      <p class="muted">Adicione prints de alcance, interações, seguidores, conteúdos, insights ou visão geral do Instagram profissional.</p>

      <input type="file" accept="image/*" multiple onchange="handlePerfilPrints(this)" style="width:100%;border-radius:14px;border:1px dashed rgba(251,191,36,.35);background:#020617;color:white;padding:16px;">

      <br><br>

      <div class="row">
        <button class="btn secondary" onclick="clearPerfilPrints()">Remover prints</button>
      </div>

      <br>

      <div id="perfilPrintPreview"></div>
    </div>

    <br>

    <div class="card">
      <div class="row">
        <button class="btn" onclick="gerarAnalisePerfilCliente()">Gerar análise do perfil</button>
        <button class="btn secondary" onclick="savePerfilCliente()">Salvar preenchimento</button>
        <button class="btn secondary" onclick="baixarPerfilClienteHtml()">Baixar análise</button>
        <button class="btn ghost" onclick="imprimirPerfilClientePdf()">Salvar em PDF</button>
        <button class="btn ghost" onclick="clearPerfilCliente()">Limpar tudo</button>
      </div>
    </div>

    <br>

    <div id="perfilClienteResultado">
      <div class="empty">Preencha os campos e clique em <strong>Gerar análise do perfil</strong>.</div>
    </div>
  `;

  setTimeout(loadPerfilCliente, 50);
}
'''

if "function renderPerfilCliente()" not in html:
    html = html.replace("function renderSobre(){", perfil_cliente_js + "\nfunction renderSobre(){")

p.write_text(html, encoding="utf-8")

print("Aba Perfil Cliente adicionada com sucesso.")
print("Agora a VÉRTICE IA terá análise manual de bio, destaques, posts e prints.")
