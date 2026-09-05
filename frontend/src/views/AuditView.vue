<template>
  <div class="space-y-5">
    <div class="mb-1">
      <h1 class="text-2xl font-bold text-ink tracking-tight">Trilha de Auditoria</h1>
      <p class="text-sm text-gray-500 mt-1">
        Consulte alterações de <strong>Divisão</strong> (individual) ou faça varredura de <strong>Filas, Roles e Grupos</strong> para até 10 pessoas ao mesmo tempo.
      </p>
    </div>

    <AuditSearchBar
      ref="searchBar"
      :loading="loadingBase"
      :loading-category="loadingCategory"
      @search="runBaseSearch"
      @deep-search="runDeepSearch"
      @clear="onClear"
      @cancel="cancelSearch"
    />

    <p v-if="error" class="text-sm text-red-600 font-medium">{{ error }}</p>

    <!-- Painel de Progresso da Varredura em Tempo Real -->
    <div
      v-if="loadingCategory && progressState"
      class="rounded-2xl border border-brand/20 bg-brand-soft/20 p-4 space-y-3 shadow-xs"
      data-testid="sweep-progress-panel"
    >
      <div class="flex items-center justify-between text-xs flex-wrap gap-2">
        <div class="flex items-center gap-2">
          <span class="relative flex h-2.5 w-2.5">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand opacity-75"></span>
            <span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-brand"></span>
          </span>
          <span class="font-semibold text-ink text-sm">
            Varrendo {{ progressState.serviceLabel }}
          </span>
          <span v-if="progressState.dateLabel" class="text-gray-500 text-xs">
            · janela de {{ progressState.dateLabel }}
          </span>
        </div>
        <div class="flex items-center gap-3">
          <span class="font-mono text-xs text-brand font-bold">
            {{ progressState.percent }}% concluído
          </span>
          <button
            type="button"
            class="text-xs text-gray-400 hover:text-red-600 underline font-medium"
            @click="cancelSearch"
          >
            Cancelar varredura
          </button>
        </div>
      </div>

      <!-- Barra de progresso -->
      <div class="h-2.5 w-full overflow-hidden rounded-full bg-gray-200">
        <div
          class="h-full rounded-full bg-brand transition-all duration-300 ease-out"
          :style="{ width: `${progressState.percent}%` }"
        ></div>
      </div>

      <!-- Etapa atual em tempo real -->
      <div class="flex items-center gap-2.5 text-xs bg-white/80 border border-brand/20 rounded-xl px-3.5 py-2.5 text-ink shadow-xs">
        <span class="inline-block h-2 w-2 shrink-0 rounded-full bg-brand animate-pulse"></span>
        <span class="font-medium truncate">{{ progressState.currentMessage || 'Processando varredura...' }}</span>
      </div>

      <!-- Contadores em tempo real -->
      <div class="flex items-center justify-between text-xs text-gray-600 pt-0.5">
        <div class="flex items-center gap-4">
          <span>
            Eventos analisados na org: <strong class="text-ink font-mono text-sm">{{ progressState.scanned.toLocaleString('pt-BR') }}</strong>
          </span>
          <span>
            Alterações encontradas: <strong class="text-brand font-mono text-sm">{{ progressState.matched }}</strong>
          </span>
        </div>
        <span class="text-[11px] text-gray-500 font-mono">
          Janela {{ progressState.chunk }} de {{ progressState.totalChunks }}
        </span>
      </div>

      <!-- Visão do que foi feito em cada etapa (Linha do tempo) -->
      <div v-if="progressState.steps && progressState.steps.length" class="border-t border-brand/10 pt-2.5 space-y-1.5">
        <div class="flex items-center justify-between">
          <p class="text-[10px] font-bold uppercase tracking-wider text-gray-400">
            Etapas executadas da varredura
          </p>
          <span class="text-[10px] text-gray-400 font-mono">{{ progressState.steps.length }} concluída(s)</span>
        </div>
        <div class="space-y-1 max-h-36 overflow-y-auto pr-1">
          <div
            v-for="(st, sIdx) in progressState.steps.slice(-6)"
            :key="sIdx"
            class="flex items-center gap-2 text-[11px] text-gray-600 font-mono bg-white/50 rounded px-2 py-0.5"
          >
            <span class="text-green-600 font-bold shrink-0">✓</span>
            <span class="text-gray-400 text-[10px] shrink-0">{{ st.time }}</span>
            <span class="text-gray-700 truncate">{{ st.message }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Feedback de busca vazia com lista já preenchida (ex.: deep sem matches novos) -->
    <div
      v-if="emptyNotice && changes.length && !error && !loadingBase && !loadingCategory"
      class="rounded-xl border border-gray-200 bg-white px-3.5 py-2.5 text-sm text-gray-600"
      role="status"
      data-testid="empty-notice-banner"
    >
      {{ emptyNotice.message }}
    </div>

    <!-- Resumo de Varredura e Resultados -->
    <div
      v-if="searched && changes.length && !loadingBase && !loadingCategory"
      class="flex flex-wrap items-center justify-between gap-3 px-1 text-xs text-gray-500"
    >
      <div class="flex items-center gap-2">
        <span class="font-semibold text-ink text-sm">
          {{ changes.length }} alteração{{ changes.length === 1 ? '' : 'ões' }} encontrada{{ changes.length === 1 ? '' : 's' }}
        </span>
        <span v-if="queriedUsers.length > 1" class="text-gray-400">
          (para {{ queriedUsers.length }} pessoas consultadas)
        </span>
      </div>
      <div v-if="meta?.scanned_total" class="text-gray-500">
        Varredura analisou <span class="font-mono font-medium text-ink">{{ meta.scanned_total.toLocaleString('pt-BR') }}</span> eventos da organização
      </div>
    </div>

    <!-- Skeleton só na primeira carga (sem cards ainda) -->
    <div v-if="loadingBase && !changes.length" class="space-y-3">
      <div v-for="i in 4" :key="i" class="h-20 rounded-2xl bg-white/80 border border-black/[0.04] animate-pulse"></div>
    </div>

    <!-- Empty state geral (lista vazia após busca bem-sucedida) -->
    <div
      v-else-if="searched && !changes.length && !loadingBase && !loadingCategory && !error"
      class="card rounded-2xl border-dashed p-10 text-center"
      data-testid="empty-state"
    >
      <svg class="mx-auto h-10 w-10 text-gray-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="11" cy="11" r="7" />
        <path d="M21 21l-4.3-4.3" stroke-linecap="round" />
      </svg>
      <p class="mt-3 text-ink font-semibold">
        {{ emptyNotice?.message || 'Nenhuma alteração encontrada neste período.' }}
      </p>
      <p class="text-sm text-gray-500 mt-1">
        {{ emptyNotice?.hint || defaultEmptyHint }}
      </p>
    </div>

    <!-- Resultados -->
    <UserChangesList
      v-else-if="changes.length"
      :changes="changes"
      :truncated="anyTruncated"
      :truncated-by-category="truncatedByCategory"
      :fetched-deep-categories="fetchedDeepCategories"
      :queried-users="queriedUsers"
    />
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { getUserChanges, streamUserChanges } from '../api/audits'
import { useToast } from '../composables/useToast'
import AuditSearchBar from '../components/AuditSearchBar.vue'
import UserChangesList from '../components/UserChangesList.vue'
import { datetimeLocalToIso } from '../utils/datetimeLocal'

const { addToast } = useToast()

const SERVICE_BY_CATEGORY = {
  queue: 'ContactCenter',
  role: 'PeoplePermissions',
  group: 'Groups',
  division: 'Directory',
}

const CATEGORY_LABELS = {
  queue: 'filas',
  role: 'roles',
  group: 'grupos',
}

/** Mensagens de empty ≠ erro (HTTP 200, sem matches). */
const EMPTY_MESSAGES = {
  division: 'Nenhuma alteração de divisão encontrada neste período para este usuário.',
  queue: 'Nenhuma alteração de fila encontrada neste período.',
  role: 'Nenhuma alteração de role encontrada neste período.',
  group: 'Nenhuma alteração de grupo encontrada neste período.',
}

const defaultEmptyHint =
  'Amplie o intervalo de datas ou confira se a pessoa está correta. A pesquisa padrão só traz divisão — use “Buscar filas”, “Buscar roles” ou “Buscar grupos” para incluir essas categorias.'

const searchBar = ref(null)
const changes = ref([])
const meta = ref(null)
const loadingBase = ref(false)
const loadingCategory = ref(null)
const searched = ref(false)
const error = ref('')
const fetchedDeepCategories = ref([])
const truncatedByCategory = ref({})
const queriedUsers = ref([])
const progressState = ref(null)
/** Última busca sem novos matches: { message, hint, category } | null */
const emptyNotice = ref(null)
/** AbortController da busca em voo; seq invalida handlers após cancel/supersede. */
let activeController = null
let searchSeq = 0

const anyTruncated = computed(() =>
  Object.values(truncatedByCategory.value).some(Boolean),
)

function isAbortError(err) {
  return err?.name === 'AbortError'
}

function abortActiveSearch() {
  if (activeController) {
    activeController.abort()
    activeController = null
  }
}

/** Cancela busca anterior (se houver) e retorna { signal, seq } da nova. */
function beginSearchRequest() {
  abortActiveSearch()
  const seq = ++searchSeq
  const controller = new AbortController()
  activeController = controller
  return { signal: controller.signal, seq }
}

function isStale(seq) {
  return seq !== searchSeq
}

function cancelSearch() {
  if (!loadingBase.value && !loadingCategory.value) return
  abortActiveSearch()
  searchSeq++
  loadingBase.value = false
  loadingCategory.value = null
  progressState.value = null
  error.value = ''
  addToast('Busca cancelada.', 'info')
}

function emptyHintFor(category) {
  if (category === 'division') return defaultEmptyHint
  return 'Amplie o intervalo de datas ou tente outra categoria. Isso não é um erro — só não há matches novos nesse período.'
}

function setEmptyNotice(category) {
  emptyNotice.value = {
    category,
    message: EMPTY_MESSAGES[category] || 'Nenhuma alteração encontrada neste período.',
    hint: emptyHintFor(category),
  }
}

function countNewCategoryMatches(incoming, category) {
  const existingKeys = new Set(
    changes.value
      .filter((c) => c?.category === category)
      .map((c) => `${c?.id || ''}_${c?.target_user?.id || ''}`),
  )
  let newCount = 0
  for (const c of incoming || []) {
    if (c?.category !== category) continue
    const key = `${c?.id || ''}_${c?.target_user?.id || ''}`
    if (c?.id) {
      if (!existingKeys.has(key)) {
        newCount++
        existingKeys.add(key)
      }
    } else {
      newCount++
    }
  }
  return newCount
}

function resetResults() {
  changes.value = []
  meta.value = null
  searched.value = false
  error.value = ''
  fetchedDeepCategories.value = []
  truncatedByCategory.value = {}
  emptyNotice.value = null
  queriedUsers.value = []
  progressState.value = null
}

function onClear() {
  resetResults()
}

function mergeChanges(incoming) {
  const byKey = new Map()
  const extras = []
  for (const c of changes.value) {
    const key = `${c?.id || ''}_${c?.target_user?.id || ''}`
    if (c?.id) byKey.set(key, c)
    else extras.push(c)
  }
  for (const c of incoming || []) {
    const key = `${c?.id || ''}_${c?.target_user?.id || ''}`
    if (c?.id) byKey.set(key, c)
    else extras.push(c)
  }
  const all = [...byKey.values(), ...extras]
  all.sort((a, b) => (b.event_date || '').localeCompare(a.event_date || ''))
  changes.value = all
}

function applyTruncationFromMeta(responseMeta, categoriesRan) {
  const bySvc = responseMeta?.truncated_by_service || {}
  const scanned = responseMeta?.scanned_by_service || {}
  const next = { ...truncatedByCategory.value }

  if (categoriesRan.length === 0) {
    // Busca base (divisão)
    const trunc =
      bySvc.Directory === true
      || scanned.Directory?.truncated === true
    next.division = trunc
  }
  for (const cat of categoriesRan) {
    const svc = SERVICE_BY_CATEGORY[cat]
    const trunc = bySvc[svc] === true || scanned[svc]?.truncated === true
    next[cat] = trunc
  }
  truncatedByCategory.value = next
}

function markFetchedDeep(categories) {
  const set = new Set(fetchedDeepCategories.value)
  for (const c of categories) set.add(c)
  fetchedDeepCategories.value = [...set]
}

async function runBaseSearch({ user, start, end }) {
  if (!user?.id && !user?.email) return
  const { signal, seq } = beginSearchRequest()
  loadingCategory.value = null
  loadingBase.value = true
  searched.value = true
  error.value = ''
  emptyNotice.value = null
  progressState.value = null
  queriedUsers.value = [user]
  // Nova pesquisa base substitui a lista (novo critério de pessoa/período)
  changes.value = []
  meta.value = null
  fetchedDeepCategories.value = []
  truncatedByCategory.value = {}

  try {
    const userRef = user.email || user.id
    const interval_start = datetimeLocalToIso(start)
    const interval_end = datetimeLocalToIso(end)

    const data = await getUserChanges(
      {
        user: userRef,
        interval_start,
        interval_end,
        deep_categories: [],
      },
      { signal },
    )
    if (isStale(seq)) return
    changes.value = data.changes || []
    meta.value = data.meta || null
    applyTruncationFromMeta(data.meta, [])
    if (!(data.changes || []).length) {
      setEmptyNotice('division')
    }
    if (data.user?.name || data.user?.email) {
      searchBar.value?.updateSelected({
        id: data.user.id || user.id,
        name: data.user.name || user.name,
        email: data.user.email || user.email || '',
      })
    }
  } catch (err) {
    if (isStale(seq) || isAbortError(err)) return
    error.value = err.message
    emptyNotice.value = null
    addToast(err.message, 'error')
  } finally {
    if (!isStale(seq)) {
      loadingBase.value = false
      activeController = null
    }
  }
}

async function runDeepSearch({ user, users, start, end, category }) {
  const userList = users && users.length ? users : (user ? [user] : [])
  if (!userList.length || !category) return

  const { signal, seq } = beginSearchRequest()
  loadingBase.value = false
  loadingCategory.value = category
  searched.value = true
  error.value = ''
  emptyNotice.value = null
  queriedUsers.value = userList

  progressState.value = {
    serviceLabel: CATEGORY_LABELS[category] || category,
    chunk: 1,
    totalChunks: 1,
    percent: 5,
    scanned: 0,
    matched: 0,
    dateLabel: '',
    currentMessage: 'Iniciando varredura na Genesys...',
    steps: [],
  }

  try {
    const interval_start = datetimeLocalToIso(start)
    const interval_end = datetimeLocalToIso(end)

    const payload = {
      users: userList.map((u) => u.email || u.id),
      interval_start,
      interval_end,
      deep_categories: [category],
    }

    const data = await streamUserChanges(
      payload,
      (ev) => {
        if (isStale(seq)) return
        const now = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
        if (ev.type === 'init') {
          if (progressState.value) {
            progressState.value.totalChunks = ev.total_chunks || 1
            progressState.value.currentMessage = 'Varredura inicializada...'
            progressState.value.steps.push({
              time: now,
              message: `Varredura configurada: ${ev.total_chunks || 1} janela(s) de tempo para ${userList.length} pessoa(s).`,
              stage: 'init',
            })
          }
        } else if (ev.type === 'step') {
          if (progressState.value) {
            progressState.value.currentMessage = ev.message
            if (ev.scanned != null) progressState.value.scanned = ev.scanned
            if (ev.matched != null) progressState.value.matched = ev.matched
            if (ev.chunk) progressState.value.chunk = ev.chunk
            if (ev.total_chunks) progressState.value.totalChunks = ev.total_chunks

            const chunkIndex = Math.max(0, (progressState.value.chunk || 1) - 1)
            const total = Math.max(1, progressState.value.totalChunks || 1)
            const chunkBase = (chunkIndex / total) * 100
            const chunkWeight = (1 / total) * 100

            let stageFrac = 0.1
            if (ev.stage === 'resolving_users') stageFrac = 0.08
            else if (ev.stage === 'users_resolved') stageFrac = 0.15
            else if (ev.stage === 'loading_catalogs') stageFrac = 0.25
            else if (ev.stage === 'create_query') stageFrac = 0.35
            else if (ev.stage === 'polling') stageFrac = Math.min(0.60, 0.35 + (ev.attempt || 1) * 0.02)
            else if (ev.stage === 'query_ready') stageFrac = 0.65
            else if (ev.stage === 'fetching_page') stageFrac = Math.min(0.85, 0.65 + (ev.page || 1) * 0.05)
            else if (ev.stage === 'page_analyzed') stageFrac = Math.min(0.92, 0.70 + (ev.page || 1) * 0.05)
            else if (ev.stage === 'formatting_cards') stageFrac = 0.96

            const calcPercent = Math.min(99, Math.round(chunkBase + chunkWeight * stageFrac))
            progressState.value.percent = Math.max(progressState.value.percent, calcPercent)

            if (['users_resolved', 'create_query', 'query_ready', 'page_analyzed', 'formatting_cards', 'resolving_group_directions'].includes(ev.stage)) {
              progressState.value.steps.push({
                time: now,
                message: ev.message,
                stage: ev.stage,
              })
            }
          }
        } else if (ev.type === 'progress') {
          if (progressState.value) {
            const chunk = ev.chunk || 1
            const total = ev.total_chunks || progressState.value.totalChunks || 1
            progressState.value.chunk = chunk
            progressState.value.totalChunks = total
            progressState.value.percent = Math.min(100, Math.round((chunk / total) * 100))
            if (ev.scanned != null) progressState.value.scanned = ev.scanned
            if (ev.matched != null) progressState.value.matched = ev.matched
            if (ev.start) {
              const d = new Date(ev.start)
              progressState.value.dateLabel = d.toLocaleDateString('pt-BR')
            }
            progressState.value.steps.push({
              time: now,
              message: ev.message || `Janela ${chunk} de ${total} concluída.`,
              stage: 'chunk_done',
            })
          }
        }
      },
      { signal },
    )

    if (isStale(seq)) return
    const incoming = data?.changes || []
    const hadOtherResults = changes.value.length > 0
    const newMatches = countNewCategoryMatches(incoming, category)
    mergeChanges(incoming)
    meta.value = data?.meta || null
    markFetchedDeep([category])
    applyTruncationFromMeta(data?.meta, [category])
    if (data?.meta?.truncated) {
      addToast(
        `Varredura parcial em ${CATEGORY_LABELS[category] || category}: parte do histórico pode faltar.`,
        'warning',
      )
    }
    if (newMatches === 0) {
      setEmptyNotice(category)
      // Com lista já preenchida: toast + banner. Lista vazia: só empty state.
      if (hadOtherResults) {
        addToast(
          EMPTY_MESSAGES[category] || 'Nenhuma alteração encontrada neste período.',
          'info',
        )
      }
    }
  } catch (err) {
    if (isStale(seq) || isAbortError(err)) return
    error.value = err.message
    emptyNotice.value = null
    addToast(err.message, 'error')
  } finally {
    if (!isStale(seq)) {
      loadingCategory.value = null
      progressState.value = null
      activeController = null
    }
  }
}
</script>
