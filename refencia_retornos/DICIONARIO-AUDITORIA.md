# Dicionário de Dados — Platform Audit API (Genesys Cloud)

Cruzamento entre a **documentação oficial** da Platform Audit API (Swagger público
`api.mypurecloud.com/api/v2/docs/swagger`, definições `AuditQuery*` e
`AuditLogMessage`) e o **comportamento real observado na org** (`sae1.pure.cloud`),
medido pelas amostras em `amostras/` geradas por `explorar_auditoria.py`:

| Amostra | Eventos | Período coletado |
|---|---|---|
| `servicemapping_raw.json` | 58 serviços | mapa completo da org |
| `ContactCenter_raw.json` / `_perfil.txt` | 100 | últimas ~19h |
| `Directory_raw.json` / `_perfil.txt` | 60 | últimas ~3h |
| `PeoplePermissions_raw.json` / `_perfil.txt` | 100 | últimas ~18h |
| `Groups_raw.json` / `_perfil.txt` | 300 | últimos 30 dias |

### Referências oficiais usadas neste cruzamento

| Documento | Link |
|---|---|
| Audit APIs — visão geral | https://developer.genesys.cloud/platform/audit/ |
| Audits Query (criação da consulta) | https://developer.genesys.cloud/platform/audit/auditquerycreate |
| Cursor and Page Size (paginação) | https://developer.genesys.cloud/platform/audit/usecursor |
| Action Catalog (serviços/entidades/ações da plataforma) | https://developer.genesys.cloud/platform/audit/actioncatalog |
| Sample Usage | https://developer.genesys.cloud/platform/audit/sampleusage |
| REST API v2 reference — domínio `audits` (gerado do Swagger) | https://developer.genesys.cloud/api/rest/v2/audits/ |
| Swagger público (schema bruto, usado para os dicionários abaixo) | https://api.mypurecloud.com/api/v2/docs/swagger |
| About the Audit Viewer (UI administrativa, não a API) | https://help.genesys.cloud/articles/about-the-audit-log-viewer/ |
| View audit events (UI administrativa) | https://help.genesys.cloud/articles/view-audit-events/ |

> **Nota:** o Developer Center (`developer.genesys.cloud`) é uma SPA — os links
> acima levam à página certa, mas o conteúdo é renderizado em JS (não dá para
> extrair automaticamente via scraping simples). Os dicionários de campos
> abaixo foram extraídos direto do **Swagger público**, que é a fonte
> estruturada e verificável.

> **Atenção:** os exemplos abaixo têm UUIDs, IPs e nomes reais **mascarados**
> (`<uuid-...>`) — os valores crus estão nos `*_raw.json`, que são gitignored
> por conterem PII.

---

## 1. Como a API funciona (fluxo assíncrono)

A Platform Audit API não devolve eventos numa chamada única: você **cria uma
consulta**, ela roda no lado da Genesys, e você **pagina o resultado por cursor**.

```
POST /api/v2/audits/query                      → cria a consulta, devolve transactionId + state
GET  /api/v2/audits/query/{transactionId}      → polling do estado
GET  /api/v2/audits/query/{tid}/results        → páginas de eventos (cursor)
GET  /api/v2/audits/query/servicemapping       → descobre o que é auditável na org
```

Estados possíveis da consulta (oficial): `Queued` → `Running` →
`Succeeded` | `Failed` | `Cancelled`. Só há resultado quando `Succeeded`.

**Permissão exigida em todos os endpoints:** `audits:audit:view`
(confirmado concedida na integração — nenhum 403 durante a exploração).

Existe também a variante **realtime** (`POST /api/v2/audits/query/realtime`,
síncrona, paginada por `pageNumber`), mas a própria doc oficial avisa que ela
**só cobre ~14 dias de histórico para certos serviços** — por isso o projeto usa
o fluxo assíncrono, que cobre o histórico retido completo. Há ainda
`POST /audits/query/realtime/related`, que devolve todos os audits gerados pela
mesma ação de um audit dado (útil porque uma ação única pode gerar N eventos).

### Mapeamento para as rotas do projeto

| Rota do backend (`backend/routes/audits.py`) | Endpoint Genesys consumido |
|---|---|
| `GET /audits/services` | `GET /api/v2/audits/query/servicemapping` |
| `POST /audits/search` | `POST /api/v2/audits/query` + polling + 1ª página de `/results` |
| `POST /audits/search/deep` | idem, varrendo até `max_pages` páginas e filtrando por UUID no backend |
| `GET /audits/search/{tid}/results` | `GET /api/v2/audits/query/{tid}/results` (cursor) |

---

## 2. Endpoints consultados — descrição e dicionário

### 2.1 `GET /api/v2/audits/query/servicemapping`

