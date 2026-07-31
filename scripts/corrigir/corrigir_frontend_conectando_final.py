from pathlib import Path
import re

p = Path("backend/static/index.html")

if not p.exists():
    raise RuntimeError("backend/static/index.html não encontrado.")

s = p.read_text(encoding="utf-8")

Path("backend/static/index_backup_corrigir_frontend_conectando_final.html").write_text(s, encoding="utf-8")

# 1. Troca APIs locais por rota relativa.
replaces = {
    "http://127.0.0.1:8000/api": "/api",
    "http://127.0.0.1:8001/api": "/api",
    "http://localhost:8000/api": "/api",
    "http://localhost:8001/api": "/api",
    "https://127.0.0.1:8000/api": "/api",
    "https://127.0.0.1:8001/api": "/api",
    "https://localhost:8000/api": "/api",
    "https://localhost:8001/api": "/api",
}

for old, new in replaces.items():
    s = s.replace(old, new)

# 2. Corrige imagem quebrada literal ${img.data}
s = s.replace('src="${img.data}"', 'src=""')
s = s.replace("src='${img.data}'", "src=''")
s = s.replace('href="${img.data}"', 'href="#"')
s = s.replace("href='${img.data}'", "href='#'")

# 3. Evita que algum patch antigo fique sobrescrevendo fetch de forma incorreta
s = re.sub(
    r"<script>\s*\(function\(\)\{\s*if \(window\.__VERTICE_PUBLIC_API_FINAL_FIX__\)[\s\S]*?</script>",
    "",
    s
)

s = re.sub(
    r"<script>\s*\(function\(\)\{\s*if \(window\.__VERTICE_FIX_API_PUBLICA__\)[\s\S]*?</script>",
    "",
    s
)

# 4. Instala um patch simples e seguro: qualquer fetch local vira /api no domínio atual
patch = r'''
<script>
(function(){
  if (window.__VERTICE_FETCH_RELATIVO_FINAL__) return;
  window.__VERTICE_FETCH_RELATIVO_FINAL__ = true;

  const originalFetch = window.fetch.bind(window);

  window.fetch = function(input, init) {
    init = init || {};

    if (typeof input === "string") {
      input = input
        .replace(/^http:\/\/127\.0\.0\.1:8000\/api/, "/api")
        .replace(/^http:\/\/127\.0\.0\.1:8001\/api/, "/api")
        .replace(/^http:\/\/localhost:8000\/api/, "/api")
        .replace(/^http:\/\/localhost:8001\/api/, "/api");

      if (input.startsWith("/api")) {
        init.credentials = "include";
      }
    }

    return originalFetch(input, init);
  };
})();
</script>
'''

if "__VERTICE_FETCH_RELATIVO_FINAL__" not in s:
    if "<head>" in s:
        s = s.replace("<head>", "<head>\n" + patch, 1)
    else:
        s = patch + "\n" + s

p.write_text(s, encoding="utf-8")

final = p.read_text(encoding="utf-8")

print("Frontend corrigido.")
print("Ainda existe 127.0.0.1:8000?", "127.0.0.1:8000" in final)
print("Ainda existe 127.0.0.1:8001?", "127.0.0.1:8001" in final)
print("Ainda existe localhost:8000?", "localhost:8000" in final)
print("Ainda existe ${img.data}?", "${img.data}" in final)
print("Patch fetch relativo instalado?", "__VERTICE_FETCH_RELATIVO_FINAL__" in final)
