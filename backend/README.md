# ⚙️ Genesys Manager: Backend Core

O backend do Genesys Manager é uma API assíncrona construída em **Python 3.11** utilizando o framework **FastAPI**. Ele atua como um middleware seguro entre o frontend e a API oficial do Genesys Cloud.

---

## 🛠️ Stack Tecnológica

- **FastAPI**: Framework web moderno, de alto desempenho e com suporte nativo a `async/await`.
- **SQLAlchemy & PostgreSQL**: ORM e banco de dados relacional para persistência de tickets e base de conhecimento.
- **Psycopg2**: Driver PostgreSQL de alta performance para operações relacionais e pipeline ETL.
- **Pydantic Settings**: Gestão de variáveis de ambiente e validação de configurações.
- **Httpx**: Cliente HTTP assíncrono para integração com a API da Genesys e Cloudflare.
- **Python-jose**: Gerenciamento de tokens JWT (assinatura e validação).
- **Passlib (Bcrypt)**: Ainda usado só para popular o campo legado `hashed_password`
  em `users.json` no cadastro admin — **login não usa senha** (magic link).
- **Resend**: Envio do e-mail com o magic link (`email_service.py`).

---

## 🔐 Autenticação Dual

Camada dupla: sessão local (operadores) + proxy Genesys (credenciais de org).

### 1. Login local — magic link (passwordless)

1. Operador informa e-mail em `POST /auth/login`.
2. Domínio deve ser `@{ALLOWED_EMAIL_DOMAIN}` (padrão: `claro.com.br`).
3. O e-mail **precisa** existir e estar `active` em `users.json`. Ter só o domínio **não** basta.
4. Se o usuário existir, o backend gera um token com TTL de 10 minutos (hash SHA-256 em
   `auth_tokens.json`, `MAGIC_LINK_EXPIRE_MINUTES` = 10 — distinto da sessão JWT),
   envia o link via **Resend** (`{APP_BASE_URL}/api/auth/verify?token=...`) e
   responde com mensagem genérica (não revela se o e-mail existe).
5. O clique abre `GET /auth/verify?token=...`, que valida e redireciona (302) para o frontend
   `/login?token=...` ou `/login?error=invalid_link` (sem JSON cru de erro no browser).
6. A SPA (`LoginView`) monta com `?token=`, mostra “Entrando…” e dispara
   automaticamente `POST /auth/verify` com `{ "token": "..." }` — emite JWT e seta o cookie `access_token`
   (HttpOnly; Secure + SameSite=None em produção). Sem botão de confirmação.
   O link permanece válido para múltiplos acessos durante toda a sua janela de 10 minutos.
7. Sessão idle **48h** (`JWT_EXPIRE_MINUTES=2880`), renovada a cada request
   autenticado (sliding session).

#### Validade por 10 minutos e resiliência a scanners

O link permanece ativo por **10 minutos**, independente de quantos acessos ou cliques
ocorram nesse intervalo:

| Método | Comportamento |
| :--- | :--- |
| `GET /auth/verify` | Validação rápida → redirect para `/login?token=...` ou `?error=invalid_link` |
| `HEAD /auth/verify` | Resposta sem corpo (204 se utilizável, 404 caso contrário) |
| `POST /auth/verify` | Autentica, seta cookie JWT, devolve JSON (`Acesso autorizado.` + user). Funciona múltiplas vezes dentro dos 10 min |

Arquivos sensíveis (gitignored): `users.json`, `auth_tokens.json`, `.env`.
No Docker Compose, `users.json` e `auth_tokens.json` têm bind mount — sobrevivem
a `docker compose up --force-recreate`.

### 2. Proxy Genesys (OAuth2 Client Credentials)

- Credenciais `GENESYS_CLIENT_*` ficam **só no backend**.
- O token da Genesys **nunca** vai ao frontend; cache em memória com renovação.

### Admin — usuários da plataforma

Rotas sob `/auth/users*` exigem `role: admin` (`require_admin`).

