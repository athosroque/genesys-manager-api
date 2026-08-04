# Âncora — Audit API Genesys × Módulo local

Documento de referência para implementar **testes** e **novas funcionalidades** do
módulo de auditoria sem reconsultar a documentação oficial.

| Campo | Valor |
|---|---|
| Data da análise | 2026-08-03 |
| Escopo | Double-check das 6 páginas oficiais de Audit vs código do `genesys-manager-api` |
| Relacionado | [`DICIONARIO-AUDITORIA.md`](./DICIONARIO-AUDITORIA.md) (campos/schemas/amostras) |
| Código principal | `backend/routes/audits.py`, `backend/services/user_audit.py`, `frontend/src/views/AuditView.vue`, `frontend/src/components/AuditSearchBar.vue`, `frontend/src/components/UserChangesList.vue` |
| Testes atuais | `backend/test_audits.py` (429, 403, `pageSize` da deep search) |

> **Como usar:** trate este arquivo como backlog + contrato. O dicionário cobre
> *o que cada campo significa*; esta âncora cobre *o que está implementado, o que
> falta e o que testar*.

---

## 1. Metodologia e fontes

### 1.1 Páginas oficiais analisadas

| Página | URL | Agente (transcript) |
|---|---|---|
| Overview | https://developer.genesys.cloud/platform/audit/ | [overview](7cf6e0c0-0c0c-457b-b04f-7f3938685bc0) |
| Audit Query Create | https://developer.genesys.cloud/platform/audit/auditquerycreate | [auditquerycreate](69f1ab9e-6f09-40b2-9ab9-0dcd382cc66b) |
| Action Catalog | https://developer.genesys.cloud/platform/audit/actioncatalog | [actioncatalog](e16b065f-87c7-46ce-9871-e4289b38c5ce) |
| Use Cursor | https://developer.genesys.cloud/platform/audit/usecursor | [usecursor](b3361e9a-914f-4c0e-992a-769d622c83d9) |
| Audit Wiki | https://developer.genesys.cloud/platform/audit/auditwiki | [auditwiki](3bf9ecf8-da7c-474e-a100-26b047086a5b) |
| Sample Usage | https://developer.genesys.cloud/platform/audit/sampleusage | [sampleusage](942c24e6-e4a3-4615-a2bc-a4a9c5549f45) |

### 1.2 Fontes estruturadas usadas (porque o Developer Center é SPA)

O fetch direto das URLs `developer.genesys.cloud/platform/audit/*` devolve
apenas o shell HTML (“enable JavaScript”). Os agentes validaram o contrato via:

| Fonte | URL / caminho | Uso |
|---|---|---|
| REST API v2 — domínio audits | https://developer.genesys.cloud/api/rest/v2/audits/ | Endpoints e schemas |
| Sample usage (HTML estático) | https://developer.genesys.cloud/api/rest/v2/audit/sampleusage.html | Payloads oficiais de exemplo |
| Swagger público | https://api.mypurecloud.com/api/v2/docs/swagger | Schemas `AuditQuery*`, `AuditLogMessage` |
| Dicionário local | `refencia_retornos/DICIONARIO-AUDITORIA.md` | Comportamento observado na org `sae1.pure.cloud` |
| Explorador local | `refencia_retornos/explorar_auditoria.py` | Coleta de amostras |
| Código do módulo | `backend/routes/audits.py` (+ frontend listado acima) | Double-check de implementação |

### 1.3 Caveats da pesquisa

- Detalhes de **TTL do cursor** na página `usecursor` ficaram pendentes de
  validação no HTML renderizado ao vivo (browser indisponível na sessão do agente).
- Limites de **30 dias / consulta** e **365 dias de retenção** vieram do Audit
  Wiki / referências indexadas e REST relacionadas — confirmar se a Genesys
  alterar a política.
