from pathlib import Path
import re

p = Path("backend/static/index.html")

if not p.exists():
    raise RuntimeError("backend/static/index.html não encontrado.")

html = p.read_text(encoding="utf-8")
Path("backend/static/index_backup_botao_acompanhamento_quinzenal.html").write_text(html, encoding="utf-8")

# Botão visual do módulo
botao = '''
<button class="btn" onclick="window.location.href='/acompanhamento-quinzenal'">Acompanhamento Quinzenal</button>
'''

# Evita duplicar
if "/acompanhamento-quinzenal" not in html:
    # Coloca o botão junto dos botões principais da Visão Geral
    alvo = '<button class="btn" onclick="go(\'metricas\')">Importar métricas reais</button>'
    
    if alvo in html:
        html = html.replace(alvo, alvo + "\n        " + botao, 1)
    else:
        # Plano B: adiciona depois do título da Visão Geral
        alvo2 = '<h1 id="title">Visão Geral</h1>'
        if alvo2 in html:
            html = html.replace(
                alvo2,
                alvo2 + "\n        " + botao,
                1
            )
        else:
            raise RuntimeError("Não encontrei o ponto seguro para inserir o botão.")

p.write_text(html, encoding="utf-8")

print("Botão Acompanhamento Quinzenal adicionado com sucesso.")
print("Backup criado: backend/static/index_backup_botao_acompanhamento_quinzenal.html")
