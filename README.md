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
- **🔐 Segurança:** [Protocolo de Autenticação](backend/auth.py)

---

## 📌 Problema de Negócio

Originalmente um script manual no Google Colab, a gestão de usuários no Genesys Cloud era fragmentada e de difícil auditoria. O **Genesys Manager V2** centraliza essa operação em uma plataforma web segura, automatizando fluxos complexos de reativação e migração que antes levavam minutos em segundos.

## 📊 Stack Tecnológica

### Core Services
| Tecnologia | Função | Vantagem |
| :--- | :--- | :--- |
| **Python / FastAPI** | API Backend | Performante, assíncrona e tipagem forte. |
| **Vue 3 / Vite** | Dashboard Frontend | Interface reativa e rápida com Composition API. |
| **Tailwind CSS 3** | Design System | Estilização moderna e layout responsivo. |
| **Docker Compose** | Infraestrutura | Reprodutibilidade total do ambiente produtivo. |

## 📁 Estrutura do Projeto

```text
├── backend/            # API Python (FastAPI, Auth, Routes)
├── frontend/           # Interface Vue 3 (Vite, Tailwind)
├── reports/            # Ativos visuais e documentação técnica
│   └── figures/        # Banners e diagramas
├── docker-compose.yml  # Orquestração de containers
└── .gitignore          # Proteção de envs e caches
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
    Copie o arquivo de exemplo e preencha com suas credenciais:
    ```bash
    cp backend/.env.example backend/.env
    ```
    *Nota: Consulte a seção de [Variáveis de Ambiente](#-variáveis-de-ambiente) abaixo.*

3.  **Suba os containers:**
    ```bash
    docker-compose up -d --build
    ```

4.  **Acesse a aplicação:**
    - **Frontend:** [http://localhost:80](http://localhost:80)
    - **API Docs (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)

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

O sistema utiliza as seguintes variáveis no arquivo `backend/.env`:

| Variável | Descrição | Exemplo |
| :--- | :--- | :--- |
| `GENESYS_CLIENT_ID` | Client ID de uma integração OAuth | `ae12...` |
| `GENESYS_CLIENT_SECRET` | Secret da integração OAuth | `xP92...` |
| `GENESYS_REGION` | Região da sua Org Genesys | `sae1.pure.cloud` |
| `JWT_SECRET_KEY` | Chave para assinatura de tokens locais | `openssl rand -hex 32` |
| `ENVIRONMENT` | Ambiente de execução | `development` / `production` |

---
**Desenvolvido por Athos** - [LinkedIn](https://www.linkedin.com/in/athosroque) | [GitHub](https://github.com/athosroque)
