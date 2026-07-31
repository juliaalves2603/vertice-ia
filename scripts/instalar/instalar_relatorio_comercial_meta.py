from pathlib import Path

p = Path("backend/static/index.html")

if not p.exists():
    raise RuntimeError("backend/static/index.html não encontrado.")

s = p.read_text(encoding="utf-8")

backup = Path("backend/static/index_backup_relatorio_comercial_meta.html")
backup.write_text(s, encoding="utf-8")

block = r'''
<script>
(function(){
  if (window.__VERTICE_RELATORIO_META_COMERCIAL__) return;
  window.__VERTICE_RELATORIO_META_COMERCIAL__ = true;

  const originalFetch = window.fetch;

  window.fetch = async function(...args) {
    const response = await originalFetch.apply(this, args);

    try {
      const url = String(args[0] || "");

      if (url.includes("/api/meta-connected/accounts/") && url.includes("/insights")) {
        const clone = response.clone();
        const data = await clone.json();

        localStorage.setItem("vertice_meta_connected_last_report", JSON.stringify({
          saved_at: new Date().toISOString(),
          source_url: url,
          data: data
        }));
      }
    } catch (e) {
      console.warn("VÉRTICE: não foi possível salvar relatório Meta localmente.", e);
    }

    return response;
  };

  function getLastMetaReport() {
    try {
      return JSON.parse(localStorage.getItem("vertice_meta_connected_last_report") || "null");
    } catch (e) {
      return null;
    }
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function findValues(obj, keys) {
    const found = {};

    function walk(value) {
      if (!value || typeof value !== "object") return;

      if (Array.isArray(value)) {
        value.forEach(walk);
        return;
      }

      Object.entries(value).forEach(([k, v]) => {
        const keyLower = String(k).toLowerCase();

        keys.forEach(target => {
          if (keyLower.includes(target.toLowerCase()) && found[target] === undefined) {
            found[target] = v;
          }
        });

        walk(v);
      });
    }

    walk(obj);
    return found;
  }

  function commercialDiagnosis(data) {
    const json = JSON.stringify(data || {}).toLowerCase();

    const pontos = [];
    const ajustes = [];
    const recomendacoes = [];

    if (json.includes("reach") || json.includes("alcance")) {
      pontos.push("A conta possui dados de alcance disponíveis para análise de visibilidade.");
    } else {
      ajustes.push("A análise de alcance precisa ser acompanhada com consistência para medir crescimento real.");
    }

    if (json.includes("impression") || json.includes("impress")) {
      pontos.push("Existem dados de impressões, permitindo avaliar exposição do conteúdo.");
    }

    if (json.includes("engagement") || json.includes("comment") || json.includes("like")) {
      pontos.push("Há sinais de interação que podem ser usados para medir engajamento.");
    } else {
      ajustes.push("É necessário fortalecer conteúdos que estimulem interação, comentários e salvamentos.");
    }

    if (json.includes("follower")) {
      pontos.push("A conta possui dados relacionados à base de seguidores.");
    }

    recomendacoes.push("Transformar os dados em rotina de conteúdo com pilares claros.");
    recomendacoes.push("Acompanhar evolução mensal para identificar crescimento, queda ou estagnação.");
    recomendacoes.push("Criar calendário estratégico com foco em autoridade, relacionamento e conversão.");
    recomendacoes.push("Usar os insights reais para ajustar frequência, formato e temas dos posts.");

    return { pontos, ajustes, recomendacoes };
  }

  function buildMetaCommercialHtml() {
    const report = getLastMetaReport();

    if (!report) {
      alert("Gere primeiro o relatório com insights da conta conectada.");
      return null;
    }

    const data = report.data || {};
    const found = findValues(data, [
      "username",
      "name",
      "followers",
      "reach",
      "impressions",
      "profile_views",
      "accounts_engaged",
      "website_clicks"
    ]);

    const diag = commercialDiagnosis(data);

    const generatedAt = new Date(report.saved_at || Date.now()).toLocaleString("pt-BR");

    return `
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Relatório Comercial - VÉRTICE IA</title>
<style>
  body {
    font-family: Arial, sans-serif;
    color: #171717;
    margin: 0;
    background: #f4f4f4;
  }
  .page {
    max-width: 900px;
    margin: 30px auto;
    background: #fff;
    padding: 42px;
    border-radius: 18px;
  }
  .brand {
    font-size: 13px;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #777;
    margin-bottom: 8px;
  }
  h1 {
    font-size: 34px;
    margin: 0 0 10px;
  }
  h2 {
    margin-top: 34px;
    border-bottom: 1px solid #ddd;
    padding-bottom: 8px;
  }
  .subtitle {
    font-size: 16px;
    color: #555;
    margin-bottom: 28px;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px;
    margin: 22px 0;
  }
  .card {
    border: 1px solid #ddd;
    border-radius: 14px;
    padding: 18px;
    background: #fafafa;
  }
  .label {
    font-size: 12px;
    text-transform: uppercase;
    color: #777;
    margin-bottom: 6px;
  }
  .value {
    font-size: 20px;
    font-weight: bold;
  }
  li {
    margin-bottom: 10px;
    line-height: 1.5;
  }
  .footer {
    margin-top: 40px;
    font-size: 12px;
    color: #777;
    border-top: 1px solid #ddd;
    padding-top: 18px;
  }
  pre {
    white-space: pre-wrap;
    background: #111;
    color: #eee;
    padding: 18px;
    border-radius: 14px;
    overflow: auto;
    font-size: 12px;
  }
  @media print {
    body { background: #fff; }
    .page { margin: 0; border-radius: 0; }
  }
</style>
</head>
<body>
<div class="page">
  <div class="brand">VÉRTICE IA</div>
  <h1>Relatório Comercial da Conta Conectada</h1>
  <div class="subtitle">
    Diagnóstico gerado a partir dos dados reais autorizados via Meta/Facebook Login.
    <br>Gerado em: ${escapeHtml(generatedAt)}
  </div>

  <h2>Resumo da Conta</h2>
  <div class="grid">
    <div class="card">
      <div class="label">Usuário/Nome</div>
      <div class="value">${escapeHtml(found.username || found.name || "Conta conectada")}</div>
    </div>
    <div class="card">
      <div class="label">Seguidores</div>
      <div class="value">${escapeHtml(found.followers || "Não identificado")}</div>
    </div>
    <div class="card">
      <div class="label">Alcance</div>
      <div class="value">${escapeHtml(found.reach || "Disponível nos dados brutos")}</div>
    </div>
    <div class="card">
      <div class="label">Impressões</div>
      <div class="value">${escapeHtml(found.impressions || "Disponível nos dados brutos")}</div>
    </div>
  </div>

  <h2>Leitura Estratégica</h2>
  <p>
    A análise da conta conectada mostra que a marca já possui dados suficientes para sair do achismo
    e começar a tomar decisões com base em comportamento real do perfil.
  </p>

  <h2>Pontos identificados</h2>
  <ul>
    ${diag.pontos.map(item => `<li>${escapeHtml(item)}</li>`).join("") || "<li>Dados recebidos. A análise deve ser complementada com histórico mensal.</li>"}
  </ul>

  <h2>Ajustes necessários</h2>
  <ul>
    ${diag.ajustes.map(item => `<li>${escapeHtml(item)}</li>`).join("") || "<li>Manter acompanhamento dos dados para identificar oportunidades de crescimento.</li>"}
  </ul>

  <h2>Recomendações comerciais</h2>
  <ul>
    ${diag.recomendacoes.map(item => `<li>${escapeHtml(item)}</li>`).join("")}
  </ul>

  <h2>Conclusão</h2>
  <p>
    Com os dados reais conectados, a VÉRTICE IA consegue apoiar uma gestão mais estratégica do perfil,
    mostrando onde existe visibilidade, onde falta constância e quais pontos precisam ser ajustados para
    fortalecer posicionamento, autoridade e presença digital.
  </p>

  <h2>Dados técnicos capturados</h2>
  <pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre>

  <div class="footer">
    Relatório gerado pela VÉRTICE IA. Os dados dependem das permissões autorizadas pela conta conectada na Meta.
  </div>
</div>
</body>
</html>`;
  }

  window.verticeMetaPrintCommercial = function() {
    const html = buildMetaCommercialHtml();
    if (!html) return;

    const w = window.open("", "_blank");
    w.document.open();
    w.document.write(html);
    w.document.close();

    setTimeout(() => {
      w.focus();
      w.print();
    }, 600);
  };

  window.verticeMetaDownloadCommercial = function() {
    const html = buildMetaCommercialHtml();
    if (!html) return;

    const blob = new Blob([html], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = "relatorio-comercial-vertice-ia.html";
    document.body.appendChild(a);
    a.click();
    a.remove();

    URL.revokeObjectURL(url);
  };

  window.verticeMetaCopyCommercial = async function() {
    const report = getLastMetaReport();

    if (!report) {
      alert("Gere primeiro o relatório com insights da conta conectada.");
      return;
    }

    const diag = commercialDiagnosis(report.data || {});

    const texto = `
RELATÓRIO COMERCIAL - VÉRTICE IA

Diagnóstico:
A conta conectada possui dados reais autorizados via Meta, permitindo uma análise mais estratégica e menos genérica.

Pontos identificados:
${diag.pontos.map(x => "- " + x).join("\n")}

Ajustes necessários:
${diag.ajustes.map(x => "- " + x).join("\n")}

Recomendações:
${diag.recomendacoes.map(x => "- " + x).join("\n")}

Conclusão:
A marca precisa transformar os dados em rotina de conteúdo, acompanhamento mensal e decisões baseadas em métricas reais.
`.trim();

    await navigator.clipboard.writeText(texto);
    alert("Diagnóstico comercial copiado.");
  };

  window.verticeMetaSendToProposal = function() {
    const report = getLastMetaReport();

    if (!report) {
      alert("Gere primeiro o relatório com insights da conta conectada.");
      return;
    }

    const diag = commercialDiagnosis(report.data || {});

    const resumo = `
Diagnóstico feito com dados reais conectados via Meta.

Pontos identificados:
${diag.pontos.map(x => "- " + x).join("\n")}

Ajustes necessários:
${diag.ajustes.map(x => "- " + x).join("\n")}

Recomendações:
${diag.recomendacoes.map(x => "- " + x).join("\n")}
`.trim();

    localStorage.setItem("vertice_proposta_diagnostico_meta", resumo);
    alert("Resumo enviado para uso na proposta. Abra a aba Proposta e utilize o diagnóstico comercial.");
  };

  function injectButtons() {
    const text = document.body.innerText || "";

    if (!text.includes("Conectar Cliente Meta")) return;
    if (document.getElementById("vertice-meta-commercial-actions")) return;

    const candidates = Array.from(document.querySelectorAll("section, div, main"))
      .filter(el => (el.innerText || "").includes("Gerar relatório com insights"));

    const target = candidates[candidates.length - 1];

    if (!target) return;

    const box = document.createElement("div");
    box.id = "vertice-meta-commercial-actions";
    box.style.marginTop = "18px";
    box.style.padding = "18px";
    box.style.border = "1px solid rgba(0,0,0,.12)";
    box.style.borderRadius = "14px";
    box.style.background = "rgba(0,0,0,.035)";

    box.innerHTML = `
      <h3 style="margin:0 0 10px;">Relatório comercial da conta conectada</h3>
      <p style="margin:0 0 14px; opacity:.8;">
        Depois de gerar o relatório com insights, use estes botões para transformar os dados em material comercial.
      </p>
      <div style="display:flex; flex-wrap:wrap; gap:10px;">
        <button onclick="verticeMetaPrintCommercial()">Gerar PDF Comercial</button>
        <button onclick="verticeMetaDownloadCommercial()">Baixar HTML do Relatório</button>
        <button onclick="verticeMetaCopyCommercial()">Copiar diagnóstico comercial</button>
        <button onclick="verticeMetaSendToProposal()">Enviar resumo para Proposta</button>
      </div>
    `;

    target.appendChild(box);
  }

  setInterval(injectButtons, 1000);
})();
</script>
'''

if "__VERTICE_RELATORIO_META_COMERCIAL__" in s:
    print("Relatório comercial Meta já estava instalado.")
else:
    if "</body>" in s:
        s = s.replace("</body>", block + "\n</body>")
    else:
        s += "\n" + block

    p.write_text(s, encoding="utf-8")
    print("Relatório comercial Meta instalado com sucesso.")
