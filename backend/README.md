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

Prefixo externo `/api/*` (o Nginx do frontend estripa esse prefixo antes de
encaminhar pro backend — ver `frontend/nginx.conf`). Endpoints internos
exigem cookie JWT válido (`Depends(get_current_user)`), exceto `/auth/login`.

**Auth** (`routes/auth_routes.py`, prefixo `/auth`)

| Rota Interna | Método | Descrição |
| :--- | :--- | :--- |
| `/api/auth/login` | `POST` | Autentica operador e gera cookie JWT |
| `/api/auth/logout` | `POST` | Invalida a sessão |
| `/api/auth/me` | `GET` | Sessão atual (usado no boot do frontend) |

**Users** (`routes/users.py`, prefixo `/users`)

| Rota Interna | Método | Descrição | Endpoint Genesys Correspondente |
| :--- | :--- | :--- | :--- |
| `/api/users/autocomplete` | `GET` | Sugestões por nome/e-mail (usado na busca "Por pessoa") | `/api/v2/users/search` |
| `/api/users/search` | `GET` | Busca avançada por matrícula, e-mail ou UUID | `/api/v2/users/search` |
| `/api/users/{id}/reactivate` | `POST` | Reativa conta desativada | `/api/v2/users/{userId}` |
| `/api/users/{id}/queues` | `GET` | Filas em que o usuário está | `/api/v2/users/{userId}/queues` |
| `/api/users/{id}/name` | `GET` | Lookup leve `{found, id, name}` — alimenta o cache de nomes da timeline de auditoria | `/api/v2/users/{userId}` (sem `expand`) |

**Queues / Groups / Roles / Divisions**

| Rota Interna | Método | Descrição | Endpoint Genesys Correspondente |
| :--- | :--- | :--- | :--- |
| `/api/queues/user/{id}/all` | `DELETE` | Remove usuário de todas as filas | `/api/v2/routing/queues/...` |
| `/api/queues/{queue_id}/member/{user_id}` | `DELETE` | Remove usuário de uma fila específica | `/api/v2/routing/queues/{id}/members` |
| `/api/groups` | `GET` | Mapa `{id, name}` de todos os grupos da org (paginado, cache bulk no frontend) | `/api/v2/groups` |
| `/api/groups/{group_id}/members/{user_id}` | `DELETE` | Remove usuário de um grupo | `/api/v2/groups/{groupId}/members` |
| `/api/roles` | `GET` | Mapa `{id, name}` de todas as roles da org (paginado) | `/api/v2/authorization/roles` |
| `/api/divisions` | `GET` | Mapa `{id, name}` de todas as divisões da org (paginado) | `/api/v2/authorization/divisions` |

**Migration** (`routes/migration.py`, prefixo `/migration`)

| Rota Interna | Método | Descrição |
| :--- | :--- | :--- |
| `/api/migration/run` | `POST` | Fluxo completo de migração (Divisão + Role + Grupo) num usuário |

**Auditoria** (`routes/audits.py`, prefixo `/audits`) — proxy assíncrono da
Platform Audit API da Genesys (criar consulta → poll → paginar por cursor).

| Rota Interna | Método | Descrição |
| :--- | :--- | :--- |
| `/api/audits/services` | `GET` | Árvore serviço → entidade → ação auditável na org |
| `/api/audits/search` | `POST` | Cria a consulta, aguarda concluir, devolve a 1ª página |
| `/api/audits/search/deep` | `POST` | Varredura multi-página filtrando por UUID no backend (para achar "fulano foi adicionado à fila/role X", onde o alvo do evento não é a pessoa) |
| `/api/audits/search/{tid}/results` | `GET` | Próximas páginas via cursor |

Detalhes de comportamento por serviço da Audit API (formatos de UUID
embutidos em `propertyChanges`, quirks confirmados por serviço, etc.) ficam
em [`refencia retornos/DICIONARIO-AUDITORIA.md`](../refencia%20retornos/DICIONARIO-AUDITORIA.md).

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