| Ação | Endpoint | UI |
| :--- | :--- | :--- |
| Listar | `GET /auth/users` | `/admin/usuarios` |
| Cadastrar | `POST /auth/users` (`email`, `full_name`, `role`, `username` opcional) | formulário na mesma tela |
| Excluir | `DELETE /auth/users/{username}` | confirmação na tabela (busca client-side) |

Validação no create: domínio permitido, e-mail único, username único (ou derivado
da parte local do e-mail). `hashed_password` aleatório só mantém o schema JSON —
login é por magic link. Exclusão: admin only; 400 se tentar excluir a si mesmo
ou o último administrador restante.

### Segurança

Controles atuais:

- Secrets e stores locais fora do git (`.env`, `users.json`, `auth_tokens.json`)
- Login com resposta genérica 200 quando o e-mail não está cadastrado
- Magic tokens hashed, single-use, TTL curto
- Cookie HttpOnly; Secure em produção; logout limpa com os mesmos atributos do set
- Sem API keys no frontend
- Admin gated por role

Riscos residuais (aceitáveis neste estágio):

- Falha de envio Resend para e-mail **cadastrado** pode retornar **502** (enumeração
  parcial sob falha de infra; caminho feliz permanece genérico)
- `users.json` / `auth_tokens.json` em arquivo local (sem DB) — permissões de FS importam
- JWT sem denylist: logout só apaga o cookie; o JWT antigo vale até expirar se for reenviado

---

## 🔌 Registro de Endpoints (API Registry)

Prefixo externo `/api/*` (o Nginx do frontend estripa esse prefixo antes de
encaminhar pro backend — ver `frontend/nginx.conf`). Endpoints internos
exigem cookie JWT válido (`Depends(get_current_user)`), exceto `/auth/login`
e `/auth/verify`.

**Auth** (`routes/auth_routes.py`, prefixo `/auth`)

| Rota Interna | Método | Descrição |
| :--- | :--- | :--- |
| `/api/auth/login` | `POST` | Solicita magic link (resposta genérica) |
| `/api/auth/verify` | `GET` | Landing: *peek* do token (não consome); 302 → `/login?token=...` ou `/login?error=invalid_link` |
| `/api/auth/verify` | `HEAD` | Scanners (Safe Links): 204/404 sem consumir |
| `/api/auth/verify` | `POST` | Consome token (`{ "token" }`), seta cookie JWT, JSON de sessão |
| `/api/auth/logout` | `POST` | Remove cookie de sessão |
| `/api/auth/me` | `GET` | Sessão atual (boot do frontend; renova sliding) |
| `/api/auth/users` | `GET` | Lista usuários locais (admin) |
| `/api/auth/users` | `POST` | Cadastra usuário local (admin) |
| `/api/auth/users/{username}` | `DELETE` | Remove usuário local (admin; não self / não último admin) |

**Users** (`routes/users.py`, prefixo `/users`)

| Rota Interna | Método | Descrição | Endpoint Genesys Correspondente |
| :--- | :--- | :--- | :--- |
| `/api/users/autocomplete` | `GET` | Sugestões por nome/e-mail (usado na busca "Por pessoa") | `/api/v2/users/search` |
| `/api/users/search` | `GET` | Busca avançada por matrícula, e-mail ou UUID | `/api/v2/users/search` |
| `/api/users/{id}/reactivate` | `POST` | Reativa conta desativada | `/api/v2/users/{userId}` |
| `/api/users/{id}/queues` | `GET` | Filas em que o usuário está | `/api/v2/users/{userId}/queues` |
| `/api/users/{id}/name` | `GET` | Lookup leve `{found, id, name}` — alimenta o cache de nomes da timeline de auditoria | `/api/v2/users/{userId}` (sem `expand`) |
| `/api/users/{id}/telephony` | `GET` | Diagnóstico completo de telefonia, ramal e telefone base (WebRTC / SIP), validando os 3 pilares de integridade | `/api/v2/users/{userId}?expand=station,telephony`<br>`/api/v2/stations/{stationId}`<br>`/api/v2/telephony/providers/edges/phones` |


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

**Analytics** (`routes/analytics.py` + `services/user_presence.py`, prefixo `/analytics`) —
proxy síncrono da User Status Detail query (presença). Scope OAuth:
`analytics:readonly`.