- `sortOrder` canônico é `ascending`/`descending`; a org aceita `asc`/`desc`
  empiricamente (registrado no dicionário). Tratar aliases como risco contratual.

---

## 2. Mapa do que existe hoje

### 2.1 Fluxo Genesys (oficial)

```
POST /api/v2/audits/query                         → cria execução (id = transactionId)
GET  /api/v2/audits/query/{transactionId}         → polling: Queued|Running|Succeeded|Failed|Cancelled
GET  /api/v2/audits/query/{transactionId}/results → páginas (cursor, pageSize≤500, expand=user)
GET  /api/v2/audits/query/servicemapping          → catálogo vivo da org
```

Permissão: `audits:audit:view` (OAuth scope típico: `audits:readonly`).

Não usados pelo projeto (decisão coerente para histórico):

- `POST /api/v2/audits/query/realtime` — histórico limitado (~14 dias em alguns serviços)
- `POST /api/v2/audits/query/realtime/related` — eventos correlatos da mesma ação

### 2.2 Rotas locais ↔ Genesys

| Rota local | Genesys | Comportamento |
|---|---|---|
| `POST /audits/user-changes` | create+poll+results (orquestrado em `user_audit.py`) | **Fluxo principal da UI.** Resolve usuário; `deep_categories: []` = só Directory/divisão; lista explícita = deep só nessas (`queue`/`role`/`group`, sem Directory); compat `deep_search:true` sem lista = Directory + as 3. Deep: chunk diário + bisecção. Retorna `{ user, interval, changes[], meta }` (`deep_categories`, `truncated_by_service`, `scanned_by_service`, …) |
| `GET /audits/services` | `GET .../servicemapping` | Normaliza `name/entities` **e** `serviceName/entityTypes` |
| `POST /audits/search` | create + poll + 1ª página `/results` | Retorna `transactionId`, `state`, `cursor`, `pageSize`, `entities` (API de baixo nível) |
| `GET /audits/search/{tid}/results` | `GET .../results?cursor&pageSize` | Retorna `transactionId`, `cursor`, `entities` (**sem** `pageSize`/`nextUri`) |
| `POST /audits/search/deep` | create + poll + N páginas | Filtra UUID localmente; retorna `truncated` (API genérica; a Trilha usa a lógica em `user_audit`) |

### 2.3 Payload montado pelo backend

```json
{
  "interval": "<interval_start>/<interval_end>",
  "serviceName": "<service_name>",
  "sort": [{ "name": "Timestamp", "sortOrder": "desc" }],
  "filters": [{ "property": "...", "value": "..." }]
}
```

Parâmetros de results sempre incluem `expand=user`.

### 2.4 Constantes / limites no código (estado em 2026-08-03)

| Item | Valor no código | Observação |
|---|---|---|
| Retry 429 | `MAX_RETRIES = 5` (`audits.py`) | Usa header `Retry-After` ou `[N]` na mensagem |
| Timeout HTTP por chamada | `httpx.AsyncClient(timeout=30)` | Não há teto global da operação |
| Polling | 15 tentativas × `sleep(2)` ≈ 30s | Se ainda `Queued`/`Running`, devolve estado incompleto + `entities: []` |
| Intervalo máx. (`user-changes`) | `MAX_INTERVAL_DAYS = 30` | Validado em `user_audit.validate_interval` |
| Deep `pageSize` / páginas | `DEEP_PAGE_SIZE = 250`, `DEEP_MAX_PAGES = 10` | Por janela; chunk diário + bisecção até 1h |
| Deep chunk / pause | `DEEP_CHUNK_DAYS = 1`, pause `0.4s` | Pool `QUERY_POOL_SIZE = 1` (evita 429) |
| `page_size` (`/search`) | 1–500 (default 50) | API de baixo nível |
| `max_pages` (`/search/deep`) | default 10, max schema 50 | Schema permite 50; fluxo da Trilha usa `user_audit` |
| `sort_order` | pattern `^(asc\|desc)$` | Canônico Genesys: `ascending`/`descending` |

