from pathlib import Path
import re

p = Path("backend/app.py")

if not p.exists():
    raise RuntimeError("backend/app.py não encontrado.")

s = p.read_text(encoding="utf-8")
Path("backend/app_backup_reparo_meta_graph_get.py").write_text(s, encoding="utf-8")

nova_funcao = r'''
def _meta_graph_get(path: str, token_or_params=None, params: dict | None = None):
    """
    Função compatível com os dois formatos usados na VÉRTICE:

    1) _meta_graph_get("me", user_token, {"fields": "id,name"})
    2) _meta_graph_get("me/accounts", {"fields": "...", "access_token": token})
    """
    import os, requests

    api_version = os.getenv("META_API_VERSION", "v25.0")
    url = f"https://graph.facebook.com/{api_version}/{path.lstrip('/')}"

    # Formato antigo: path, token, params
    if isinstance(token_or_params, str):
        final_params = params.copy() if isinstance(params, dict) else {}
        final_params["access_token"] = token_or_params

    # Formato novo: path, params
    elif isinstance(token_or_params, dict):
        final_params = token_or_params.copy()

    # Sem params
    else:
        final_params = params.copy() if isinstance(params, dict) else {}

    try:
        r = requests.get(url, params=final_params, timeout=30)
        data = r.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "message": "Erro ao chamar Graph API.",
            "path": path,
            "error": str(e)
        })

    if isinstance(data, dict) and data.get("error"):
        raise HTTPException(status_code=400, detail={
            "message": "Erro retornado pela Meta.",
            "path": path,
            "meta": data
        })

    return data
'''

# Troca TODAS as versões existentes da função _meta_graph_get pela versão compatível
pattern = r'def _meta_graph_get\(.*?\n(?=\ndef |\n@app\.|\n# =|\Z)'
matches = re.findall(pattern, s, flags=re.S)

if not matches:
    raise RuntimeError("Nenhuma função _meta_graph_get encontrada para substituir.")

for m in matches:
    s = s.replace(m, nova_funcao + "\n", 1)

p.write_text(s, encoding="utf-8")

print("Reparo aplicado com sucesso.")
print("Funções _meta_graph_get encontradas e substituídas:", len(matches))