| Rota Interna | Método | Descrição | Endpoint Genesys Correspondente |
| :--- | :--- | :--- | :--- |
| `/api/analytics/users/{id}/presence` | `GET` | Presença (`primaryPresence`) do dia civil BR (`?date=YYYY-MM-DD`) | `POST /api/v2/analytics/users/details/query` |

**Auditoria** (`routes/audits.py` + `services/user_audit.py`, prefixo `/audits`) —
proxy assíncrono da Platform Audit API da Genesys e consolidação focada por
usuário. A tela principal do frontend usa a rota SSE **`POST /audits/user-changes/stream`**; as
rotas `/search` e `/search/deep` e o antigo `/user-changes` síncrono permanecem como API de baixo nível.

| Rota Interna | Método | Descrição |
| :--- | :--- | :--- |
| `/api/audits/user-changes/stream` | `POST` | **Fluxo principal:** streaming via Server-Sent Events (SSE) do progresso e resultado das alterações de um usuário no intervalo (ChangeCards). Default: só divisão (Directory). Deep por categoria via `deep_categories` (`queue` / `role` / `group`) |
| `/api/audits/user-changes` | `POST` | **Endpoint Antigo (Síncrono):** equivalente ao stream, mas mantendo a conexão bloqueada (propício a timeouts no proxy). |
| `/api/audits/services` | `GET` | Árvore serviço → entidade → ação auditável na org |
| `/api/audits/search` | `POST` | Cria a consulta, aguarda concluir, devolve a 1ª página |
| `/api/audits/search/deep` | `POST` | Varredura multi-página filtrando por UUID no backend (API genérica; o fluxo por pessoa usa a lógica equivalente em `user_audit`) |
| `/api/audits/search/{tid}/results` | `GET` | Próximas páginas via cursor |

### `POST /audits/user-changes/stream` — contrato

**Request** (`UserChangesRequest`):

| Campo | Tipo | Descrição |
| :--- | :--- | :--- |
| `user` | string | E-mail ou UUID do usuário |
| `interval_start` | string | ISO-8601 (início do intervalo) |
| `interval_end` | string | ISO-8601 (fim; deve ser posterior a `start`) |
| `deep_categories` | string[] | `"queue"` \| `"role"` \| `"group"`. Default `[]` = só Directory/divisão. Com categorias, roda deep **só** nelas (**sem** Directory) |
| `deep_search` | bool | **Compat.** Se `true` e `deep_categories` vazio/ausente, equivale a `["queue","role","group"]` **+** Directory. Preferir `deep_categories` |

**Modos de busca:**

| Pedido | Directory (divisão) | Deep (Groups / Role / Queue) |
| :--- | :--- | :--- |
| `deep_categories: []` (default) | Sim | Não |
| `deep_categories: ["queue"]` (ou `role` / `group`) | Não | Só as categorias pedidas |
| `deep_search: true` sem lista explícita | Sim | As três categorias |

Mapeamento categoria → serviço Genesys: `queue` → ContactCenter (`Queue`), `role` → PeoplePermissions (`Role`), `group` → Groups (`DirectoryGroup`). Deep filtra o UUID do usuário **localmente** no corpo do evento (a Platform Audit API não filtra esses serviços direto pela pessoa).

**Limites** (em `services/user_audit.py`):

- Intervalo máximo: **30 dias** para busca base (limite da Platform Audit API) e **48 horas** em modo Deep para garantir estabilidade.
- Deep: `pageSize` **250**, no máximo **10 páginas** por janela (~2.500 eventos/janela)
- Deep parte o intervalo em **janelas diárias** (`DEEP_CHUNK_DAYS = 1`); se uma janela truncar, **bisecta** até ~1h (`DEEP_MIN_CHUNK_SECONDS`). Pause `0.4s` entre chunks
- `meta.truncated` / `meta.truncated_by_service` só ficam true se alguma janela ainda estourar o teto após a bisecção
- Pool de consultas: sequencial (`QUERY_POOL_SIZE = 1`) para evitar 429

**Response:**

