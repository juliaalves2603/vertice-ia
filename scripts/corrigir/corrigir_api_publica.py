from pathlib import Path

p = Path("backend/static/index.html")

if not p.exists():
    raise RuntimeError("backend/static/index.html não encontrado.")

s = p.read_text(encoding="utf-8")

Path("backend/static/index_backup_corrigir_api_publica.html").write_text(s, encoding="utf-8")

# Remove chamadas fixas ao localhost/127 para a API funcionar no domínio público
replaces = {
    "http://127.0.0.1:8000": "",
    "http://127.0.0.1:8001": "",
    "http://localhost:8000": "",
    "http://localhost:8001": "",
    "https://127.0.0.1:8000": "",
    "https://127.0.0.1:8001": "",
    "https://localhost:8000": "",
    "https://localhost:8001": "",
}

for old, new in replaces.items():
    s = s.replace(old, new)

# Proteção extra: se alguma chamada fetch antiga sobrar, redireciona para o domínio atual
patch = r'''
<script>
(function(){
  if (window.__VERTICE_FIX_API_PUBLICA__) return;
  window.__VERTICE_FIX_API_PUBLICA__ = true;

  const originalFetch = window.fetch;

  window.fetch = function(input, init) {
    try {
      if (typeof input === "string") {
        input = input
          .replace(/^http:\/\/127\.0\.0\.1:8000(?=\/api\/)/, window.location.origin)
          .replace(/^http:\/\/127\.0\.0\.1:8001(?=\/api\/)/, window.location.origin)
          .replace(/^http:\/\/localhost:8000(?=\/api\/)/, window.location.origin)
          .replace(/^http:\/\/localhost:8001(?=\/api\/)/, window.location.origin);
      }
    } catch (e) {}

    return originalFetch.call(this, input, init);
  };
})();
</script>
'''

if "__VERTICE_FIX_API_PUBLICA__" not in s:
    if "<head>" in s:
        s = s.replace("<head>", "<head>\n" + patch, 1)
    else:
        s = patch + "\n" + s

p.write_text(s, encoding="utf-8")

final = p.read_text(encoding="utf-8")

print("Correção aplicada.")
print("Ainda existe 127.0.0.1:8000?", "127.0.0.1:8000" in final)
print("Ainda existe localhost:8000?", "localhost:8000" in final)
print("Ainda existe 127.0.0.1:8001?", "127.0.0.1:8001" in final)
print("Patch público instalado?", "__VERTICE_FIX_API_PUBLICA__" in final)
