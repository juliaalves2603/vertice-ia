from pathlib import Path

p = Path("melhorar_analise_sem_achismo.py")
s = p.read_text(encoding="utf-8")

s = s.replace(
    's = re.sub(pattern, new_function + \'\\n@app.get("/api/profile-public-analysis")\', s, count=1)',
    's = re.sub(pattern, lambda m: new_function + \'\\n@app.get("/api/profile-public-analysis")\', s, count=1)'
)

s = s.replace(
    'new_block,\n        html,\n        count=1',
    'lambda m: new_block,\n        html,\n        count=1'
)

p.write_text(s, encoding="utf-8")

print("Script corrigido. Agora rode novamente.")