```json
{
  "user": { "id": "...", "name": "...", "email": "..." },
  "interval": { "start": "...", "end": "..." },
  "changes": [ /* ChangeCard[] */ ],
  "meta": {
    "deep_categories": [],
    "deep_search": false,
    "include_directory": true,
    "truncated": false,
    "truncated_by_service": {
      "Directory": false,
      "Groups": false,
      "PeoplePermissions": false,
      "ContactCenter": false
    },
    "scanned_by_service": {
      "Directory": { "scanned": 0, "matched": 0, "truncated": false },
      "Groups": { "omitted": true, "reason": "deep_search_off" },
      "PeoplePermissions": { "omitted": true, "reason": "deep_search_off" },
      "ContactCenter": { "omitted": true, "reason": "deep_search_off" }
    }
  }
}
```

Campos de `meta`:

| Campo | Significado |
| :--- | :--- |
| `deep_categories` | Categorias deep efetivamente pedidas/normalizadas |
| `deep_search` | Compat: `true` se alguma categoria deep rodou |
| `include_directory` | Se a consulta Directory (divisão) entrou nesta resposta |
| `truncated` | `true` se qualquer serviço truncou |
| `truncated_by_service` | Truncamento por serviço (`Directory`, `Groups`, `PeoplePermissions`, `ContactCenter`) |
| `scanned_by_service` | Contadores `{ scanned, matched, truncated }` ou `{ omitted: true, reason }` |
| `errors` | (opcional) falhas por serviço quando a consulta levanta exceção |

Razões de omissão em `scanned_by_service`: `deep_search_off` (nenhuma deep pedida), `not_requested` (outras categorias deep pedidas, esta não), `not_in_request` (Directory omitido porque só deep foi pedida).

Cada **ChangeCard** tem `category` (`division` | `queue` | `role` | `group`),
`action` (`add` | `remove` | `update` | `activate` | `deactivate`), `resource`,
`before` / `after`, `changed_by` e `event_date`.

Detalhes de comportamento por serviço da Audit API (formatos de UUID
embutidos em `propertyChanges`, quirks confirmados por serviço, etc.) ficam
em [`refencia_retornos/DICIONARIO-AUDITORIA.md`](../refencia_retornos/DICIONARIO-AUDITORIA.md).

**Tickets & Base de Conhecimento** (`routes/tickets.py`, prefixo `/tickets`) —
Gestão de chamados técnicos enriquecidos, curadoria de classificação e agregação de métricas para a Base de Conhecimento (FAQ).

| Rota Interna | Método | Descrição |
| :--- | :--- | :--- |
| `/api/tickets/` | `GET` | Lista tickets enriquecidos com suporte a paginação (`limit`, `offset`) e filtro por `status` |
| `/api/tickets/knowledge-base` | `GET` | Métricas agregadas (total de tickets, categorizados como FAQ) e distribuição por categoria |
| `/api/tickets/{external_id}` | `GET` | Detalhes completos de um ticket por ID externo |
| `/api/tickets/{external_id}` | `PUT` | Permite operadores revisarem/atualizarem classificação e status de FAQ |
| `/api/tickets/sync` | `POST` | Disparo manual de sincronização/carga |

---

## 🐘 Banco de Dados PostgreSQL & Pipeline ETL

O backend utiliza o **PostgreSQL 15** para armazenamento persistente de tickets e conhecimento acumulado.

- **ORM & Models:** Estrutura gerenciada via **SQLAlchemy** em `models.py` (`Ticket`, `Base`) com engine e sessões em `database.py`.
- **Pipeline Incremental SQLite ➔ PostgreSQL:**
  - O script [`etl_sync_sqlite_to_postgres.py`](etl_sync_sqlite_to_postgres.py) atua como worker contínuo (loop de 10s).
  - Executa na máquina de origem (onde reside o SQLite legado), conectando-se ao PostgreSQL via túnel seguro Cloudflare Zero Trust (`postgres.projetoathos.com.br`).
  - Utiliza controle de **Watermark** (`MAX(id)` e `MAX(updated_at)`) e **UPSERT** (`ON CONFLICT (external_id) DO UPDATE`) para garantir idempotência e sincronização de modificações.
