from pathlib import Path
import re
import shutil

base = Path("backend/static")
index = base / "index.html"

if not index.exists():
    raise RuntimeError("index.html não encontrado.")

# Backup do arquivo quebrado atual
shutil.copy2(index, base / "index_quebrado_syntax_html_backup.html")

# Tenta restaurar a versão anterior ao relatório comercial
candidatos = [
    base / "index_backup_relatorio_comercial_meta.html",
    base / "index_backup_corrigir_api_publica.html",
    base / "index_backup_corrigir_tela_conectando.html",
]

restaurado = False

for c in candidatos:
    if c.exists():
        shutil.copy2(c, index)
        print("Restaurado a partir de:", c.name)
        restaurado = True
        break

if not restaurado:
    print("Nenhum backup principal encontrado. Vou limpar o arquivo atual.")
    
s = index.read_text(encoding="utf-8")

# Remove scripts que instalamos e que podem ter quebrado o JavaScript
marcadores = [
    "__VERTICE_RELATORIO_META_COMERCIAL__",
    "__VERTICE_PUBLIC_API_FINAL_FIX__",
    "__VERTICE_FIX_API_PUBLICA__",
    "__VERTICE_FETCH_RELATIVO_FINAL__"
]

for marcador in marcadores:
    while marcador in s:
        pos = s.find(marcador)
        start = s.rfind("<script", 0, pos)
        end = s.find("</script>", pos)

        if start == -1 or end == -1:
            break

        end = end + len("</script>")
        s = s[:start] + "\n" + s[end:]
        print("Removido script:", marcador)

# Corrige chamadas fixas antigas para API relativa
trocas = {
    "http://127.0.0.1:8000/api": "/api",
    "http://127.0.0.1:8001/api": "/api",
    "http://localhost:8000/api": "/api",
    "http://localhost:8001/api": "/api",
    "https://127.0.0.1:8000/api": "/api",
    "https://127.0.0.1:8001/api": "/api",
    "https://localhost:8000/api": "/api",
    "https://localhost:8001/api": "/api",
}

for old, new in trocas.items():
    s = s.replace(old, new)

# Remove imagem quebrada literal
s = s.replace('${img.data}', '')

index.write_text(s, encoding="utf-8")

print("Frontend estabilizado.")
print("Ainda existe marcador comercial?", "__VERTICE_RELATORIO_META_COMERCIAL__" in s)
print("Ainda existe marcador fetch final?", "__VERTICE_FETCH_RELATIVO_FINAL__" in s)
print("Ainda existe ${img.data}?", "${img.data}" in s)
