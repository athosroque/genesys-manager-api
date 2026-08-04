<div align="center">
  <img src="reports/figures/banner.svg?v=2" width="100%" alt="Genesys Manager V2 Banner">
</div>

# ⚡ Genesys Manager: Gestão Avançada Genesys Cloud

> Dashboard full-stack de alto desempenho para orquestração de usuários, filas e permissões na plataforma Genesys Cloud.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Vue.js](https://img.shields.io/badge/Vue.js-3-4FC08D?style=flat-square&logo=vuedotjs&logoColor=white)
![Tailwind](https://img.shields.io/badge/Tailwind-CSS-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Container-2496ED?style=flat-square&logo=docker&logoColor=white)
![Cloudflare](https://img.shields.io/badge/Cloudflare-Tunnel-F38020?style=flat-square&logo=cloudflare&logoColor=white)

---

<div align="center">

### 🌐 Página de Apresentação do Projeto

**[→ Ver Portfólio Completo](https://genesys-manager.projetoathos.com.br)**

*Arquitetura · Stack técnica · Destaques de engenharia · Como rodar*

</div>

---

## 🎯 Explore o Projeto
- **🌐 Portfólio:** [Página de apresentação completa](https://genesys-manager.projetoathos.com.br)
- **🚀 Frontend:** [Vue 3 App](frontend/)
- **⚙️ Backend:** [FastAPI Core](backend/)
- **🔐 Auth local:** [Magic link + JWT](backend/auth_local.py) · [Rotas](backend/routes/auth_routes.py)

---

## 📌 Problema de Negócio

Originalmente um script manual no Google Colab, a gestão de usuários no Genesys Cloud era fragmentada e de difícil auditoria. O **Genesys Manager V2** centraliza essa operação em uma plataforma web segura, automatizando fluxos complexos de reativação e migração que antes levavam minutos em segundos.

## ✨ Funcionalidades

- **Login passwordless** — magic link por e-mail `@claro.com.br` (Resend); sessão JWT em cookie HttpOnly com idle de 48h (sliding).
- **Admin de usuários locais** — listar, cadastrar e excluir operadores da plataforma (`GET/POST/DELETE /auth/users*`); domínio sozinho não basta — o e-mail precisa existir em `users.json`.
- **Consulta e migração de usuários** — busca por matrícula/e-mail/UUID, reativação de contas e migração completa (divisão + role + grupo) em um fluxo só.
- **Trilha de Auditoria** — alterações de uma pessoa no período: **Pesquisar** traz só divisão; botões separados buscam filas, roles ou grupos (merge na lista), via `POST /audits/user-changes` (`deep_categories`) e cards normalizados no frontend.

## 🔐 Autenticação (resumo)

| Item | Comportamento |
| :--- | :--- |
| Login | Passwordless: `POST /auth/login` com e-mail → magic link |
| Domínio | Somente `@{ALLOWED_EMAIL_DOMAIN}` (padrão: `claro.com.br`) |
| Cadastro | Usuário **precisa** estar em `users.json` (admin cria ou edição manual). Ter o domínio não basta. |
| Link | Uso único, hash SHA-256 em `auth_tokens.json`, TTL **10 min** (`MAGIC_LINK_EXPIRE_MINUTES`) |
| Sessão | Cookie `access_token` HttpOnly; idle **48h** (`JWT_EXPIRE_MINUTES=2880`), renovado a cada request autenticado |
| E-mail | Resend (`RESEND_*`); FROM em domínio verificado (ex.: `noreply@projetoathos.com.br`) |
| Admin | Rotas `/auth/users*` exigem `role: admin` |

Detalhes e riscos residuais: [backend/README.md](backend/README.md#segurança).

## 📊 Stack Tecnológica

### Core Services
| Tecnologia | Função | Vantagem |
| :--- | :--- | :--- |
| **Python / FastAPI** | API Backend | Performante, assíncrona e tipagem forte. |
| **Vue 3 / Vite** | Dashboard Frontend | Interface reativa e rápida com Composition API. |
| **Tailwind CSS 3** | Design System | Estilização moderna e layout responsivo. |
| **Docker Compose** | Infraestrutura | Reprodutibilidade total do ambiente produtivo. |

## 📁 Estrutura do Projeto

| Pasta / arquivo | Para que serve |
| :--- | :--- |
| `backend/` | API FastAPI: auth magic link, proxy Genesys, auditoria, migração |
| `frontend/` | SPA Vue 3 (login, consulta/migração, trilha de auditoria, admin) |
| `refencia_retornos/` | Material de referência da Audit API (dicionário, âncora, amostras locais) |
| `docs/arquivo/` | Código/UI histórica fora do runtime (ex.: CLI de senha, UI antiga de auditoria) |
| `reports/figures/` | Banner e assets visuais do README / portfólio |
| `portfolio.html` | Página estática de apresentação do projeto |
| `docker-compose.yml` | Stack local: backend + frontend (nginx na porta **8082**) |
| `.gitignore` | Ignora `.env`, `users.json`, `auth_tokens.json`, amostras com PII, etc. |

```text
├── backend/                 # Runtime da API
├── frontend/                # Runtime da SPA
├── refencia_retornos/       # Referência Audit API (não é serviço)
├── docs/arquivo/            # Histórico / legado (não entra no Docker)
├── reports/figures/         # Assets visuais
├── portfolio.html           # Landing de portfólio
└── docker-compose.yml
```

## 🛠️ Pré-requisitos

Antes de iniciar, certifique-se de ter instalado:
- **Docker & Docker Compose** (Recomendado)
- **Python 3.11+** (Para execução local do backend)
- **Node.js 18+ & npm** (Para execução local do frontend)
- **Conta Genesys Cloud** com permissões de Admin para criar Client Credentials.

---

## 🚀 Como Executar

O projeto pode ser executado de duas formas principais: via Docker (idêntico à produção) ou em modo de desenvolvimento local.

### 🐳 1. Via Docker Compose (Recomendado)

Esta é a forma mais rápida de subir o ambiente completo.

1.  **Clone o repositório:**
    ```bash
    git clone https://github.com/athosroque/genesys-manager-v2-pilot.git
    cd genesys-manager-v2-pilot
    ```

2.  **Configure as variáveis de ambiente:**
    ```bash
    cp backend/.env.example backend/.env
    # Preencha Genesys OAuth, JWT_SECRET_KEY, RESEND_* e APP_BASE_URL
    # (nunca commite o .env — está no .gitignore)
    ```
    *Nota: Consulte a seção de [Variáveis de Ambiente](#-variáveis-de-ambiente) abaixo.*

3.  **Suba os containers:**
    ```bash
    docker-compose up -d --build
    ```

4.  **Acesse a aplicação:**
    - **Frontend (Compose):** [http://localhost:8082](http://localhost:8082)
    - **API Docs:** via proxy `/api/docs` ou backend exposto conforme o Compose

5.  **Primeiro usuário admin:** crie/edite `backend/users.json` (não versionado) com um usuário `role: admin` e e-mail `@claro.com.br`, ou use o módulo Admin após ter um admin inicial.

### 💻 2. Desenvolvimento Local

Útil para debugar ou fazer alterações rápidas sem rebuild de containers.

#### **Backend (FastAPI)**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
cp .env.example .env       # Configure suas credenciais
uvicorn main:app --reload
```

#### **Frontend (Vue 3)**
```bash
cd frontend
npm install
npm run dev
```

---

## 🔑 Variáveis de Ambiente

Arquivo `backend/.env` (copie de `backend/.env.example`). **Não** coloque secrets no frontend — só `VITE_API_BASE_URL`.

| Variável | Descrição | Exemplo / placeholder |
| :--- | :--- | :--- |
| `GENESYS_CLIENT_ID` | Client ID OAuth (Client Credentials) | `seu_client_id_aqui` |
| `GENESYS_CLIENT_SECRET` | Secret OAuth | `seu_client_secret_aqui` |
| `GENESYS_REGION` | Região da org Genesys | `sae1.pure.cloud` |
| `JWT_SECRET_KEY` | Assinatura dos JWTs locais | `openssl rand -hex 32` |
| `JWT_EXPIRE_MINUTES` | Idle da sessão (sliding) | `2880` (48h) |
| `ENVIRONMENT` | Flags de cookie (Secure / SameSite) | `development` / `production` |
| `COOKIE_DOMAIN` | Domain do cookie (prod); vazio no Compose local | `.projetoathos.com.br` ou vazio |
| `CORS_ORIGINS` | Origens permitidas (dev) | `http://localhost:5173,...` |
| `RESEND_API_KEY` | API key Resend (só backend) | `re_xxxxxxxxx` |
| `RESEND_FROM_EMAIL` | Remetente em domínio verificado | `Genesys Manager <noreply@projetoathos.com.br>` |
| `APP_BASE_URL` | Base pública (link do e-mail + redirect) | `https://genesys.projetoathos.com.br` — definida só no `.env` (o Compose **não** sobrescreve). Para testar magic links só em localhost, altere temporariamente no `backend/.env`; não bakeie localhost no `docker-compose.yml` se a stack também servir o domínio público. |
| `ALLOWED_EMAIL_DOMAIN` | Domínio aceito no login/cadastro | `claro.com.br` |
| `MAGIC_LINK_EXPIRE_MINUTES` | TTL do magic link | `10` |

Arquivos sensíveis **gitignored**: `.env`, `backend/users.json`, `backend/auth_tokens.json`.

---
**Desenvolvido por Athos** - [LinkedIn](https://www.linkedin.com/in/athosroque) | [GitHub](https://github.com/athosroque)