### 2.5 Frontend — Trilha de Auditoria (fluxo principal)

Em `AuditView.vue` + `AuditSearchBar.vue` + `UserChangesList.vue`:

- **Pesquisar** → `deep_categories: []` (só divisão; substitui a lista)
- Botões **Buscar filas / roles / grupos** → `deep_categories: [categoria]`; merge na lista
- **Cancelar** via `AbortController`; empty states por categoria; bloco “Como funciona”
- Truncamento: aviso na UI a partir de `meta.truncated` / `truncated_by_service`
- Proxy nginx `/api/`: `proxy_read_timeout` / `proxy_send_timeout` **300s**; UI trata 504/408 com mensagem amigável (`api/http.js`)
- Cards narrativos para membership; Antes/Depois para divisão
- Abas por filtros / multi-serviço / toggle único de deep na UI **não são mais o fluxo principal**
  (rotas `/search` e `/search/deep` seguem disponíveis no backend)

### 2.6 Filtros nativos Genesys

| Property | Significado | Exposto na UI? |
|---|---|---|
| `UserId` | Autor da ação | Sim (“o que a pessoa fez”) |
| `EntityId` | Alvo direto | Sim (com `EntityType`) |
| `EntityType` | Tipo do alvo | Sim (dinâmico) |
| `Action` | Ação (exige `EntityType`) | Sim (dinâmico) |
| `ClientId` | Cliente OAuth | Não (API interna aceita string livre) |
| `TrusteeOrganizationId` | Org trustee | Não |

Filtros combinam com **AND**.

---

## 3. Contratos oficiais consolidados

### 3.1 Create query — request

`AuditQueryRequest`:

| Campo | Obrigatório | Formato |
|---|---|---|
| `interval` | Sim | ISO-8601 `start/end` |
| `serviceName` | Sim (na prática) | Identificador case-sensitive do mapping |
| `filters[]` | Não | `{ "property", "value" }` |
| `sort[]` | Não | `{ "name": "Timestamp", "sortOrder": "ascending\|descending" }` |

Regra crítica: **`Action` sem `EntityType` → 400 `IllegalQueryException`**.

### 3.2 Create / status — response

`AuditQueryExecutionStatusResponse`:

- `id` (= transactionId; **não** existe `jobId` nesse contrato)
- `state`: `Queued` \| `Running` \| `Succeeded` \| `Failed` \| `Cancelled`
- Também pode trazer `startDate`, `interval`, `serviceName`, `filters`, `sort`
- HTTP: `200` ou `202`

### 3.3 Results — query params e response

Params: `cursor`, `pageSize` (default 25, max 500), `expand=user`, `allowRedirect`.

Response típica: `id`, `pageSize`, `cursor` (ausente na última página), `entities[]`,
e potencialmente `nextUri`.

Conjuntos muito grandes podem responder **`302`** com URL de download
(`allowRedirect`) — **não modelado** no backend local.

### 3.4 Limites de produto (Audit Wiki)

| Limite | Valor | Implicação |
|---|---|---|
| Janela por consulta assíncrona | **máx. 30 dias** | Intervalos maiores precisam de fatiamento |
| Retenção de eventos | **365 dias** | Além disso: irrecuperável; exportar preventivamente (API ou EventBridge) |
| `pageSize` | máx. 500 | Já limitado no Pydantic |
| Paginação | cursor opaco, só para frente | Sem `pageNumber` no fluxo async |
| Realtime | histórico menor (~14d em alguns serviços) | Projeto usa async de propósito |

### 3.5 Samples oficiais (fixtures prontas para testes)

#### Sample A — membership de fila

Request:

```json
{
  "interval": "2020-05-14T14:40:00/2020-05-19T14:45:00",
  "serviceName": "ContactCenter",
  "filters": [
    { "property": "EntityType", "value": "Queue" },
    { "property": "Action", "value": "MemberAdd" }
  ]
}
```

