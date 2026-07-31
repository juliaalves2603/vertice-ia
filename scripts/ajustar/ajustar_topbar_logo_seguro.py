from pathlib import Path

p = Path("backend/static/index.html")

if not p.exists():
    raise RuntimeError("backend/static/index.html não encontrado.")

html = p.read_text(encoding="utf-8")

# Backup antes da alteração
Path("backend/static/index_backup_logo_topbar_seguro.html").write_text(html, encoding="utf-8")

# CSS pequeno para logo no topo
css = """
<style id="vertice-logo-topbar-css">
  .vertice-topbar-logo {
    width: 76px;
    height: 76px;
    object-fit: contain;
    border-radius: 18px;
    background: rgba(255,255,255,.96);
    padding: 7px;
    box-shadow: 0 10px 22px rgba(0,0,0,.18);
    display: block;
    margin-bottom: 10px;
  }
</style>
"""

if "vertice-logo-topbar-css" not in html:
    html = html.replace("</head>", css + "\n</head>", 1)

# Troca apenas o texto superior VÉRTICE IA pelo logo
html = html.replace(
    '<div class="eyebrow">VÉRTICE IA</div>\n        <h1 id="title">Visão Geral</h1>',
    '<img class="vertice-topbar-logo" src="/static/assets/logo-vertice-ia.png" alt="Logo">\n        <h1 id="title">Visão Geral</h1>',
    1
)

p.write_text(html, encoding="utf-8")

print("Ajuste aplicado com sucesso.")
print("Texto superior removido e logo inserido.")
print("Logo existe:", Path("backend/static/assets/logo-vertice-ia.png").exists())
