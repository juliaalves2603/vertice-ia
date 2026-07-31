from pathlib import Path
import re

app_py = Path("backend/app.py")
index_html = Path("backend/static/index.html")

if not app_py.exists():
    raise RuntimeError("backend/app.py não encontrado.")

if not index_html.exists():
    raise RuntimeError("backend/static/index.html não encontrado.")

# Backup antes do reparo
Path("backend/app_backup_reparo_logo_login.py").write_text(app_py.read_text(encoding="utf-8"), encoding="utf-8")
Path("backend/static/index_backup_reparo_logo_login.html").write_text(index_html.read_text(encoding="utf-8"), encoding="utf-8")

# =====================================================
# 1) REMOVER LOGO FIXO DO PAINEL
# =====================================================
html = index_html.read_text(encoding="utf-8")

marker = "__VERTICE_LOGO_PATCH__"

while marker in html:
    pos = html.find(marker)
    script_start = html.rfind("<script", 0, pos)
    script_end = html.find("</script>", pos)
    if script_start != -1 and script_end != -1:
        html = html[:script_start] + html[script_end + len("</script>"):]
    else:
        break

# Remove qualquer bloco visual fixo que tenha ficado
html = html.replace('id="vertice-logo-fixed"', 'id="vertice-logo-fixed-removido"')

index_html.write_text(html, encoding="utf-8")


# =====================================================
# 2) AJUSTAR LOGO SOMENTE NA CAIXA DE LOGIN
# =====================================================
s = app_py.read_text(encoding="utf-8")

# Remove estilos antigos grandes, se existirem
s = re.sub(
    r"\.brand-logo-login\s*\{.*?\}\s*\.brand-logo-login img\s*\{.*?\}",
    "",
    s,
    flags=re.S
)

# Adiciona estilo novo, menor e dentro da caixa
login_css = """
.brand-logo-login {
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  margin: 0 0 14px 0;
}
.brand-logo-login img {
  width: 72px;
  height: 72px;
  object-fit: contain;
  border-radius: 16px;
  background: rgba(255,255,255,.96);
  padding: 7px;
  box-shadow: 0 8px 18px rgba(0,0,0,.16);
}
"""

if ".brand-logo-login img" not in s:
    if "<style>" in s:
        s = s.replace("<style>", "<style>\n" + login_css, 1)
    else:
        s = login_css + s

# Troca o logo antigo V pelo logo em imagem, dentro do formulário
old_1 = '''<div class="logo">V</div>
    <div class="eyebrow">Acesso restrito</div>'''

new_1 = '''<div class="brand-logo-login">
      <img src="/static/assets/logo-vertice-ia.png" alt="Logo VÉRTICE IA">
    </div>
    <div class="eyebrow">Acesso restrito</div>'''

if old_1 in s:
    s = s.replace(old_1, new_1, 1)

# Se já tiver logo duplicado, mantém apenas o primeiro bloco
s = re.sub(
    r'(<div class="brand-logo-login">\s*<img src="/static/assets/logo-vertice-ia\.png" alt="Logo VÉRTICE IA">\s*</div>\s*){2,}',
    r'\1',
    s,
    flags=re.S
)

app_py.write_text(s, encoding="utf-8")

print("Reparo aplicado:")
print("- Logo fixo removido do painel")
print("- Logo mantido apenas dentro da caixa de login")
print("- Tamanho ajustado para 72x72")
print("- Logo existe:", Path("backend/static/assets/logo-vertice-ia.png").exists())