📖 [Action Catalog](https://developer.genesys.cloud/platform/audit/actioncatalog) · [REST reference (audits)](https://developer.genesys.cloud/api/rest/v2/audits/)

**O que é:** devolve a árvore `serviço → entidades → ações` auditáveis **na sua
org** — é o "cardápio" de valores válidos para `serviceName`, `EntityType` e
`Action` da consulta. O frontend usa isso para popular os selects de filtro.

**Retorno (`AuditQueryServiceMapping`):**

| Campo | Tipo | Descrição |
|---|---|---|
| `services[]` | array | Lista de serviços auditáveis |
| `services[].name` | string | Nome do serviço (valor a usar em `serviceName`) |
| `services[].entities[]` | array | Entidades auditáveis do serviço |
| `services[].entities[].name` | string | Nome da entidade (valor a usar no filtro `EntityType`) |
| `services[].entities[].actions[]` | array\<string\> | Ações auditáveis (valores do filtro `Action`) |

> **Nota de compatibilidade:** versões da API podem devolver
> `serviceName`/`entityTypes`/`entityType` em vez de `name`/`entities`/`name`.
> Na org real veio `name`/`entities`; o backend normaliza os dois formatos.

**Observado na org:** 58 serviços. Os 4 com eventos reais confirmados (lista
curada da UI): `PeoplePermissions`, `ContactCenter`, `Directory`, `Groups`.
Ações mais comuns no mapa inteiro: `Update`, `Delete`, `Create` (~220x cada);
ações de membership (`MemberAdd`/`MemberUpdate`/`MemberRemove`) existem só em
`Role` (PeoplePermissions) e `Queue` (ContactCenter).

Árvore dos serviços-chave observada na org:

```
PeoplePermissions
 ├─ Role: Create, Update, LicenseUpdate, MemberAdd, MemberUpdate, MemberRemove
 ├─ AuthUser: Authenticate, ChangePassword, AuthenticationFailed
 ├─ UserSamlAuthentication: Authenticate, AuthenticationFailed, SingleLogout, ...
 ├─ OAuthClient: Create, Update, Delete
 └─ (RoleSettings, Policy, MFAVerifier, IdentityProvider, AccessToken, ...)

ContactCenter
 ├─ Queue: Create, Update, Delete, MemberAdd, MemberUpdate, MemberRemove,
 │         WrapupCodeAdd, WrapupCodeRemove
 ├─ WrapupCode: Create, Update, Delete
 └─ (AgentRoutingInfo, ConversationAttributes, RoutingUtilizationTag, ...)

Directory
 ├─ User: Create, Update, Delete
 └─ Organization: Create, Update, Delete

Groups
 ├─ SkillGroup / DirectoryGroup / Team / SkillGroupDefinition: Create, Update, Delete
```

---

### 2.2 `POST /api/v2/audits/query`

📖 [Audits Query](https://developer.genesys.cloud/platform/audit/auditquerycreate) · [Sample Usage](https://developer.genesys.cloud/platform/audit/sampleusage) · [REST reference (audits)](https://developer.genesys.cloud/api/rest/v2/audits/)

**O que é:** cria a execução assíncrona da consulta de auditoria. Devolve o
`transactionId` para polling e paginação.

**Corpo da requisição (`AuditQueryRequest`):**

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `interval` | string | **sim** | Intervalo ISO-8601: `YYYY-MM-DDThh:mm:ssZ/YYYY-MM-DDThh:mm:ssZ` |
| `serviceName` | string | não* | Serviço a consultar (valores do `servicemapping`). *Na prática o projeto sempre envia. |
| `filters[]` | array | não | Filtros adicionais (AND entre eles) |
| `filters[].property` | enum | — | `UserId` \| `TrusteeOrganizationId` \| `ClientId` \| `Action` \| `EntityType` \| `EntityId` |
| `filters[].value` | string | — | Valor do filtro |
| `sort[]` | array | não | Ordenação |
| `sort[].name` | enum | — | Só existe `Timestamp` |
| `sort[].sortOrder` | enum | — | `ascending` \| `descending` (a org aceita também `asc`/`desc`) |

**Semântica dos filtros nativos (importante para investigação):**

- `UserId` → eventos em que a pessoa é o **autor** ("o que fulano fez").
- `EntityId` → eventos em que a entidade é o **alvo** ("o que fizeram com X").
  Só funciona quando o alvo direto do evento é a própria pessoa/objeto — p.ex.
  `Directory/User Update`. **Não** encontra "fulano adicionado à fila/role",
  porque nesses eventos o alvo é a fila/role (daí a busca profunda do projeto).
- `ClientId` → eventos feitos por uma integração OAuth específica.
- `EntityType` / `Action` → restringem tipo de entidade e ação.

**Retorno (`AuditQueryExecutionStatusResponse`)** — o mesmo schema do endpoint
de status 2.3:

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | string | **transactionId** da execução — usado no polling e nos results |
| `state` | enum | `Queued` \| `Running` \| `Succeeded` \| `Failed` \| `Cancelled` |
| `startDate` | date-time | Quando a execução começou |
| `interval` | string | Eco do intervalo pedido |
| `serviceName` | string | Eco do serviço |
| `filters[]` / `sort[]` | array | Eco dos parâmetros |

---

### 2.3 `GET /api/v2/audits/query/{transactionId}`

📖 [REST reference (audits)](https://developer.genesys.cloud/api/rest/v2/audits/)

**O que é:** polling do estado da execução. Mesmo dicionário de retorno da 2.2.
O projeto faz polling a cada 2s, até 15 tentativas (~30s), e considera
terminal `Succeeded`/`Failed`/`Cancelled`.

---

### 2.4 `GET /api/v2/audits/query/{transactionId}/results`

📖 [Cursor and Page Size](https://developer.genesys.cloud/platform/audit/usecursor) · [REST reference (audits)](https://developer.genesys.cloud/api/rest/v2/audits/)

**O que é:** devolve os eventos em páginas, navegadas por **cursor opaco**
(não há `pageNumber` — só dá para andar para frente).

**Parâmetros de query:**

| Parâmetro | Tipo | Default | Descrição |
|---|---|---|---|
| `cursor` | string | — | Onde retomar (omitir na 1ª página) |
| `pageSize` | int | 25 | Máximo **500** |
| `expand` | array | — | Único valor válido: `user` — **preenche `user.name`** no evento (sem isso o autor vem só com `id`/`selfUri`) |
| `allowRedirect` | bool | false | Resultados muito grandes viram uma URL de download em vez de JSON inline |

**Retorno (`AuditQueryExecutionResultsResponse`):**

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | string | transactionId |
| `pageSize` | int | Tamanho da página |
| `cursor` | string | Cursor da **próxima** página; ausente na última |
| `entities[]` | array\<AuditLogMessage\> | Os eventos de auditoria (dicionário na seção 3) |

---

## 3. Dicionário do evento de auditoria (`AuditLogMessage`)

📖 Definição `AuditLogMessage` extraída do [Swagger público](https://api.mypurecloud.com/api/v2/docs/swagger) (sem página estática equivalente no Developer Center — os campos aparecem espalhados nos exemplos de [Sample Usage](https://developer.genesys.cloud/platform/audit/sampleusage)).

O objeto que interessa para estudo. Coluna "observado" = preenchimento real
medido nas 260 amostras da org (100 ContactCenter + 60 Directory + 100
PeoplePermissions).

| Campo | Tipo | Descrição oficial | Observado na org |
|---|---|---|---|
| `id` | string (uuid) | Id do evento de auditoria | 100% preenchido — bom para dedupe |
| `eventDate` | date-time | Quando o evento foi registrado (ISO-8601, UTC) | 100% — eixo da timeline |
| `serviceName` | string | Serviço que gerou o evento | 100% — ecoa o serviço consultado |
| `action` | string | Ação executada | 100% — `MemberAdd`, `MemberUpdate`, `MemberRemove`, `Update` nas amostras |
| `entityType` | string | Tipo da entidade impactada | 100% — `Queue`, `Role`, `User` nas amostras |
| `entity` | DomainEntityRef | Entidade **alvo** do evento | `entity.id` 100%; `entity.name` varia por serviço (ver §4) |
| `user` | DomainEntityRef | **Autor humano** do evento | `user.id` preenchido só em eventos `USER` (3–56%); `user.name` **só vem com `expand=user`** (as amostras foram coletadas sem expand → 0%) |
| `client` | AddressableEntityRef | Integração OAuth autora | `client.id` veio **sempre vazio** (`""`) nas amostras — chave presente, valor vazio |
| `userHomeOrgId` | string (uuid) | Org de origem do autor | Só presente quando `user.id` presente |
| `remoteIp` | array\<string\> | IPs que originaram/trataram a requisição | Preenchido apenas em eventos `USER` |
| `level` | enum | `USER` \| `SYSTEM` \| `GENESYS_INTERNAL` | `USER` = ação humana direta; `SYSTEM` = efeito em cascata/automação (44–97% dos eventos!) |
| `status` | enum | `SUCCESS` \| `FAILURE` \| `WARNING` | 100% `SUCCESS` nas amostras |
| `application` | string | Aplicação usada na ação | Veio sempre `""` nas amostras |
| `propertyChanges[]` | array\<PropertyChange\> | Propriedades alteradas (diff) | 100% em ContactCenter/Directory; **sempre vazio em PeoplePermissions** |
| `entityChanges[]` | array\<EntityChange\> | Entidades alteradas (diff em nível de entidade) | Sempre `[]` nas 260 amostras |
| `context` | object (map) | Contexto adicional, chaves variam por serviço | ContactCenter: `{entityId, auditType}`; Directory/PeoplePermissions: `{}` |
| `initiatingAction` | InitiatingAction | Audit que iniciou a transação (causa raiz) | Sempre `{}` nas amostras |
| `transactionInitiator` | boolean | Se este audit é o iniciador da transação | Sempre `false` nas amostras |
| `message` | MessageInfo | Mensagem descritiva do evento | Não veio em nenhuma amostra |

### Sub-objetos

**`DomainEntityRef`** (usado em `user` e `entity`):

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | string | UUID da entidade/usuário |
| `name` | string | Nome legível (em `user`, só com `expand=user`; em `entity`, depende do serviço) |
| `selfUri` | string | URI da API para buscar o objeto completo (ex.: `/api/v2/users/{id}`, `/api/v2/routing/queues/{id}`) — diz o **tipo real** do alvo |

**`AddressableEntityRef`** (`client`): apenas `id` + `selfUri`.

**`PropertyChange`** — o diff propriamente dito:

| Campo | Tipo | Descrição |
|---|---|---|
| `property` | string | Propriedade alterada. Pode ser um nome simples (`version`, `addresses`) ou uma **chave composta com UUIDs embutidos** (ver §4) |
| `oldValues[]` | array\<string\> | Valores anteriores (vazio em criação) |
| `newValues[]` | array\<string\> | Valores novos (vazio em remoção). Podem conter **JSON serializado como string** |

**`EntityChange`**: `entityId`, `entityName`, `entityType`, `oldValues[]`,
`newValues[]` — nunca observado preenchido na org.

**`InitiatingAction`**: `transactionId`, `actionContext` — nunca observado
preenchido na org.

**`MessageInfo`**: `message`, `messageWithParams`, `messageParams`,
`localizableMessageCode` — nunca observado na org.

---

## 4. Perfil real por serviço consultado

Onde a documentação genérica e a realidade da org divergem — validado
empiricamente na exploração feita com `explorar_auditoria.py` antes de
implementar a busca por pessoa (ver §7 para o histórico dessa implementação).

### 4.1 `ContactCenter` (100 eventos — 100% `Queue`)

Membership de filas. Actions observadas: `MemberUpdate` (62), `MemberAdd` (26),
`MemberRemove` (12).

- `entity` = **a fila** (`entity.name` = nome da fila, 100% preenchido).
- **O UUID da pessoa fica em `propertyChanges[].property`**, formatos:
  - `QueueMember/<uuid-fila>:<uuid-usuario>` → add/remove de membro
    (`newValues: ["<queue member added>"]` / `oldValues: ["<queue member deleted>"]`)
  - `QueueMember/<uuid-fila>:<uuid-usuario>:joined` → ativação/desativação
    do membro na fila (`oldValues/newValues`: `"true"`/`"false"`)
- `context` sempre `{entityId: <uuid-fila>, auditType: "QUEUE"}` (redundante
  com `entity.id`).
- `level`: 56% `USER` (com `user.id` + `remoteIp`), 44% `SYSTEM`.

### 4.2 `PeoplePermissions` (100 eventos — 100% `Role`)

Atribuição/remoção de roles. Actions: `MemberAdd` (78), `MemberRemove` (22).

- `entity` = **a role** (`entity.id` = UUID da role), **mas** `entity.name`
  **não é o nome da role**: é uma chave composta
  `{uuid-usuario}--{uuid-role}--{uuid-org}` — **é aqui que mora o UUID da
  pessoa afetada** (a doc genérica sugeria `propertyChanges`, que neste
  serviço vem **sempre vazio**).
- `context` sempre vazio; sem diff nenhum — o evento em si (action) é toda
  a informação.
- `level`: 80% `SYSTEM`, 20% `USER`.

### 4.3 `Directory` (60 eventos — 100% `User Update`)

Edição de perfil de usuário.

- `entity.id` = **o próprio UUID da pessoa editada** → o filtro nativo
  `EntityId` funciona direto aqui (caminho rápido, sem varredura).
- `entity.name` vazio neste serviço.
- `propertyChanges` observados: `version` (100% — contador interno, ruído),
  `addresses` (17% — telefones, **JSON serializado dentro da string**),
  `primaryContactInfo`, `state`, `stateChangeTimestamp` (raros).
- `context` sempre vazio.
- `level`: 97% `SYSTEM` (sincronizações/automatismos), 3% `USER`.

### 4.4 `Groups` (300 eventos / 30 dias — 100% `DirectoryGroup Update`)

Membership de grupo (`DirectoryGroup`; o mesmo vale para `SkillGroup`/`Team`/
`SkillGroupDefinition`, nunca observados na org). Validado com
`explorar_auditoria.py --amostra Groups --dias 30 --max 300` e chamadas
diretas à API durante a investigação de 2026-07-12 (ver `groups-membership-direction-quirk`
na memória do projeto).

- **`action` é sempre `Update`** — ao contrário de `Queue`/`Role`, não existe
  `MemberAdd`/`MemberRemove` distinto para Groups.
- **`entity.name` vem sempre vazio** (diferente de `Queue`, que preenche);
  o nome do grupo só existe via o mapa bulk `GET /groups`.
- **Cada mudança de membership gera um trio de eventos**, sempre com o mesmo
  `context.correlationId`, tipicamente em 1–3 segundos um do outro:
  1. `memberCount` (propertyChange) — `oldValues`/`newValues` = contagem antes/depois
     do grupo. **É o único lugar onde a direção real (adição vs. remoção) existe**:
     contagem sobe = adição, desce = remoção. Sempre `level: SYSTEM`, mesmo
     quando a mudança foi 100% humana via painel — `user` vem `{}`, só
     `context.userid` tem o UUID de quem fez (não `user.id`).
  2. `individuals` (propertyChange) — **`oldValues`/`newValues` sempre vazios
     nos dois lados, 104/104 ocorrências na amostra de 30 dias**. Ruído puro
     da API, sem nenhuma informação. `level` USER (ação humana) ou SYSTEM
     (sync/automação, ex. regra dinâmica de grupo).
  3. `group-membership` (propertyChange) — **é aqui que mora o UUID do
     membro afetado**, mas como uma string não-JSON `"[uuid1, uuid2]"` (sem
     aspas nos UUIDs) em `newValues`, com `oldValues` **sempre vazio** —
     **tanto em adição quanto em remoção** (confirmado: 0 ocorrências de
     `oldValues` populado em 104 amostras). Ou seja: **esse propertyChange
     sozinho não permite saber a direção**, só quem foi afetado.
- **Gotcha do filtro `UserId`:** como `memberCount` não tem `user.id` (só
  `context.userid`), o filtro nativo `UserId` da consulta (usado na busca
  "por pessoa, ações que ela fez") **exclui `memberCount` no lado da
  Genesys**, antes do evento chegar no backend — confirmado comparando a
  mesma janela filtrada por `UserId` (3–4 eventos, sem `memberCount`) vs.
  filtrada por `EntityId`+`EntityType` do grupo (6 eventos, com
  `memberCount`). Sem esse terceiro evento, não há como inferir direção.

**Como o projeto resolve isso** (`backend/routes/audits.py`):

- `_enrich_group_membership_direction(batch)` — correlaciona `memberCount` ↔
  `group-membership` por `context.correlationId` dentro do mesmo lote/página
  já buscado, e anota `_groupMembershipDirection: "add"|"remove"` no evento
  `group-membership` (campo próprio do projeto, não existe na API da
  Genesys). Suficiente para `POST /audits/search/deep` (sem filtro `UserId`).
- `_resolve_group_membership_directions(entities, interval_start, interval_end)`
  — fecha a lacuna do filtro `UserId`: para cada `group-membership` ainda sem
  direção, dispara **uma consulta extra** por grupo (`EntityId`+`EntityType`,
  que a Genesys aceita e que inclui `SYSTEM`), busca só o `memberCount`
  daquele grupo no intervalo, e roda a correlação de novo. Ligado em
  `POST /audits/search` (tem o intervalo original) e
  `GET /audits/search/{tid}/results` (não tem intervalo na paginação — deriva
  um a partir do `eventDate` mín/máx da própria página, ±5min de folga).
  Os eventos extras buscados aqui **não** entram na resposta — são só canal
  lateral pra correlação.
- Frontend (`frontend/src/utils/auditFormat.js`) lê `ev._groupMembershipDirection`
  pra escolher o verbo ("adicionou"/"removeu"); se a correlação falhar (grupo
  não encontrado, consulta extra deu erro), cai numa frase neutra
  ("alterou a associação de X com o grupo Y") em vez de chutar — nunca inferir
  direção pelo lado old/new do `group-membership`, que é sempre a mesma forma
  nos dois casos. `individuals` é filtrado do diff inteiramente (zero
  informação, ver acima).

### 4.5 Resumo: onde encontrar a pessoa em cada serviço

| Pergunta | Serviço/entidade | Onde está o UUID da pessoa | Filtro nativo? |
|---|---|---|---|
| O que fulano **fez**? | qualquer | `user.id` | ✅ `UserId` |
| Perfil de fulano foi editado? | `Directory/User` | `entity.id` | ✅ `EntityId` |
| Fulano entrou/saiu de fila? | `ContactCenter/Queue` | `propertyChanges[].property` (`QueueMember/...`) | ❌ busca profunda |
| Fulano ganhou/perdeu role? | `PeoplePermissions/Role` | `entity.name` (`{user}--{role}--{org}`) | ❌ busca profunda |
| Fulano entrou/saiu de grupo? | `Groups/DirectoryGroup` | `propertyChanges[].newValues` (`group-membership`, string `"[uuid, ...]"`) | ⚠️ `UserId` funciona p/ achar o evento, mas **não traz a direção** (precisa da consulta extra por `EntityId` — ver §4.4) |

---

## 5. Quais dados são mais importantes (para estudo)

Ranking prático, do que sempre carrega informação para o que quase nunca:

**Essenciais (sempre usar):**

1. `eventDate` — eixo temporal de qualquer análise.
2. `action` + `entityType` — "o quê" do evento; junto com `serviceName`
   define o significado.
3. `entity.id` / `entity.name` / `entity.selfUri` — o alvo. Atenção aos
   formatos especiais por serviço (§4).
4. `user.id` — o autor humano. **Vazio ≠ sem autor**: significa evento
   `SYSTEM`. Usar `expand=user` para obter `user.name` sem lookup extra.
5. `propertyChanges` — o diff (o "antes → depois"). Único lugar com o
   conteúdo da mudança; em filas, também identifica o membro.

**Importantes (contexto/qualificação):**

6. `level` — separa ação humana (`USER`) de cascata/automação (`SYSTEM`).
   Na org, `SYSTEM` domina (44–97%) — filtrar por `USER` reduz muito o ruído
   em investigações de "quem fez".
7. `client.id` — quando preenchido, a mudança veio de integração/API, não de
   humano (badge "via API" na UI). Na org veio sempre vazio até agora.
8. `remoteIp` — rastreio de origem; só em eventos `USER`.
9. `id` — dedupe ao mesclar consultas (fan-out da busca por pessoa).
10. `context` — só relevante em ContactCenter (`auditType`), e mesmo lá é
    redundante com `entity.id`.

**Baixo valor na prática (nesta org, até agora):**

- `status` — sempre `SUCCESS` (a API nem registra tentativas negadas aqui).
- `application`, `initiatingAction`, `transactionInitiator`, `entityChanges`,
  `message`, `userHomeOrgId` — vazios ou constantes em todas as 260 amostras.
  Documentados no schema oficial, mas sem sinal observado; reavaliar se outros
  serviços (ex.: `Architect`, `Telephony`) os preencherem.

---

## 6. Gotchas confirmados

- **`user.name` não vem por padrão** — só com `expand=user` no `/results`.
  O backend do projeto já envia; o `explorar_auditoria.py` não (por isso o
  perfil mostra `user.name` 0%).
- **`propertyChanges` vazio não significa "sem mudança"** — em
  `PeoplePermissions/Role` a informação está na `action` + `entity.name`.
- **`newValues`/`oldValues` podem conter JSON dentro da string**
  (ex.: `addresses` no Directory) — para estudar o diff é preciso
  `json.loads` no valor.
- **`Directory/User Update` gera muito ruído `SYSTEM`** — o `version` muda a
  cada sync; 97% dos eventos não são ação humana.
- **Cursor só anda para frente** — não há paginação aleatória; para UI, o
  padrão é "carregar mais".
- **Realtime API ≠ Query API** — a realtime cobre só ~14 dias em certos
  serviços (aviso oficial no próprio endpoint); usar sempre a assíncrona para
  histórico. A retenção total da assíncrona não consta no Swagger — confirmar
  em [View audit events](https://help.genesys.cloud/articles/view-audit-events/)
  / [About the Audit Viewer](https://help.genesys.cloud/articles/about-the-audit-log-viewer/)
  se precisar de números exatos (essas páginas documentam a UI, que usa a
  mesma retenção da API).
- **Sentinelas em texto**: `<queue member added>` / `<queue member deleted>`
  aparecem como *valores literais* em `newValues`/`oldValues` — não são
  placeholders da doc, vêm assim da API.
- **`Groups/group-membership` não expõe direção** — `oldValues` sempre vazio,
  `newValues` sempre com o UUID afetado, tanto em adição quanto remoção. A
  direção só existe no `memberCount` irmão (mesmo `correlationId`), que por
  sua vez **some da consulta filtrada por `UserId`** porque é sempre
  `level: SYSTEM` sem `user.id`. Ver §4.4 para o mecanismo de correlação que
  o projeto usa pra contornar isso.

---

## 7. Histórico de implementação e pendências

Migrado de `AUDITORIA.md` (removido para não duplicar documentação — este
arquivo passa a ser a referência única do módulo de auditoria).

### O que existe hoje

**Backend** — `backend/routes/audits.py`, registrado em `backend/main.py`
com `prefix="/audits"`, protegido por `Depends(get_current_user)` (mesmo
JWT/cookie do resto do painel). Reaproveita `get_token()`/`h()` de `auth.py`
e `BASE_URL` de `config.py`.

**Frontend** — `frontend/src/api/audits.js` (client HTTP), `frontend/src/views/AuditView.vue`
(tela com duas abas: filtros dinâmicos e busca "Por pessoa"),
`frontend/src/components/AuditTimeline.vue` (timeline reutilizável, badge
"via API" quando `client.id` preenchido). Rota `/auditoria` no router,
item na sidebar (`App.vue`), botão "Ver auditoria deste usuário" na
`ConsultaView.vue`.

Camada de apresentação (refactor de UX/UI, sem mudança de backend):

- `frontend/src/utils/auditFormat.js` — o §4 deste dicionário em código:
  parsing de `QueueMember/<fila>:<user>[:joined]`, da chave composta
  `{user}--{role}--{org}` de Role, tradução das sentinelas literais,
  `JSON.parse` dos valores de diff e frase legível por evento.
- `frontend/src/composables/useUserNames.js` — hoje é um re-export fino de
  `useEntityNames.js` (ver "Resolução de nomes" abaixo). Mantém o contrato
  antigo (`prime`/`resolveMany`/`nameOf`); a fonte de nome mudou de
  `GET /users/search` (pesado) para `GET /users/{id}/name` (leve).
- `frontend/src/components/AuditTokens.vue` — renderiza a frase como tokens;
  chips de role/grupo resolvem para nome automaticamente (mapa bulk); UUID
  fora do mapa aparece abreviado (`43e34005…8269`) com tooltip + botão copiar.
- Timeline separa `USER` de `SYSTEM` (avatar de engrenagem, card esmaecido,
  filtro "Todos / Ação humana / Sistema" na toolbar de resultados); `version`
  do Directory marcado como ruído no diff; na aba "Por pessoa" os 4 serviços
  com eventos confirmados ficam em destaque e os demais colapsados atrás de
  um toggle; progresso do fan-out vira stat cards por serviço.

A busca "Por pessoa" faz fan-out concorrente (até 3 serviços em paralelo)
usando `/audits/search/deep`, com autocomplete de usuário
(`GET /users/autocomplete?q=`) e deep-link via `?userId=&name=`.

### Resolução de nomes (usuários, roles, grupos, divisões)

UUIDs na timeline viram nomes reais por caminhos escolhidos pelo custo:

**Backend — endpoints novos:**

- `GET /users/{user_id}/name` (`routes/users.py`) — proxy leve de
  `GET /api/v2/users/{id}` **sem `expand`**; devolve `{found, id, name}`
  (404 → `found:false`). Substitui o `/users/search` pesado como fonte do
  cache (o search expande `authorization,groups` + N chamadas de grupo).
- `GET /roles` (`routes/roles.py`) — lista o mapa `{id, name}` de **todas** as
  roles da org, paginando `GET /api/v2/authorization/roles`. Um `403`
  (integração sem `authorization:role:view`) devolve `{roles: [], warning}` —
  o frontend degrada para chips de UUID sem quebrar a timeline.
- `GET /groups` (`routes/groups.py`) — idem para grupos, paginando
  `GET /api/v2/groups` com teto de páginas (`MAX_PAGES=25`, flag `truncated`).
- `GET /divisions` (`routes/divisions.py`) — idem para divisões organizacionais
  (`GET /api/v2/authorization/divisions`), mesmo formato (`403` →
  `{divisions: [], warning}`). Confirmado na org: **50 divisões, 1 página**.

**Frontend — `useEntityNames.js`** (o `useUserNames.js` é um re-export):

- **Usuário — cache per-UUID:** resolve sob demanda (pool de 3, teto de 60
  lookups/sessão), alimentado de graça por `prime()` (autores via `expand=user`,
  pessoa buscada). Não dá para listar todos os usuários da org → segue per-UUID.
- **Role/grupo/divisão — cache bulk:** `ensureBulk()` busca o mapa inteiro
  **uma vez por sessão** (guardado por flag + promessa in-flight) e prima
  todos os nomes; a partir daí todo chip/pílula daquele tipo resolve de graça.
- `auditFormat.js` normaliza os 4 entityTypes do serviço Groups
  (`DirectoryGroup`/`SkillGroup`/`Team`/`SkillGroupDefinition`) para o hint
  `'group'`; o token de role já sai com hint `'role'`.
- **Divisão é um caso à parte:** não aparece como token na frase do evento
  (`describeEvent()`), e sim como `propertyChanges[].property === 'divisionId'`
  no diff genérico (`Directory/User Update`, valores antigo/novo). `AuditTokens.vue`
  dispara `ensureBulk()` de role/grupo com base nos tokens da frase; como o diff
  de `divisionId` não passa pelo sistema de tokens, `formatChanges()` (que
  monta as linhas do diff) dispara `ensureBulk()` de divisões direto, só quando
  há um `divisionId` no evento, e troca o UUID pelo nome resolvido na pílula
  (mantendo o UUID no `title`/tooltip). Resolvido a pedido do Athos ao notar
  `divisionId` cru numa atualização de perfil (`Directory/User`).

**Decisão de UX (auto vs. sob demanda) — evolução:** a intenção inicial
(2026-07-12, ver memória `audit-name-resolution-followup.md`) era tradução
**sob demanda por clique**, sob a premissa de que só existia lookup individual
caro (1 chamada por UUID). Ao descobrir os endpoints de **listagem** da Genesys,
a economia inverteu: 1 (ou poucas) chamada(s) por sessão trazem o mapa inteiro
de roles/grupos — mais barato **e** melhor de usar (resolução automática, sem
clique) que o per-chip. Por isso a versão final é **mapa em bulk + automático**
para role/grupo. Usuário continua per-UUID automático por não ser listável em
bulk. O custo do bulk é lazy: só é pago quando há evento de role/grupo na tela,
que é exatamente quando os nomes interessam.

### Verificação já feita

- Backend importa sem erro; 3+2 rotas novas expostas (`/audits/*`,
  `/users/autocomplete`).
- `npx vite build` limpo; `AuditView` sai como chunk separado.
- `pytest`: sem regressão introduzida (as falhas pré-existentes em
  `test_actions.py`/`test_users.py` são as mesmas com e sem a mudança).
- Rotas `/audits/*` e `/users/autocomplete` sem cookie → `401` (proteção JWT
  ativa); com cookie válido → resultados reais testados ponta a ponta.
- `_event_matches` (busca profunda) validado contra dado real: localizou
  corretamente um `MemberRemove` de Role usando o UUID da pessoa.
- Amostras reais (`amostras/*.json`, continham e-mail/telefone reais) foram
  a base deste dicionário e a pasta está no `.gitignore` para não vazar PII.

### Direção de membership em Groups (2026-07-12, CONCLUÍDO)

Descoberto ao investigar por que a timeline mostrava "adicionou" pra uma
remoção real de grupo (ver §4.4 para o perfil completo do serviço `Groups` e
os gotchas). Resumo do que foi implementado:

- `_enrich_group_membership_direction()` e `_resolve_group_membership_directions()`
  em `backend/routes/audits.py` — correlacionam `group-membership` ↔
  `memberCount` (mesmo `correlationId`) e anotam `_groupMembershipDirection`;
  a segunda função cobre o caso em que o filtro `UserId` já descartou o
  `memberCount` antes de chegar no backend, com uma consulta extra por grupo.
- `frontend/src/utils/auditFormat.js` — `describeEvent()` e `formatChanges()`
  usam `ev._groupMembershipDirection` em vez de inferir pela forma do
  `oldValues`/`newValues` (que é sempre a mesma nos dois casos).
- Validado ponta a ponta contra a Genesys real (não só dado sintético):
  chamada direta de `search_audits()` dentro do container rodando, contra o
  caso de teste real (adicionar e depois remover a si mesmo de um grupo) —
  os dois eventos resolveram a direção corretamente.

### Pendências conhecidas (ainda não implementadas)

- **`max_pages` da busca profunda tem cap de 10** (~1000 eventos varridos) —
  períodos muito longos podem truncar o resultado; monitorar se isso
  incomoda no uso real antes de subir o limite.
- **Resolução inline de grupo em `users.py` duplicada** — `search_user()`
  resolve nome de grupo chamando `GET /groups/{id}` da Genesys direto, em dois
  blocos quase idênticos. Poderia reusar o mapa de `GET /groups` / o cache do
  frontend. Cleanup futuro, fora do escopo da normalização de nomes.
- **`_resolve_group_membership_directions` faz 1 consulta assíncrona (create+poll)
  por grupo distinto** — cada uma pode levar alguns segundos (polling a cada
  2s). Para uma pessoa com histórico em muitos grupos diferentes no mesmo
  período, isso soma latência perceptível. Não observado como problema real
  ainda; considerar paralelizar (hoje é sequencial) se aparecer reclamação de
  lentidão na aba "Por pessoa".