Formato de diff no **sample oficial**:

- `propertyChanges[].property` = `queueId:<queueId>:members`
- `propertyChanges[].newValues[]` = `queueMember:<userId>`
- `entity.id` = fila
- Orientação oficial: resolver usuário via `GET /api/v2/users/{userId}`

Formato **observado na org** (parser atual):

- `property` = `QueueMember/<queueId>:<userId>[:joined]`
- Regex legada em `docs/arquivo/frontend-audit-legado/auditFormat.js`: `QUEUE_MEMBER_RE`

> **Gap concreto:** `parseQueueMemberProp()` **não** cobre o formato do sample
> oficial. Deep search ainda acha o UUID em `newValues`, mas a timeline não
> monta a frase de membership nem resolve o user a partir de `queueMember:<id>`.

#### Sample B — permissões / AccessToken

Request:

```json
{
  "interval": "2020-03-1T12:00:00/2020-03-5T20:00:00",
  "serviceName": "PeoplePermissions",
  "filters": [
    { "property": "EntityType", "value": "AccessToken" },
    { "property": "Action", "value": "Create" }
  ]
}
```

Nesse sample, `propertyChanges` vem **vazio**; o evento ainda é significativo
via `action`, `entity`, `user`, `client`. A timeline local já trata diff vazio
sem assumir “sem mudança”.

### 3.6 Action Catalog — combos relevantes ao produto

Nomes **case-sensitive**. Seção Async é a referência (Realtime é subconjunto).

| Serviço | EntityType | Actions relevantes |
|---|---|---|
| `PeoplePermissions` | `Role` | `Create`, `Update`, `LicenseUpdate`, `MemberAdd`, `MemberUpdate`, `MemberRemove` |
| `ContactCenter` | `Queue` | `Create`, `Update`, `Delete`, `MemberAdd`, `MemberUpdate`, `MemberRemove`, `WrapupCodeAdd`, `WrapupCodeRemove` |
| `Directory` | `User`, `Organization` | `Create`, `Update`, `Delete` |
| `Groups` | `SkillGroup`, `DirectoryGroup`, `Team`, `SkillGroupDefinition` | `Create`, `Update`, `Delete` |

Fonte operacional por org: **`servicemapping` ao vivo** (melhor que snapshot do
Action Catalog). Action Catalog = referência global da plataforma.

A deep search de `user_audit` filtra Groups por `EntityType=DirectoryGroup`.
`SkillGroup`, `Team` e `SkillGroupDefinition` podem existir no catálogo, mas
**não** entram nesse fan-out (só `DirectoryGroup`).

---

## 4. Achados por página (síntese dos subagentes)

### 4.1 Overview — alinhado no fluxo; faltam status exposto e realtime/related

**Alinhado:** create → poll → results; servicemapping; `expand=user`; pageSize≤500;
403 com mensagem de `audits:audit:view`; cursor unidirecional.

**Gaps:** sem rota local de status; polling ~30s pode virar “lista vazia”;
`sort_order` não canônico; deep search sem metadados de cobertura; `transaction_id`
acessível a qualquer usuário autenticado local; testes só na camada HTTP.

### 4.2 Audit Query Create — contrato coberto; validações fracas

**Alinhado:** payload, async, `id` como transactionId, filtros principais,
servicemapping, UI evita Action sem EntityType, retry 429.

**Gaps:** `asc|desc` vs `ascending|descending`; `AuditFilter.property` livre;
sem validação Action→EntityType no backend; `ClientId`/`TrusteeOrganizationId`
não na UI; timeout de poll ambíguo; sem `302`/allowRedirect; responses Genesys
não validadas por Pydantic.

### 4.3 Action Catalog — dinâmico (correto); deep/curadoria parciais