- **Documentação Operacional:**
  - Guia de arquitetura e infraestrutura: [`docs/SINCRONIZACAO_SQLITE_POSTGRES.md`](../docs/SINCRONIZACAO_SQLITE_POSTGRES.md)
  - Guia pronto para envio à máquina de origem: [`INSTRUCOES_ORIGEM_SYNC.md`](../INSTRUCOES_ORIGEM_SYNC.md)

---

## ☁️ Integração Cloudflare (Zero Trust)

O backend possui um client integrado em `services/cloudflare_service.py` configurado para interagir com a API v4 da Cloudflare. Ele gerencia as configurações sem expor credenciais ao frontend. Atualmente suporta:
- Verificação de validade de Tokens
- Listagem e detalhes de Túneis Zero Trust (`cfd_tunnel`)
- Leitura de registros DNS

As chaves ficam isoladas no backend, exigindo no `.env`:
`CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` e `CLOUDFLARE_ZONE_ID`.

---

## 📁 Estrutura de Diretórios

```text
├── routes/                         # Definição modular de rotas (APIRouter)
│   ├── auth_routes.py              # Login magic link e gestão de usuários
│   ├── users.py                    # Busca, autocomplete e diagnóstico de telefonia
│   ├── queues.py                   # Gestão de filas, grupos e divisões
│   ├── audits.py                   # Proxy SSE e histórico de auditoria
│   ├── analytics.py                # Presença de operadores
│   ├── migration.py                # Fluxo automatizado de migração
│   └── tickets.py                  # Endpoints de tickets e FAQ
├── services/                       # Orquestração de domínio (auditoria, presença, etc.)
│   ├── user_audit.py               # Motor da trilha de auditoria SSE
│   ├── user_presence.py            # Consulta de presença e timeline
│   ├── db_tickets.py               # Camada de acesso a dados (PostgreSQL)
│   └── cloudflare_service.py       # Client da API Cloudflare Zero Trust
├── models.py                       # Modelos ORM SQLAlchemy (Ticket)
├── database.py                     # Configuração de Engine e Session do PostgreSQL
├── etl_sync_sqlite_to_postgres.py  # Worker contínuo de sincronização (10s)
├── migrate_sqlite_to_postgres.py   # Script de carga única local SQLite -> Postgres
├── auth.py                         # OAuth2 Client Credentials Genesys
├── auth_local.py                   # JWT, cookie, RBAC local (sem login por senha)
├── email_service.py                # Envio de magic link (Resend)
├── token_store.py                  # Tokens magic link (hash em auth_tokens.json)
├── config.py                       # Settings / env (Pydantic)
├── main.py                         # Entrada e middlewares FastAPI
├── requirements.txt                # Dependências da aplicação
├── requirements-etl.txt            # Dependências do worker ETL
├── .env.example                    # Placeholders de variáveis de ambiente
├── users.json                      # Usuários locais (gitignored)
└── auth_tokens.json                # Hashes de magic link (gitignored)
```

CLI histórica de hash de senha: [`docs/arquivo/create_user.py`](../docs/arquivo/create_user.py)
(não usada no fluxo atual — cadastro via `POST /auth/users`).

---

## 🚀 Como Rodar Localmente (Desenvolvimento)

Stack completa via Compose na raiz: `docker-compose up -d --build`
(frontend em `http://localhost:8082`, postgres na porta `5432`). Só o backend:

1.  **Crie um ambiente virtual:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # Linux/Mac
    ```

2.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure o `.env`:**
    ```bash
    cp .env.example .env
    # Preencha JWT_SECRET_KEY, GENESYS_*, RESEND_*, APP_BASE_URL, CLOUDFLARE_*, DATABASE_URL
    ```

4.  **Inicie o servidor:**
    ```bash
    uvicorn main:app --reload
    ```
    *API em `http://localhost:8000`.*

---

**Camada de Segurança:** Rotas autenticadas exigem JWT no cookie (exceto
`/auth/login` e `/auth/verify`). Gestão de usuários locais exige `role: admin`.

