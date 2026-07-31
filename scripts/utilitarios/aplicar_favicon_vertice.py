from pathlib import Path

index = Path("backend/static/index.html")
app = Path("backend/app.py")
logo = Path("backend/static/assets/logo-vertice-ia.png")

if not index.exists():
    raise RuntimeError("backend/static/index.html não encontrado.")

if not logo.exists():
    raise RuntimeError("Logo não encontrado em backend/static/assets/logo-vertice-ia.png")

html = index.read_text(encoding="utf-8")
Path("backend/static/index_backup_favicon.html").write_text(html, encoding="utf-8")

favicon_tag = '<link rel="icon" type="image/png" href="/static/assets/logo-vertice-ia.png">'

# Remove favicon antigo se existir
html = html.replace('<link rel="icon" href="/favicon.ico">', '')
html = html.replace('<link rel="shortcut icon" href="/favicon.ico">', '')

# Insere favicon no head
if 'href="/static/assets/logo-vertice-ia.png"' not in html:
    html = html.replace("</head>", f"  {favicon_tag}\n</head>", 1)

index.write_text(html, encoding="utf-8")

print("Favicon aplicado com sucesso no painel.")
print("Logo usado:", logo)
