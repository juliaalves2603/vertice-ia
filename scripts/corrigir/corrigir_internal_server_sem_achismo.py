from pathlib import Path

p = Path("backend/app.py")
s = p.read_text(encoding="utf-8")

Path("backend/app_backup_corrigir_internal_server_sem_achismo.py").write_text(s, encoding="utf-8")

s = s.replace(
    '"positioning_text": positioning_atual,',
    '"positioning_text": posicionamento_atual,'
)

p.write_text(s, encoding="utf-8")

print("Correção aplicada: positioning_atual -> posicionamento_atual")
