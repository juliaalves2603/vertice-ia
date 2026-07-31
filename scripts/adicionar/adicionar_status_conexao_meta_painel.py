from pathlib import Path

p = Path("backend/static/index.html")

if not p.exists():
    raise RuntimeError("backend/static/index.html não encontrado.")

html = p.read_text(encoding="utf-8")
Path("backend/static/index_backup_status_conexao_meta.html").write_text(html, encoding="utf-8")

# =====================================================
# CSS DO CARD DE STATUS META
# =====================================================
css = """
<style id="vertice-meta-status-css">
  .meta-status-card {
    margin: 18px 0;
    border: 1px solid rgba(148,163,184,.18);
    background: linear-gradient(135deg, rgba(15,23,42,.96), rgba(2,6,23,.96));
    border-radius: 22px;
    padding: 20px;
    box-shadow: 0 14px 34px rgba(0,0,0,.22);
  }

  .meta-status-head {
    display: flex;
    justify-content: space-between;
    gap: 16px;
    align-items: flex-start;
    margin-bottom: 16px;
  }

  .meta-status-title {
    margin: 0;
    font-size: 18px;
    color: #fff;
  }

  .meta-status-subtitle {
    margin: 6px 0 0 0;
    color: #94a3b8;
    font-size: 13px;
    line-height: 1.5;
  }

  .meta-status-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
    margin-top: 14px;
  }

  .meta-status-item {
    border: 1px solid rgba(148,163,184,.14);
    border-radius: 16px;
    padding: 14px;
    background: rgba(2,6,23,.62);
  }

  .meta-status-item small {
    display: block;
    color: #94a3b8;
    font-size: 11px;
    margin-bottom: 6px;
  }

  .meta-status-item strong {
    display: block;
    color: #fff;
    font-size: 14px;
    word-break: break-word;
  }

  .meta-status-pill {
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    padding: 8px 12px;
    font-size: 12px;
    font-weight: 800;
    border: 1px solid rgba(148,163,184,.18);
  }

  .meta-status-pill.ativo {
    background: rgba(34,197,94,.12);
    color: #86efac;
    border-color: rgba(34,197,94,.28);
  }

  .meta-status-pill.erro {
    background: rgba(239,68,68,.12);
    color: #fca5a5;
    border-color: rgba(239,68,68,.28);
  }

  .meta-status-pill.neutro {
    background: rgba(245,158,11,.12);
    color: #facc15;
    border-color: rgba(245,158,11,.28);
  }

  .meta-status-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 16px;
  }

  .meta-status-note {
    margin-top: 14px;
    color: #94a3b8;
    font-size: 12px;
    line-height: 1.5;
  }

  @media (max-width: 980px) {
    .meta-status-grid {
      grid-template-columns: 1fr;
    }

    .meta-status-head {
      flex-direction: column;
    }
  }
</style>
"""

if "vertice-meta-status-css" not in html:
    html = html.replace("</head>", css + "\n</head>", 1)

# =====================================================
# CARD VISUAL DENTRO DA ABA CONECTAR CLIENTE META
# =====================================================
card = """
      <div class="meta-status-card" id="metaStatusCard">
        <div class="meta-status-head">
          <div>
            <div class="eyebrow">Conexão Meta</div>
            <h3 class="meta-status-title">Status da conta conectada</h3>
            <p class="meta-status-subtitle">
              Verifique se a Página, o Instagram profissional e o token da Meta estão ativos.
            </p>
          </div>
          <span id="metaStatusPill" class="meta-status-pill neutro">Aguardando verificação</span>
        </div>

        <div id="metaStatusBox">
          <p class="muted">Clique em “Verificar conexão” para carregar o status atual.</p>
        </div>

        <div class="meta-status-actions">
          <button class="btn" onclick="carregarStatusMetaToken()">Verificar conexão</button>
          <button class="btn ghost" onclick="validarStatusMetaToken()">Validar token agora</button>
        </div>

        <p class="meta-status-note">
          O token não será exibido por segurança. O painel mostra apenas se existe token salvo e se ele está ativo.
        </p>
      </div>
"""

target = '''        <span class="badge gold">OAuth Meta</span>
      </div>'''

