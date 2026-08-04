# 🚀 Genesys Manager: Frontend Dashboard

A interface do Genesys Manager é uma Single Page Application (SPA) construída com **Vue 3** e **Vite**, focada em velocidade operacional e experiência do usuário clara para processos de gestão.

---

## 🛠️ Stack Tecnológica

- **Vue 3 (Composition API)**: Framework reativo com a sintaxe `<script setup>` para código limpo e modular.
- **Vite**: Build tool de última geração que permite HMR (Hot Module Replacement) instantâneo.
- **Tailwind CSS v3**: Framework CSS utility-first que permite a criação de interfaces customizadas com zero CSS escrito à mão.
- **Vue Router**: Motor de navegação com suporte a *Navigation Guards* para proteção de rotas.
- **Vitest**: Framework de testes unitários focado em componentes Vue.

---

## 🔐 Autenticação no frontend

Login é **passwordless** (magic link). O frontend **não** guarda senha nem API keys
(`RESEND_*`, Genesys OAuth, `JWT_SECRET_KEY` ficam só no backend).

1. `LoginView.vue` chama `requestLoginLink(email)` → `POST /auth/login`.
2. Mensagem genérica: “verifique seu e-mail” (link válido ~10 min).
3. O clique no link bate no backend (`/api/auth/verify`), que seta o cookie
   HttpOnly e redireciona para a SPA.
4. No boot, `useAuth.checkAuth()` usa `GET /auth/me` (cookie `credentials: include`).
5. Sessão idle **48h** (sliding no backend a cada request autenticado).
6. Logout: `POST /auth/logout` + limpa estado local.

Requisitos de acesso: e-mail `@claro.com.br` **e** cadastro prévio em `users.json`
(admin cria na tela ou edição manual no backend). Domínio sozinho não basta.

### Admin — usuários da ferramenta

Rota `/admin/usuarios` (`AdminUsersView.vue`), guard `requiresAdmin`
(`user.role === 'admin'`). Backend reforça com `require_admin`.

| Ação | API (`api/auth.js`) | Estado atual |
| :--- | :--- | :--- |
| Listar | `listLocalUsers()` → `GET /auth/users` | Disponível |
| Cadastrar | `createLocalUser(...)` → `POST /auth/users` | Formulário na tela |
| Buscar | filtro client-side (nome / e-mail) | Barra de busca na lista |
| Excluir | `deleteLocalUser(username)` → `DELETE /auth/users/{username}` | Confirmação; não permite excluir a si mesmo |

Variável de ambiente do frontend (única necessária):

```bash
cp .env.example .env
# VITE_API_BASE_URL=http://localhost:8000   # dev
# Em Docker/produção: /api (ver .env.production)
```

---

## 🧠 Arquitetura de Estado e Lógica

O frontend utiliza o padrão de **Composables** para encapsular lógica de negócio reutilizável e estado global reativo:

1.  **useAuth.js**:
    - Estado do usuário (`user`, `isAuthenticated`) e `logout`.
    - Boot via `/auth/me` (sessão por cookie HttpOnly).
    - Pedido de magic link fica em `LoginView` + `api/auth.js` (`requestLoginLink`).

2.  **useToast.js**:
    - Sistema de notificações globais.
    - Permite disparar avisos de `sucesso`, `erro` ou `loading` de qualquer parte da aplicação.

3.  **useEntityNames.js** (e o alias `useUserNames.js`):
    - Cache global UUID → nome, compartilhado entre telas, com duas estratégias:
      resolução **per-UUID sob demanda** (usuários, pool de concorrência + teto
      de lookups) e **mapa bulk** (roles/grupos/divisões, busca única por
      sessão via `ensureBulk()`).

4.  **Security (Navigation Guards)**:
    - Todas as rotas (exceto `/login`) exigem autenticação.
    - Rotas com `meta.requiresAdmin` exigem `role === 'admin'`.

---

## 🔎 Módulo de Auditoria

`AuditView.vue` (rota `/auditoria` — **Trilha de Auditoria**) é o fluxo
principal: selecionar **pessoa** + **período** e escolher o tipo de busca.
Chama `POST /audits/user-changes` via `getUserChanges` em `api/audits.js` e
renderiza ChangeCards normalizados pelo backend.

Fluxo da UI:

1. **Pessoa** — autocomplete (nome) ou resolução por e-mail/UUID
   (`AuditSearchBar.vue`)
2. **Período** — presets 24h / 7 dias / 30 dias ou `datetime-local`
3. **Como funciona** — bloco na barra explicando o que cada botão retorna
   (divisão vs filas / roles / grupos) e por que deep é mais lento
