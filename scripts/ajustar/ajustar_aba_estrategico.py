from pathlib import Path
import re

p = Path("backend/static/index.html")
html = p.read_text(encoding="utf-8")

Path("backend/static/index_backup_ajuste_aba_estrategico.html").write_text(html, encoding="utf-8")

def replace_js_function(src, function_name, new_code):
    patterns = [
        f"async function {function_name}(",
        f"function {function_name}("
    ]

    start = -1
    for pat in patterns:
        start = src.find(pat)
        if start != -1:
            break

    if start == -1:
        raise RuntimeError(f"Função {function_name} não encontrada.")

    brace_start = src.find("{", start)
    if brace_start == -1:
        raise RuntimeError(f"Abertura da função {function_name} não encontrada.")

    depth = 0
    end = None

    for i in range(brace_start, len(src)):
        ch = src[i]

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if end is None:
        raise RuntimeError(f"Final da função {function_name} não encontrado.")

    return src[:start] + new_code.strip() + src[end:]

# 1. Remove botão confuso de localizar cliente na aba Estratégico
html = re.sub(
    r'\s*<button[^>]*onclick="testClientDiscovery\(\)"[^>]*>.*?<\/button>',
    '',
    html,
    flags=re.S
)

# 2. Ajusta a função loadAdvanced para usar SOMENTE a conta conectada
new_load_advanced = r'''
async function loadAdvanced(){
  try{
    show("Gerando relatório estratégico com dados reais da conta conectada...", "success");

    const data = await api("/api/advanced-report?limit=50");

    state.advanced = data.advanced_report;

    const box = $("advancedContent");
    if(box){
      box.innerHTML = advancedHtml(state.advanced);
    }

    show("Relatório estratégico da conta conectada gerado.", "success");

  }catch(e){
    show(e.message);
  }
}
'''

html = replace_js_function(html, "loadAdvanced", new_load_advanced)

# 3. Ajusta texto da aba Estratégico
html = html.replace(
    "Esta leitura mostra o que repetir, o que ajustar, o que não impulsionar e o que pode virar teste de tráfego pago.",
    "Esta aba usa dados reais da conta Meta conectada. Para analisar um cliente por link ou @, use a aba Perfil Cliente."
)

html = html.replace(
    "Preencha antes de baixar ou salvar em PDF. Esses dados aparecerão no relatório exportado.",
    "Opcional: preencha para personalizar o PDF. Esses dados aparecem no relatório, mas não são usados para buscar perfil. Para cliente por link/@, use a aba Perfil Cliente."
)

# 4. Ajusta placeholder do Instagram apenas no campo da aba Estratégico
html = re.sub(
    r'(<input id="clientInstagram"[^>]*placeholder=")[^"]*(")',
    r'\1Opcional: @cliente ou link apenas para aparecer no PDF\2',
    html
)

# 5. Adiciona aviso visual dentro da aba Estratégico, se ainda não existir
notice = r'''
    <div class="alert success">
      <strong>Organização das abas:</strong> Estratégico usa os dados reais da conta conectada na Meta.
      Para analisar bio, posts e posicionamento de outro cliente por link/@, use a aba <strong>Perfil Cliente</strong>.
    </div>

    <br>
'''

if "Organização das abas:" not in html:
    marker = '<div id="advancedContent">${state.advanced ? advancedHtml(state.advanced) : `<div class="empty">Clique em <strong>Gerar relatório estratégico</strong> para analisar os dados reais atuais.</div>`}</div>'
    html = html.replace(marker, notice + marker)

p.write_text(html, encoding="utf-8")

print("Aba Estratégico ajustada com sucesso.")
print("Agora Estratégico não tenta mais localizar @ cliente.")
print("Perfil Cliente continua responsável pela análise por link/@.")
