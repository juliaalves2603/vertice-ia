from pathlib import Path

app_py = Path("backend/app.py")
index_html = Path("backend/static/index.html")
logo_rel = "/static/assets/logo-vertice-ia.png"

if not app_py.exists():
    raise RuntimeError("backend/app.py não encontrado.")

if not index_html.exists():
    raise RuntimeError("backend/static/index.html não encontrado.")

# backups
Path("backend/app_backup_logo.py").write_text(app_py.read_text(encoding="utf-8"), encoding="utf-8")
Path("backend/static/index_backup_logo.html").write_text(index_html.read_text(encoding="utf-8"), encoding="utf-8")

# =========================
# 1) LOGIN
# =========================
s = app_py.read_text(encoding="utf-8")

if ".brand-logo-login" not in s:
    s = s.replace(
        ".logo {\n  width:68px;",
        """.brand-logo-login {
  display:flex;
  justify-content:center;
  margin-bottom:16px;
}
.brand-logo-login img {
  width:88px;
  height:88px;
  object-fit:contain;
  border-radius:18px;
  box-shadow: 0 10px 24px rgba(0,0,0,.18);
  background:#fff;
  padding:8px;
}
.logo {
  width:68px;"""
    )

old_login_block = '''<div class="logo">V</div>
    <div class="eyebrow">Acesso restrito</div>'''

new_login_block = f'''<div class="brand-logo-login">
      <img src="{logo_rel}" alt="Logo VÉRTICE IA">
    </div>
    <div class="eyebrow">Acesso restrito</div>'''

if old_login_block in s:
    s = s.replace(old_login_block, new_login_block, 1)

app_py.write_text(s, encoding="utf-8")

# =========================
# 2) PAINEL
# =========================
html = index_html.read_text(encoding="utf-8")

marker = "__VERTICE_LOGO_PATCH__"
if marker in html:
    pos = html.find(marker)
    script_start = html.rfind("<script", 0, pos)
    script_end = html.find("</script>", pos)
    if script_start != -1 and script_end != -1:
        html = html[:script_start] + html[script_end + len("</script>"):]

logo_patch = f"""
<script>
(function(){{
  if (window.__VERTICE_LOGO_PATCH__) return;
  window.__VERTICE_LOGO_PATCH__ = true;

  function injectLogo(){{
    if (document.getElementById("vertice-logo-fixed")) return;

    const wrap = document.createElement("div");
    wrap.id = "vertice-logo-fixed";
    wrap.innerHTML = `
      <div style="
        position:fixed;
        top:16px;
        left:16px;
        z-index:9999;
        background:rgba(17,24,39,.92);
        border:1px solid rgba(255,255,255,.08);
        border-radius:18px;
        padding:10px 14px;
        display:flex;
        align-items:center;
        gap:12px;
        box-shadow:0 12px 28px rgba(0,0,0,.20);
        backdrop-filter: blur(8px);
      ">
        <img src="{logo_rel}" alt="Logo VÉRTICE IA" style="
          width:42px;
          height:42px;
          object-fit:contain;
          border-radius:10px;
          background:#fff;
          padding:4px;
        ">
        <div style="display:flex;flex-direction:column;line-height:1.1;">
          <span style="font-size:11px;letter-spacing:2px;color:#f4b400;font-weight:800;">VÉRTICE IA</span>
          <span style="font-size:12px;color:#fff;">Inteligência estratégica</span>
        </div>
      </div>
    `;
    document.body.appendChild(wrap);
  }}

  if (document.readyState === "loading") {{
    document.addEventListener("DOMContentLoaded", injectLogo);
  }} else {{
    injectLogo();
  }}
}})();
</script>
"""

if "</body>" in html:
    html = html.replace("</body>", logo_patch + "\n</body>", 1)
else:
    html += logo_patch

index_html.write_text(html, encoding="utf-8")

print("Logo instalado com sucesso.")
print("Logo existe?", Path("backend/static/assets/logo-vertice-ia.png").exists())