4. **Pesquisar** — só **divisão** (`deep_categories: []`); substitui a lista
5. **Buscar filas / Buscar roles / Buscar grupos** — botões separados; cada um
   chama `deep_categories: ["queue"|"role"|"group"]` e **merge** os cards
   novos na lista já existente (não apaga divisão nem outras categorias)
6. **Cancelar** — aparece durante loading; aborta a requisição em voo via
   `AbortController` (toast “Busca cancelada.”)
7. **Resultados** — `UserChangesList.vue`: chips por categoria; cards
   **narrativos** para membership (grupo/role/fila add|remove|activate|deactivate);
   layout **Antes / Depois** só para divisão (e updates com diff)
8. **Empty states por categoria** — mensagens distintas para divisão / filas /
   roles / grupos (HTTP 200 sem matches ≠ erro). Se a lista já tem cards de
   outra categoria, deep sem matches novos mostra banner + toast informativo
9. **Truncamento** — aviso âmbar na lista quando `meta.truncated` /
   `truncated_by_service` indica varredura parcial (~2.500 eventos/janela no
   backend); toast de warning na deep afetada

Componentes do fluxo atual:

| Arquivo | Papel |
| :--- | :--- |
| `views/AuditView.vue` | Orquestra busca base/deep, merge, cancelamento, empty por categoria e truncamento |
| `components/AuditSearchBar.vue` | Pessoa + período + “Como funciona” + Pesquisar + botões deep + Cancelar |
| `components/UserChangesList.vue` | Lista de ChangeCards + aviso de truncamento por categoria |
| `api/audits.js` | `getUserChanges(body, options)` — aceita `deep_categories` e `signal` (abort) |
| `api/http.js` | Em **504** / **408**, mensagem amigável de timeout (sugerindo intervalo menor na deep) |

Fluxos antigos da UI (toggle único de “busca profunda”, abas por filtros
dinâmicos, multi-serviço “o que fez / o que fizeram com ela”, timeline bruta)
**não são mais o fluxo principal**. Wrappers de baixo nível (`searchAudits`,
`deepSearchAudits`) ainda existem em `api/audits.js` (API genérica viva).
A UI antiga (`AuditTimeline`, `AuditTokens`, `auditFormat`) foi movida para
[`docs/arquivo/frontend-audit-legado/`](../docs/arquivo/frontend-audit-legado/).

Comportamento empírico dos serviços da Audit API continua em
[`refencia_retornos/DICIONARIO-AUDITORIA.md`](../refencia_retornos/DICIONARIO-AUDITORIA.md).

---

## 🏗️ Fluxo de Produção (Docker + Nginx)

O deploy do frontend é realizado em **Multi-stage Build**:
1.  **Stage 1 (Build):** Usa uma imagem Node.js para compilar e otimizar os ativos (JS, CSS, HTML).
2.  **Stage 2 (Serve):** Os arquivos estáticos gerados são copiados para uma imagem **NGINX** leve.
3.  **NGINX Proxy:** Configurado para servir a SPA e encaminhar requisições `/api/*` para o container de backend, resolvendo problemas de CORS de forma nativa.
4.  **Timeouts do proxy** (`nginx.conf` → `location /api/`): `proxy_read_timeout` e `proxy_send_timeout` em **300s** (deep search de auditoria pode levar minutos; o default de 60s gerava HTTP 504). Header de diagnóstico `X-Proxy-Read-Timeout: 300`.

---

## 📁 Estrutura de Diretórios

```text
├── src/
│   ├── api/            # Fetch wrappers (auth, genesys, audits) — sem secrets
│   ├── views/          # Login, AdminUsuários, Consulta (+ migração), Auditoria
│   ├── components/     # UI ativa (Search, UserChangesList, ConfirmDialog, …)
│   ├── composables/    # useAuth, useToast, useEntityNames
│   ├── router/         # Rotas + guards (auth / admin)
│   └── assets/         # Imagens e estilos globais
├── public/             # Arquivos estáticos puros
├── .env.example        # Só VITE_API_BASE_URL
└── nginx.conf          # Produção + proxy /api → backend
```

---

## 🚀 Como Rodar Localmente (Desenvolvimento)

Compose (raiz do repo): `docker-compose up -d --build` → `http://localhost:8082`.

Só o dashboard (Vite), com o backend em `:8000`:

1.  **Instale as dependências:**
    ```bash
    npm install
    ```

2.  **Configure o `.env`:**
    ```bash
    cp .env.example .env
    ```

3.  **Inicie o servidor de desenvolvimento:**
    ```bash
    npm run dev
    ```
    *Dashboard em `http://localhost:5173`.*

---

**Design System:** Paleta em tons de **Teal** e **Dark Slate**, pensada para uso prolongado.