replacement = '''        <span class="badge gold">OAuth Meta</span>
      </div>
''' + card

if "metaStatusCard" not in html:
    if target not in html:
        raise RuntimeError("Ponto exato da aba Conectar Cliente Meta não encontrado.")
    html = html.replace(target, replacement, 1)

# =====================================================
# JS SEGURO PARA CHAMAR OS ENDPOINTS JÁ CRIADOS
# =====================================================
js = """
<script id="vertice-meta-status-js">
async function carregarStatusMetaToken(){
  const box = document.getElementById("metaStatusBox");
  const pill = document.getElementById("metaStatusPill");

  if (!box || !pill) return;

  box.innerHTML = '<p class="muted">Carregando status da conexão...</p>';
  pill.className = "meta-status-pill neutro";
  pill.textContent = "Verificando";

  try {
    const res = await fetch("/api/meta-token/status", {
      method: "GET",
      credentials: "same-origin"
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || data.message || "Erro ao consultar status.");
    }

    const accounts = data.accounts || [];

    if (!accounts.length) {
      pill.className = "meta-status-pill erro";
      pill.textContent = "Nenhuma conta";
      box.innerHTML = '<p class="muted">Nenhuma conta Meta conectada ainda. Use o login Facebook para conectar.</p>';
      return;
    }

    const acc = accounts[0];
    const ativo = acc.page_token_status === "ativo" && acc.has_page_access_token === true;

    pill.className = ativo ? "meta-status-pill ativo" : "meta-status-pill erro";
    pill.textContent = ativo ? "Ativo" : "Precisa reconectar";

    box.innerHTML = `
      <div class="meta-status-grid">
        <div class="meta-status-item">
          <small>Instagram</small>
          <strong>@${acc.instagram_username || "não localizado"}</strong>
        </div>
        <div class="meta-status-item">
          <small>Página</small>
          <strong>${acc.page_name || "não localizada"}</strong>
        </div>
        <div class="meta-status-item">
          <small>Status do token</small>
          <strong>${acc.page_token_status || "não verificado"}</strong>
        </div>
        <div class="meta-status-item">
          <small>Última verificação</small>
          <strong>${acc.token_checked_at || "sem registro"}</strong>
        </div>
      </div>

      <div class="meta-status-grid" style="margin-top:12px;">
        <div class="meta-status-item">
          <small>Page ID</small>
          <strong>${acc.page_id || "não localizado"}</strong>
        </div>
        <div class="meta-status-item">
          <small>Instagram Business ID</small>
          <strong>${acc.instagram_business_account_id || "não localizado"}</strong>
        </div>
        <div class="meta-status-item">
          <small>Token salvo</small>
          <strong>${acc.has_page_access_token ? "Sim" : "Não"}</strong>
        </div>
        <div class="meta-status-item">
          <small>Erro</small>
          <strong>${acc.last_token_error || "Nenhum"}</strong>
        </div>
      </div>
    `;

  } catch (e) {
    pill.className = "meta-status-pill erro";
    pill.textContent = "Erro";
    box.innerHTML = `<p class="muted">Erro ao carregar status: ${e.message}</p>`;
  }
}

async function validarStatusMetaToken(){
  const box = document.getElementById("metaStatusBox");
  const pill = document.getElementById("metaStatusPill");

  if (!box || !pill) return;

  box.innerHTML = '<p class="muted">Validando token diretamente na Meta...</p>';
  pill.className = "meta-status-pill neutro";
  pill.textContent = "Validando";

  try {
    const res = await fetch("/api/meta-token/check", {
      method: "POST",
      credentials: "same-origin"
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || data.message || "Erro ao validar token.");
    }

    await carregarStatusMetaToken();

  } catch (e) {
    pill.className = "meta-status-pill erro";
    pill.textContent = "Erro";
    box.innerHTML = `<p class="muted">Erro ao validar token: ${e.message}</p>`;
  }
}
</script>
"""

if "vertice-meta-status-js" not in html:
    html = html.replace("</body>", js + "\n</body>", 1)

p.write_text(html, encoding="utf-8")

print("Status da Conexão Meta inserido no painel com sucesso.")
print("Backup criado: backend/static/index_backup_status_conexao_meta.html")
