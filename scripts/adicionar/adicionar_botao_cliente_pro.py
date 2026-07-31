from pathlib import Path

p = Path("backend/static/index.html")

if not p.exists():
    raise RuntimeError("backend/static/index.html não encontrado.")

html = p.read_text(encoding="utf-8")
Path("backend/static/index_backup_botao_cliente_pro.html").write_text(html, encoding="utf-8")

botao = '''
<button class="btn ghost" onclick="window.location.href='/meta-comercial-pro'">Cliente Pro</button>
'''

# Evita duplicar o botão
if "/meta-comercial-pro" not in html:
    # Preferência: colocar perto do botão Acompanhamento Quinzenal
    alvo = '<button class="btn" onclick="window.location.href=\'/acompanhamento-quinzenal\'">Acompanhamento Quinzenal</button>'

    if alvo in html:
        html = html.replace(alvo, alvo + "\n        " + botao, 1)
    else:
        # Plano B: colocar perto do botão de métricas
        alvo2 = '<button class="btn" onclick="go(\'metricas\')">Importar métricas reais</button>'

        if alvo2 in html:
            html = html.replace(alvo2, alvo2 + "\n        " + botao, 1)
        else:
            raise RuntimeError("Não encontrei ponto seguro para inserir o botão Cliente Pro.")

p.write_text(html, encoding="utf-8")

print("Botão Cliente Pro adicionado com sucesso.")
print("Backup criado: backend/static/index_backup_botao_cliente_pro.html")
