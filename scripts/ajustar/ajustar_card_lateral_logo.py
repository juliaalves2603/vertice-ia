from pathlib import Path
import re

p = Path("backend/static/index.html")

if not p.exists():
    raise RuntimeError("backend/static/index.html não encontrado.")

html = p.read_text(encoding="utf-8")
Path("backend/static/index_backup_logo_card_lateral.html").write_text(html, encoding="utf-8")

# CSS do logo no card lateral
css = """
<style id="vertice-sidebar-brand-logo-css">
  .vertice-sidebar-brand-logo {
    width: 96px;
    height: 96px;
    object-fit: contain;
    border-radius: 22px;
    background: rgba(255,255,255,.96);
    padding: 8px;
    box-shadow: 0 10px 24px rgba(0,0,0,.22);
    display: block;
    margin: 0 0 14px 0;
  }

  .vertice-sidebar-brand-text {
    font-size: 13px;
    color: #e5e7eb;
    line-height: 1.5;
    margin: 0 0 18px 0;
  }
</style>
"""

if "vertice-sidebar-brand-logo-css" not in html:
    html = html.replace("</head>", css + "\n</head>", 1)

# Troca o título grande VÉRTICE IA do card lateral pelo logo
patterns = [
    r'<h1>\s*VÉRTICE\s*<span>IA</span>\s*</h1>\s*<p>\s*Painel principal\s*•\s*dados reais,\s*posicionamento e decisão estratégica\.\s*</p>',
    r'<h2>\s*VÉRTICE\s*<span>IA</span>\s*</h2>\s*<p>\s*Painel principal\s*•\s*dados reais,\s*posicionamento e decisão estratégica\.\s*</p>',
    r'<div class="brandTitle">\s*VÉRTICE\s*<span>IA</span>\s*</div>\s*<p>\s*Painel principal\s*•\s*dados reais,\s*posicionamento e decisão estratégica\.\s*</p>',
]

novo = '''<img class="vertice-sidebar-brand-logo" src="/static/assets/logo-vertice-ia.png" alt="Logo">
        <p class="vertice-sidebar-brand-text">Painel principal • dados reais, posicionamento e decisão estratégica.</p>'''

alterou = False

for pattern in patterns:
    html2, count = re.subn(pattern, novo, html, count=1, flags=re.S)
    if count:
        html = html2
        alterou = True
        break

# Plano B: se o HTML estiver com tags diferentes, remove só o texto VÉRTICE/IA próximo do card
if not alterou:
    html2, count = re.subn(
        r'VÉRTICE\s*</?[^>]*>\s*IA',
        '<img class="vertice-sidebar-brand-logo" src="/static/assets/logo-vertice-ia.png" alt="Logo">',
        html,
        count=1,
        flags=re.S
    )
    html = html2
    alterou = count > 0

p.write_text(html, encoding="utf-8")

print("Ajuste aplicado.")
print("Card lateral alterado?", alterou)
print("Logo existe:", Path("backend/static/assets/logo-vertice-ia.png").exists())
