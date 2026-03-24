# ⚙️ Genesys Manager: Backend Core

O backend do Genesys Manager é uma API assíncrona construída em **Python 3.11** utilizando o framework **FastAPI**. Ele atua como um middleware seguro entre o frontend e a API oficial do Genesys Cloud.

---

## 🛠️ Stack Tecnológica

- **FastAPI**: Framework web moderno, de alto desempenho e com suporte nativo a `async/await`.
- **Pydantic Settings**: Gestão de variáveis de ambiente e validação de configurações.
- **Httpx**: Cliente HTTP assíncrono para integração com a API da Genesys.
- **Python-jose**: Gerenciamento de tokens JWT (assinatura e validação).
- **Passlib (Bcrypt)**: Algoritmo de hash seguro para armazenamento de senhas locais.

---

## 🔐 Lógica de Autenticação Dual

O sistema implementa uma camada dupla de segurança para garantir o isolamento total das credenciais de missão crítica:

1.  **Autenticação Local (RBAC):**
    - Usuários locais (operadores) são validados contra um `users.json`.
    - O backend emite um token **JWT** assinado com uma chave secreta (`JWT_SECRET_KEY`).
    - Este token é armazenado em um cookie `HttpOnly` no navegador, protegendo contra ataques XSS.

2.  **Autenticação Genesys Proxy:**
    - O backend utiliza o fluxo **OAuth2 Client Credentials** para obter tokens diretamente da Genesys.
    - O token da Genesys **nunca** sai do backend. Ele é mantido em cache de memória e renovado automaticamente antes de expirar.

---

## 🔌 Registro de Endpoints (API Registry)

Abaixo, os principais endpoints internos e sua correlação com a API da Genesys:

| Rota Interna | Método | Descrição | Endpoint Genesys Correspondente |
| :--- | :--- | :--- | :--- |
| `/api/auth/login` | `POST` | Autentica operador e gera cookie JWT | - |
| `/api/users/search` | `POST` | Busca avançada de usuários | `/api/v2/users/search` |
| `/api/users/{id}` | `GET` | Detalhes completos do usuário | `/api/v2/users/{userId}` |
| `/api/users/{id}` | `PATCH` | Reativação de conta (uso de `version`) | `/api/v2/users/{userId}` |
| `/api/queues/members` | `DELETE` | Remoção de filas em massa | `/api/v2/routing/queues/...` |
| `/api/groups/members` | `DELETE` | Remoção de grupos (via query params) | `/api/v2/groups/{groupId}/members` |
| `/api/migration/full` | `POST` | Fluxo completo (Divisão + Role + Grupo) | Multi-endpoint (Authorization + Groups) |

---

## 📁 Estrutura de Diretórios

```text
├── routes/             # Definição modular de rotas (APIRouter)
├── auth.py             # Lógica de Integração OAuth2 Genesys
├── auth_local.py       # Lógica de JWT e Segurança Local
├── config.py           # Definição de Schemas (Pydantic)
├── main.py             # Entrada da aplicação e Middlewares
└── users.json          # Banco de dados de usuários locais (JSON)
```

---

## 🚀 Como Rodar Localmente (Desenvolvimento)

Para executar apenas o backend fora do Docker:

1.  **Crie um ambiente virtual:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # Linux/Mac
    # No Windows: .venv\Scripts\activate
    ```

2.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure o arquivo `.env`:**
    Copie o `.env.example` e preencha as variáveis.

4.  **Inicie o servidor:**
    ```bash
    uvicorn main:app --reload
    ```
    *A API estará acessível em `http://localhost:8000`.*

---

**Camada de Segurança:** Todas as rotas sob `/api/*` (exceto `/auth/login`) exigem um JWT válido e verificado pelo middleware de segurança local.