**Alinhado:** não hardcoda o catálogo inteiro; casing dos curados correto;
consulta genérica usa mapping vivo; async.

**Gaps:** deep/curadoria limitados a 4 serviços / 3 combos; `actionKind()` só
CRUD-ish (Publish/Enable/… caem em “outras”); sem validação semântica backend;
sem testes de normalização dos dois formatos de servicemapping.

### 4.4 Use Cursor — paginação correta; contrato de página inconsistente

**Alinhado:** sem pageNumber; primeira página sem cursor; “carregar mais”;
pageSize≤500; deep com `truncated`; retry 429.

**Gaps:** `nextUri` não propagado; sem tratamento de cursor expirado; 2ª+ páginas
omitindo `pageSize`/`nextUri`; deep para em lote vazio **ou** cursor ausente
(risco de truncar se API devolver lote vazio + cursor válido); doc `max_pages`
10 vs schema 50; sem testes de encadeamento de cursor.

### 4.5 Audit Wiki — limites de produto não enforceados

**Alinhado:** async (não realtime); cursor; pageSize; expand=user; UserId vs
EntityId; Groups com correlação por `correlationId`/`memberCount`; SYSTEM não
tratado como “ninguém”.

**Gaps:** sem validação 30 dias / 365 dias; sem fatiamento de intervalo; poll
não-terminal; latência sem teto global; deep caro; resolução de Groups sequencial;
sem retenção externa; sem testes dos limites.

### 4.6 Sample Usage — fluxo ok; parser de fila divergente do sample

**Alinhado:** samples de filtros reproduzíveis; AccessToken com diff vazio ok;
cursor/expand.

**Gaps:** parser só `QueueMember/...`; status não exposto; envelope inconsistente;
erros Genesys reduzidos a 300 chars de texto; testes não usam os samples oficiais.

---

## 5. Gaps consolidados (priorizados para implementação)

### P0 — bugs / comportamentos enganosos

| ID | Gap | Onde |
|---|---|---|
| P0-1 | Polling timeout devolve lista vazia e UI trata como “nenhuma alteração” | `_create_and_poll` → `user-changes` / `AuditView` |
| P0-2 | Parser de membership de fila não cobre formato oficial `queueId:…:members` / `queueMember:…` | `user_audit.py` (`QUEUE_MEMBER_RE`) — cobre o formato observado na org |
| P0-3 | Intervalo >30 dias: **já validado** em `user_audit`; rotas `/search` ainda não validam localmente | `AuditSearchRequest` vs `validate_interval` |

### P1 — contrato e robustez

| ID | Gap | Onde |
|---|---|---|
| P1-1 | Normalizar `sortOrder` → `ascending`/`descending` | backend |
| P1-2 | Envelope único em todas as páginas: `transactionId`, `state`, `pageSize`, `cursor`, `nextUri`, `entities` | `/search` e `/results` |
| P1-3 | Expor `GET /audits/search/{tid}` (status) ou `pending: true` + UI continua poll | backend + frontend |
| P1-4 | Validar filtros: enum de properties; Action→EntityType; EntityId→EntityType | Pydantic |
| P1-5 | Propagar/tratar `nextUri`; erro explícito de cursor expirado | results |
| P1-6 | Vincular `transaction_id` ao usuário/sessão local | auth + results |

### P2 — produto / escala

| ID | Gap | Onde |
|---|---|---|
| P2-1 | Fatiamento automático de intervalos longos (blocos ≤30d) + dedupe por `id` | search/deep |
| P2-2 | Orçamento global deep search + motivo de interrupção | deep |
| P2-3 | Modelar `302` / download / `allowRedirect` | genesys_request |
| P2-4 | Ampliar deep Groups além de `DirectoryGroup` (SkillGroup, Team, …) | `user_audit.get_user_changes` |
| P2-5 | Expor `ClientId` / `TrusteeOrganizationId` se houver caso de governança | UI |
| P2-6 | Erros Genesys estruturados (`code`, `message`, correlation id) | genesys_request |
| P2-7 | Retenção externa / EventBridge (compliance >365d) | infra |
| P2-8 | Realtime / related (só se houver caso de uso) | opcional |

