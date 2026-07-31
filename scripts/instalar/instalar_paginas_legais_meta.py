from pathlib import Path

p = Path("backend/app.py")

if not p.exists():
    raise RuntimeError("backend/app.py não encontrado.")

s = p.read_text(encoding="utf-8")

Path("backend/app_backup_paginas_legais_meta.py").write_text(s, encoding="utf-8")

marker = "# ==== VERTICE PAGINAS LEGAIS META ===="

if marker in s:
    print("Páginas legais já estavam instaladas.")
else:
    bloco = r'''

# ==== VERTICE PAGINAS LEGAIS META ====

VERTICE_LEGAL_STYLE = """
<style>
  body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: #f4f5f7;
    color: #111827;
    line-height: 1.65;
  }
  .page {
    max-width: 920px;
    margin: 36px auto;
    background: #fff;
    padding: 42px;
    border-radius: 22px;
    box-shadow: 0 14px 34px rgba(15,23,42,.08);
  }
  .brand {
    color: #f4b400;
    font-size: 12px;
    letter-spacing: 4px;
    font-weight: 800;
    text-transform: uppercase;
  }
  h1 {
    font-size: 34px;
    margin: 10px 0 18px;
  }
  h2 {
    margin-top: 28px;
    font-size: 20px;
    border-bottom: 1px solid #e5e7eb;
    padding-bottom: 8px;
  }
  p, li {
    font-size: 15px;
  }
  .muted {
    color: #6b7280;
    font-size: 13px;
  }
  .box {
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    padding: 16px;
    border-radius: 14px;
  }
  a {
    color: #111827;
    font-weight: 700;
  }
</style>
"""

VERTICE_POLITICA_PRIVACIDADE_HTML = f"""
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Política de Privacidade | VÉRTICE IA</title>
{VERTICE_LEGAL_STYLE}
</head>
<body>
<div class="page">
  <div class="brand">VÉRTICE IA</div>
  <h1>Política de Privacidade</h1>
  <p class="muted">Última atualização: 19/07/2026</p>

  <p>
    A VÉRTICE IA é uma plataforma de análise estratégica de presença digital, criada para apoiar
    empresas e profissionais na leitura de métricas, conteúdos, posicionamento e resultados em canais conectados à Meta.
  </p>

  <h2>1. Dados que podemos coletar</h2>
  <p>
    Quando uma conta é conectada à VÉRTICE IA por meio do Facebook Login/Meta, podemos acessar dados autorizados pelo próprio usuário,
    de acordo com as permissões concedidas no momento da conexão.
  </p>
  <ul>
    <li>Informações básicas da Página do Facebook conectada.</li>
    <li>Informações da conta profissional do Instagram vinculada à Página.</li>
    <li>Nome de usuário, identificação da conta e dados públicos do perfil.</li>
    <li>Métricas e insights de desempenho, como alcance, impressões, interações e dados relacionados ao conteúdo.</li>
    <li>Dados de posts, mídia e indicadores usados para análise estratégica.</li>
  </ul>

  <h2>2. Como usamos os dados</h2>
  <p>
    Os dados são utilizados exclusivamente para gerar análises, relatórios estratégicos, diagnósticos comerciais,
    acompanhamento de evolução e recomendações de conteúdo e posicionamento.
  </p>
  <p>
    A VÉRTICE IA não vende dados pessoais, não promete resultados comerciais garantidos e não usa os dados para fins
    diferentes daqueles relacionados à análise e gestão estratégica autorizada pelo usuário.
  </p>

  <h2>3. Compartilhamento de dados</h2>
  <p>
    Os dados acessados pela VÉRTICE IA não são vendidos a terceiros. As informações podem ser utilizadas internamente
    para gerar relatórios, propostas, históricos comerciais e materiais estratégicos para o próprio cliente conectado.
  </p>

  <h2>4. Armazenamento e segurança</h2>
  <p>
    Algumas informações podem ser armazenadas em banco de dados local ou ambiente controlado da VÉRTICE IA para permitir
    histórico, comparação de evolução e geração de relatórios. Aplicamos medidas razoáveis de proteção para evitar acesso indevido.
  </p>

  <h2>5. Controle do usuário</h2>
  <p>
    O usuário pode solicitar a exclusão dos dados associados à sua conta conectada. As instruções estão disponíveis na página:
  </p>
  <p>
    <a href="/exclusao-dados">https://appverticeia.com.br/exclusao-dados</a>
  </p>

  <h2>6. Revogação de acesso</h2>
  <p>
    O usuário também pode revogar o acesso da VÉRTICE IA diretamente nas configurações da sua conta Meta/Facebook,
    na seção de aplicativos e sites conectados.
  </p>

  <h2>7. Contato</h2>
  <div class="box">
    <p>
      Para dúvidas sobre privacidade ou solicitação de exclusão de dados, entre em contato:
    </p>
    <p>
      <strong>E-mail:</strong> jujujulia.gomes757@gmail.com
    </p>
    <p>
      <strong>Responsável:</strong> Júlia Gomes Alves
    </p>
  </div>
</div>
</body>
</html>
"""

VERTICE_EXCLUSAO_DADOS_HTML = f"""
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Exclusão de Dados | VÉRTICE IA</title>
{VERTICE_LEGAL_STYLE}
</head>
<body>
<div class="page">
  <div class="brand">VÉRTICE IA</div>
  <h1>Instruções para Exclusão de Dados</h1>
  <p class="muted">Última atualização: 19/07/2026</p>

  <p>
    Esta página explica como usuários conectados à VÉRTICE IA podem solicitar a exclusão dos dados associados à sua conta Meta/Facebook/Instagram.
  </p>

  <h2>1. Como solicitar exclusão</h2>
  <p>
    Para solicitar a exclusão dos dados armazenados pela VÉRTICE IA, envie um e-mail com o assunto
    <strong>“Exclusão de Dados - VÉRTICE IA”</strong> para:
  </p>

  <div class="box">
    <p><strong>E-mail:</strong> jujujulia.gomes757@gmail.com</p>
  </div>

  <p>No corpo do e-mail, informe:</p>
  <ul>
    <li>Nome completo ou nome da empresa.</li>
    <li>Instagram conectado.</li>
    <li>Página do Facebook vinculada, se souber.</li>
    <li>Solicitação clara de exclusão dos dados da VÉRTICE IA.</li>
  </ul>

  <h2>2. Prazo de atendimento</h2>
  <p>
    Após o recebimento da solicitação, a VÉRTICE IA analisará e removerá os dados associados à conta conectada
    em prazo razoável, salvo quando houver necessidade de retenção por obrigação legal, segurança ou prevenção de fraude.
  </p>

  <h2>3. Revogar acesso pela Meta</h2>
  <p>
    Além de solicitar exclusão à VÉRTICE IA, o usuário pode remover o acesso do aplicativo diretamente em sua conta Meta/Facebook:
  </p>
  <ul>
    <li>Acesse Facebook ou Instagram.</li>
    <li>Entre em Configurações.</li>
    <li>Procure por Aplicativos e Sites.</li>
    <li>Localize VÉRTICE IA.</li>
    <li>Remova ou revogue o acesso.</li>
  </ul>

  <h2>4. Dados removidos</h2>
  <p>
    A solicitação de exclusão pode incluir dados de conexão, identificadores da conta, relatórios salvos,
    histórico de análise e informações armazenadas para fins de diagnóstico comercial.
  </p>

  <h2>5. Contato</h2>
  <div class="box">
    <p><strong>Responsável:</strong> Júlia Gomes Alves</p>
    <p><strong>E-mail:</strong> jujujulia.gomes757@gmail.com</p>
  </div>
</div>
</body>
</html>
"""

@app.get("/politica-privacidade")
def vertice_politica_privacidade():
    from fastapi.responses import HTMLResponse
    return HTMLResponse(VERTICE_POLITICA_PRIVACIDADE_HTML)

@app.get("/exclusao-dados")
def vertice_exclusao_dados():
    from fastapi.responses import HTMLResponse
    return HTMLResponse(VERTICE_EXCLUSAO_DADOS_HTML)

# ==== FIM VERTICE PAGINAS LEGAIS META ====
'''
    s = s + bloco
    p.write_text(s, encoding="utf-8")
    print("Páginas legais instaladas com sucesso.")

print("Conferência concluída.")
