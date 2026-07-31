# VÉRTICE IA

Sistema inteligente para gestão estratégica de redes sociais, análise de desempenho e acompanhamento de clientes.

## Sobre o projeto

O VÉRTICE IA é uma plataforma desenvolvida para centralizar a gestão de clientes, integrar dados da Meta (Facebook e Instagram), gerar relatórios estratégicos e apoiar a tomada de decisões para empresas e profissionais de marketing.

## Principais funcionalidades

- Login de administradores
- Gestão de clientes
- Login do cliente via Meta (Facebook)
- Integração com a Graph API da Meta
- Monitoramento de tokens
- Relatórios estratégicos
- Dashboard comercial
- Acompanhamento quinzenal
- Histórico de clientes
- Exportação de relatórios
- Painel administrativo

## Tecnologias

### Backend

- Python
- FastAPI
- Uvicorn
- SQLite
- Requests

### Frontend

- HTML5
- CSS3
- JavaScript

### Infraestrutura

- Docker
- Docker Compose
- Nginx
- Ubuntu Server
- Hostinger VPS

## Estrutura do projeto

```text
backend/
scripts/
docs/
docker/
nginx/
backups/
```

## Instalação (Desenvolvimento)

```bash
python -m venv .venv
```

Windows

```bash
.venv\Scripts\activate
```

Linux

```bash
source .venv/bin/activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Execute:

```bash
uvicorn backend.app:app --host 0.0.0.0 --port 8001
```

## Produção

O projeto foi preparado para execução utilizando:

- Docker
- Docker Compose
- Nginx
- VPS Linux

## Segurança

Os arquivos `.env`, bancos de dados e demais informações sensíveis não são versionados no Git.

## Status

🚧 Em desenvolvimento ativo.

## Licença

Projeto privado.
Todos os direitos reservados.

---

**Desenvolvido por Júlia Alves**