from pathlib import Path
import re

p = Path("backend/static/index.html")

if not p.exists():
    raise RuntimeError("backend/static/index.html não encontrado.")

html = p.read_text(encoding="utf-8")
Path("backend/static/index_backup_menu_somente_logo.html").write_text(html, encoding="utf-8")

logo = "/static/assets/logo-vertice-ia.png"

# CSS do logo no menu lateral
css = """
<style id="vertice-menu-logo-css">
  .vertice-sidebar-logo-box {
    width: 100%;
    display: flex;
    justify-content: center;
    align-items: center;
    margin: 12px 0 22px 0;
  }

  .vertice-sidebar-logo-box img {
    width: 92px;
    height: 92px;
    object-fit: contain;
    border-radius: 22px;
    background: rgba(255,255,255,.96);
    padding: 8px;
    box-shadow: 0 10px 24px rgba(0,0,0,.20);
  }

  .vertice-hide-brand-text {
    display: none !important;
  }
</style>
"""

if "vertice-menu-logo-css" not in html:
    if "</head>" in html:
        html = html.replace("</head>", css + "\n</head>", 1)
    else:
        html = css + html

# Remove patch anterior, se existir
marker = "__VERTICE_MENU_LOGO_ONLY__"
while marker in html:
    pos = html.find(marker)
    script_start = html.rfind("<script", 0, pos)
    script_end = html.find("</script>", pos)
    if script_start != -1 and script_end != -1:
        html = html[:script_start] + html[script_end + len("</script>"):]
    else:
        break

script = f"""
<script>
(function(){{
  if (window.__VERTICE_MENU_LOGO_ONLY__) return;
  window.__VERTICE_MENU_LOGO_ONLY__ = true;

  function aplicarLogoMenu(){{
    const logoUrl = "{logo}";

    // procura textos VÉRTICE IA no painel
    const all = Array.from(document.querySelectorAll("body *"));

    all.forEach(function(el){{
      const txt = (el.innerText || "").trim();

      // remove textos soltos de marca no menu/topo
      if (
        txt === "VÉRTICE IA" ||
        txt === "VERTICE IA" ||
        txt === "Vértice IA"
      ) {{
        el.classList.add("vertice-hide-brand-text");

        // tenta colocar o logo no container pai uma única vez
        const parent = el.parentElement;
        if (parent && !parent.querySelector(".vertice-sidebar-logo-box")) {{
          const box = document.createElement("div");
          box.className = "vertice-sidebar-logo-box";
          box.innerHTML = '<img src="' + logoUrl + '" alt="Logo">';
          parent.insertBefore(box, parent.firstChild);
        }}
      }}
    }});

    // se não conseguiu inserir em cima do menu, força no primeiro container lateral provável
    if (!document.querySelector(".vertice-sidebar-logo-box")) {{
      const candidates = Array.from(document.querySelectorAll("aside, nav, .sidebar, .menu, [class*=sidebar], [class*=menu]"));
      const target = candidates[0];

      if (target) {{
        const box = document.createElement("div");
        box.className = "vertice-sidebar-logo-box";
        box.innerHTML = '<img src="' + logoUrl + '" alt="Logo">';
        target.insertBefore(box, target.firstChild);
      }}
    }}
  }}

  if (document.readyState === "loading") {{
    document.addEventListener("DOMContentLoaded", aplicarLogoMenu);
  }} else {{
    aplicarLogoMenu();
  }}

  setTimeout(aplicarLogoMenu, 800);
  setTimeout(aplicarLogoMenu, 1800);
}})();
</script>
"""

if "</body>" in html:
    html = html.replace("</body>", script + "\n</body>", 1)
else:
    html += script

p.write_text(html, encoding="utf-8")

print("Menu ajustado com sucesso.")
print("Escrita VÉRTICE IA será ocultada no menu/topo.")
print("Logo será exibido no lugar.")
print("Logo existe:", Path("backend/static/assets/logo-vertice-ia.png").exists())