---

## 6. Backlog de testes (âncora para `test_audits.py` e frontend)

Cobertura atual: retry 429 (mensagem + header), desistência após max retries,
403 sem retry, deep search encaminha `pageSize` customizado.

### 6.1 Contrato de payload (fixtures = samples oficiais)

- [ ] Montagem de body: Sample A (`ContactCenter`/`Queue`/`MemberAdd`)
- [ ] Montagem de body: Sample B (`PeoplePermissions`/`AccessToken`/`Create`)
- [ ] `interval` = `start/end` concatenado
- [ ] `sort` com normalização para `descending`/`ascending`
- [ ] `expand=user` em results (1ª e demais páginas)

### 6.2 Estados da execução

- [ ] `Queued → Running → Succeeded` (poll)
- [ ] `Failed` propaga erro
- [ ] `Cancelled` propaga erro
- [ ] Timeout após 15 polls: resposta com `pending`/`state` explícito (após P0-1)
- [ ] Create respondendo 200 vs 202

### 6.3 Filtros e validação

- [ ] `Action` sem `EntityType` → 422 local (após P1-4)
- [ ] Property inválida → 422
- [ ] Intervalo invertido / >30 dias / início >365d atrás → 422
- [ ] Dois formatos de `servicemapping` normalizados para `{ name, entities: [{ name, actions }] }`
- [ ] Casing preservado (`PeoplePermissions`, não lowercased)

### 6.4 Paginação / cursor

- [ ] 1ª página sem `cursor` no request
- [ ] 2ª página repassa cursor retornado
- [ ] Última página: cursor ausente → UI para “carregar mais”
- [ ] Resposta vazia
- [ ] Cursor inválido/expirado → mensagem específica (após P1-5)
- [ ] `pageSize` presente também na rota de continuação (após P1-2)
- [ ] `nextUri` propagado (após P1-2)
- [ ] Deep: `truncated=true` ao atingir `max_pages`
- [ ] Deep: fim preferencialmente por cursor ausente; se lote vazio, sinalizar motivo

### 6.5 Interpretação de eventos (unit frontend / utils)

- [ ] `parseQueueMemberProp('QueueMember/<q>:<u>')` (formato org)
- [ ] `parseQueueMemberProp` + valores `queueId:…:members` / `queueMember:…` (formato sample)
- [ ] AccessToken/Create com `propertyChanges: []` não quebra timeline
- [ ] Evento SYSTEM vs humano
- [ ] Groups: correlação memberCount por correlationId

### 6.6 Transporte / erros

- [ ] 429 já coberto — manter
- [ ] 403 mensagem `audits:audit:view` — manter/ampliar assert de body
- [ ] 302 results / allowRedirect (após P2-3)
- [ ] Erro estruturado Genesys (após P2-6)

---

## 7. Backlog de funcionalidades (ordem sugerida)

1. **P0-1 + P1-3** — pending/status + UI não mentir “vazio”
2. **P0-3 + P1-4** — validação de intervalo e filtros no Pydantic
3. **P0-2** — parser dual de membership de fila (+ testes 6.5)
4. **P1-1 + P1-2** — sort canônico + envelope consistente (`pageSize`, `nextUri`)
5. **P1-5** — cursor expirado / reinício de busca
6. **P2-1** — fatiamento ≤30 dias com metadados (`effectiveIntervals`, `partial`, …)
7. **P2-2** — orçamento deep + motivo de parada
8. **P1-6** — ownership de transaction_id
9. **P2-4 / P2-5 / P2-3 / P2-6** conforme necessidade de produto
10. **P2-7** — retenção externa se compliance exigir

