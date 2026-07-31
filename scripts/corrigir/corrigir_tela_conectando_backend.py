from pathlib import Path

p = Path("backend/static/index.html")

if not p.exists():
    raise RuntimeError("backend/static/index.html não encontrado.")

s = p.read_text(encoding="utf-8")

Path("backend/static/index_backup_corrigir_tela_conectando.html").write_text(s, encoding="utf-8")

patch = r'''
<script>
(function(){
  if (window.__VERTICE_PUBLIC_API_FINAL_FIX__) return;
  window.__VERTICE_PUBLIC_API_FINAL_FIX__ = true;

  const ORIGIN = window.location.origin;
  const originalFetch = window.fetch.bind(window);

  function corrigirUrl(url) {
    if (!url) return url;

    url = String(url);

    url = url
      .replace(/^http:\/\/127\.0\.0\.1:8000(?=\/api\/)/, ORIGIN)
      .replace(/^http:\/\/127\.0\.0\.1:8001(?=\/api\/)/, ORIGIN)
      .replace(/^http:\/\/localhost:8000(?=\/api\/)/, ORIGIN)
      .replace(/^http:\/\/localhost:8001(?=\/api\/)/, ORIGIN)
      .replace(/^https:\/\/127\.0\.0\.1:8000(?=\/api\/)/, ORIGIN)
      .replace(/^https:\/\/127\.0\.0\.1:8001(?=\/api\/)/, ORIGIN)
      .replace(/^https:\/\/localhost:8000(?=\/api\/)/, ORIGIN)
      .replace(/^https:\/\/localhost:8001(?=\/api\/)/, ORIGIN);

    return url;
  }

  window.fetch = function(input, init) {
    init = init || {};

    try {
      if (typeof input === "string") {
        input = corrigirUrl(input);

        if (input.startsWith("/api/") || input.startsWith(ORIGIN + "/api/")) {
          init.credentials = "include";
        }
      } else if (input && input.url) {
        const novaUrl = corrigirUrl(input.url);

        if (novaUrl !== input.url) {
          input = new Request(novaUrl, input);
        }

        if (novaUrl.includes("/api/")) {
          init.credentials = "include";
        }
      }
    } catch (e) {
      console.warn("VÉRTICE IA: correção de API não aplicada em uma chamada.", e);
    }

    return originalFetch(input, init);
  };

  window.VERTICE_API_BASE = ORIGIN;
  window.API_BASE = ORIGIN;
  window.BASE_URL = ORIGIN;
})();
</script>
'''

# Remove patch antigo se existir
start = s.find("<script>\n(function(){\n  if (window.__VERTICE_PUBLIC_API_FINAL_FIX__)")
if start != -1:
    end = s.find("</script>", start)
    if end != -1:
        s = s[:start] + s[end + len("</script>"):]

# Insere no começo do head para carregar antes de qualquer JS do sistema
if "<head>" in s:
    s = s.replace("<head>", "<head>\n" + patch, 1)
else:
    s = patch + "\n" + s

# Remove origens locais fixas fora do patch antigo
s = s.replace("http://127.0.0.1:8000", "")
s = s.replace("http://127.0.0.1:8001", "")
s = s.replace("http://localhost:8000", "")
s = s.replace("http://localhost:8001", "")

p.write_text(s, encoding="utf-8")

final = p.read_text(encoding="utf-8")

print("Correção instalada.")
print("Patch final instalado?", "__VERTICE_PUBLIC_API_FINAL_FIX__" in final)
print("Existe API local antiga fora do patch? Conferir manualmente com Select-String depois.")
