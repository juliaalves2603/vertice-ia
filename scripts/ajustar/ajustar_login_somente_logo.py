from pathlib import Path
import re

p = Path("backend/app.py")

if not p.exists():
    raise RuntimeError("backend/app.py não encontrado.")

s = p.read_text(encoding="utf-8")
Path("backend/app_backup_remover_texto_vertice_logo.py").write_text(s, encoding="utf-8")

# =====================================================
# 1) AJUSTAR BLOCO VISUAL DO LOGIN
# =====================================================

# Garante CSS do logo
if ".brand-logo-login" not in s:
    css = """
.brand-logo-login {
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  margin: 0 0 18px 0;
}
.brand-logo-login img {
  width: 84px;
  height: 84px;
  object-fit: contain;
  border-radius: 18px;
  background: rgba(255,255,255,.96);
  padding: 7px;
  box-shadow: 0 8px 18px rgba(0,0,0,.16);
}
.login-subtitle {
  text-align: center;
  color: #cbd5e1;
  margin: 0 0 24px 0;
  line-height: 1.6;
  font-size: 15px;
}
.login-eyebrow {
  text-align: center;
  color: #f4b400;
  font-size: 12px;
  letter-spacing: 4px;
  font-weight: 800;
  text-transform: uppercase;
  margin-bottom: 10px;
}
"""
    if "<style>" in s:
        s = s.replace("<style>", "<style>\n" + css, 1)

# =====================================================
# 2) TROCAR CABEÇALHO DO LOGIN
# remove "VÉRTICE IA" e deixa só logo + subtítulo
# =====================================================

patterns = [
    (
        r'<div class="brand-logo-login">\s*<img src="/static/assets/logo-vertice-ia\.png" alt="Logo VÉRTICE IA">\s*</div>\s*<div class="eyebrow">Acesso restrito</div>\s*<h1>VÉRTICE IA</h1>\s*<p>Entre para acessar o painel estratégico com dados reais, relatórios e análise de conteúdo\.</p>',
        '''<div class="brand-logo-login">
      <img src="/static/assets/logo-vertice-ia.png" alt="Logo">
    </div>
    <div class="login-eyebrow">Acesso restrito</div>
    <p class="login-subtitle">Entre para acessar o painel estratégico com dados reais, relatórios e análise de conteúdo.</p>'''
    ),
    (
        r'<div class="logo">V</div>\s*<div class="eyebrow">Acesso restrito</div>\s*<h1>VÉRTICE IA</h1>\s*<p>Entre para acessar o painel estratégico com dados reais, relatórios e análise de conteúdo\.</p>',
        '''<div class="brand-logo-login">
      <img src="/static/assets/logo-vertice-ia.png" alt="Logo">
    </div>
    <div class="login-eyebrow">Acesso restrito</div>
    <p class="login-subtitle">Entre para acessar o painel estratégico com dados reais, relatórios e análise de conteúdo.</p>'''
    )
]

for pattern, repl in patterns:
    s, count = re.subn(pattern, repl, s, count=1, flags=re.S)

# =====================================================
# 3) REMOVER TEXTO "VÉRTICE IA" DO FOOTER DO LOGIN
# =====================================================
s = s.replace(
    "VÉRTICE IA • Acesso protegido para demonstração e operação do painel.",
    "Acesso protegido para demonstração e operação do painel."
)

# caso exista sem bullet
s = s.replace(
    "VÉRTICE IA - Acesso protegido para demonstração e operação do painel.",
    "Acesso protegido para demonstração e operação do painel."
)

# =====================================================
# 4) REMOVER TÍTULO H1 SOLTO, SE SOBRAR
# =====================================================
s = s.replace("<h1>VÉRTICE IA</h1>", "")

# =====================================================
# 5) OPCIONAL: TIRAR O TEXTO DO <title> DA PÁGINA DE LOGIN
# deixa mais neutro
# =====================================================
s = s.replace("<title>VÉRTICE IA</title>", "<title>Login</title>")

p.write_text(s, encoding="utf-8")

print("Ajuste aplicado com sucesso.")
print("Texto 'VÉRTICE IA' removido do bloco principal do login.")
print("Logo mantido como identidade visual.")