Metadados sugeridos nas respostas (Wiki):

```json
{
  "requestedInterval": ".../...",
  "effectiveIntervals": [".../..."],
  "partial": false,
  "truncated": false,
  "retentionBoundary": "ISO-date",
  "warning": null,
  "pending": false,
  "state": "Succeeded"
}
```

---

## 8. Arquivos tocados tipicamente

| Área | Arquivos |
|---|---|
| Backend API | `backend/routes/audits.py`, `backend/services/user_audit.py` |
| Testes backend | `backend/test_audits.py` |
| Cliente HTTP | `frontend/src/api/audits.js` (`getUserChanges`) |
| UI (fluxo principal) | `frontend/src/views/AuditView.vue`, `AuditSearchBar.vue`, `UserChangesList.vue` |
| Legado (não usado pela Trilha) | `docs/arquivo/frontend-audit-legado/` (`AuditTimeline`, `AuditTokens`, `auditFormat`) |
| Campos/amostras | `refencia_retornos/DICIONARIO-AUDITORIA.md`, `explorar_auditoria.py` |

---

## 9. Apêndice — relatórios brutos dos subagentes

Os textos completos abaixo foram produzidos em 2026-08-03 pelos agentes
listados na §1.1. Mantidos aqui para não depender dos transcripts.

<details>
<summary>Overview (completo)</summary>

Ver transcript [overview](7cf6e0c0-0c0c-457b-b04f-7f3938685bc0). Síntese operacional
já incorporada nas seções 2–5; pontos únicos: ausência de cancelamento local;
deep search sem continuação por cursor; realtime/related como futuro opcional.

</details>

<details>
<summary>Audit Query Create — pontos que não cabem só na tabela</summary>

- Resposta de status pode incluir `startDate`, `interval`, `serviceName`,
  `filters`, `sort` — hoje não propagados ao frontend.
- `genesys_request` não distingue 302 de sucesso JSON.
- Comentário no código (“Frontend pode continuar consultando /results”) está
  **desatualizado** em relação à UI atual.

</details>

<details>
<summary>Action Catalog — decisão de design a preservar</summary>

Não versionar enum estático do Action Catalog inteiro. Fonte de validade =
`servicemapping` da org. Action Catalog = referência global + documentação.
Cache com TTL + `fetchedAt` é a melhoria recomendada, não hardcode.

</details>

<details>
<summary>Use Cursor — pendência</summary>

TTL exato do cursor **não** foi confirmado no HTML renderizado da página
oficial. Implementar tratamento genérico de cursor inválido/expirado sem
assumir duração fixa até nova validação ao vivo.

</details>

<details>
<summary>Audit Wiki — interpretação de “nenhum evento”</summary>

“Nenhum evento encontrado” **não** significa automaticamente “nada ocorreu”.
Pode ser: retenção expirada, filtro incorreto, intervalo inválido, ação não
auditada, consulta ainda running, ou corte de deep search.

</details>

<details>
<summary>Sample Usage — dualidade de formatos de fila</summary>

Documentar no código/comentário:

- Formato org observado: `QueueMember/<queueId>:<userId>[:joined]`
- Formato sample oficial: `queueId:<queueId>:members` + valor `queueMember:<userId>`

Ambos devem ser aceitos pelo parser.

</details>

---

## 10. Checklist rápido antes de abrir PR de melhoria

- [ ] Li o gap em §5 e o teste correspondente em §6
- [ ] Atualizei este arquivo se o contrato local mudou (envelope, pending, sort…)
- [ ] Se mudei interpretação de campos, atualizei também `DICIONARIO-AUDITORIA.md`
- [ ] Não reintroduzi `asc`/`desc` no wire sem normalização
- [ ] Não tratei lista vazia como resposta terminal sem olhar `state`/`pending`
- [ ] Mantive `servicemapping` como fonte viva de service/entity/action
)
