from pathlib import Path
import re

p = Path("backend/app.py")
s = p.read_text(encoding="utf-8")

# Garante imports necessários
if "import base64" not in s:
    s = s.replace("import requests", "import base64\nimport requests")

if "import secrets" not in s:
    s = s.replace("import requests", "import secrets\nimport requests")

# Garante Request no FastAPI
m = re.search(r"from fastapi import ([^\n]+)", s)
if m:
    nomes = [x.strip() for x in m.group(1).split(",")]
    if "Request" not in nomes:
        nomes.append("Request")
    s = s[:m.start()] + "from fastapi import " + ", ".join(nomes) + s[m.end():]

# Garante Response no fastapi.responses
m = re.search(r"from fastapi\.responses import ([^\n]+)", s)
if m:
    nomes = [x.strip() for x in m.group(1).split(",")]
    if "Response" not in nomes:
        nomes.append("Response")
    s = s[:m.start()] + "from fastapi.responses import " + ", ".join(nomes) + s[m.end():]

p.write_text(s, encoding="utf-8")
print("Imports corrigidos com sucesso.")
