<template>
  <div class="space-y-5">
    <div class="mb-1">
      <h1 class="text-2xl font-bold text-ink tracking-tight">Trilha de Auditoria</h1>
      <p class="text-sm text-gray-500 mt-1">
        Comece pela divisão (rápido). Depois, se precisar, busque filas, roles ou grupos
        separadamente — cada busca profunda varre a organização naquele serviço.
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

    <!-- Feedback de busca vazia com lista já preenchida (ex.: deep sem matches novos) -->
    <div
      v-if="emptyNotice && changes.length && !error && !loadingBase && !loadingCategory"
      class="rounded-xl border border-gray-200 bg-white px-3.5 py-2.5 text-sm text-gray-600"
      role="status"
      data-testid="empty-notice-banner"
    >
      {{ emptyNotice.message }}
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
    />
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { getUserChanges } from '../api/audits'
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
  const existingIds = new Set(
    changes.value
      .filter((c) => c?.category === category && c?.id)
      .map((c) => c.id),
  )
  let newCount = 0
  for (const c of incoming || []) {
    if (c?.category !== category) continue
    if (c?.id) {
      if (!existingIds.has(c.id)) {
        newCount++
        existingIds.add(c.id)
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
}

function onClear() {
  resetResults()
}

function mergeChanges(incoming) {
  const byId = new Map()
  const extras = []
  for (const c of changes.value) {
    if (c?.id) byId.set(c.id, c)
    else extras.push(c)
  }
  for (const c of incoming || []) {
    if (c?.id) byId.set(c.id, c)
    else extras.push(c)
  }
  const all = [...byId.values(), ...extras]
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

async function runDeepSearch({ user, start, end, category }) {
  if (!user?.id && !user?.email || !category) return
  const { signal, seq } = beginSearchRequest()
  loadingBase.value = false
  loadingCategory.value = category
  searched.value = true
  error.value = ''
  emptyNotice.value = null

  try {
    const userRef = user.email || user.id
    const interval_start = datetimeLocalToIso(start)
    const interval_end = datetimeLocalToIso(end)

    const data = await getUserChanges(
      {
        user: userRef,
        interval_start,
        interval_end,
        deep_categories: [category],
      },
      { signal },
    )
    if (isStale(seq)) return
    const incoming = data.changes || []
    const hadOtherResults = changes.value.length > 0
    const newMatches = countNewCategoryMatches(incoming, category)
    mergeChanges(incoming)
    meta.value = data.meta || null
    markFetchedDeep([category])
    applyTruncationFromMeta(data.meta, [category])
    if (data.meta?.truncated) {
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
      loadingCategory.value = null
      activeController = null
    }
  }
}

</script>
