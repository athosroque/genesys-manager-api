<template>
  <div :class="mode === 'person' && entities.length ? 'max-w-7xl' : 'max-w-5xl'" class="mx-auto space-y-5">
    <!-- Cabeçalho -->
    <div class="mb-1 flex items-end justify-between flex-wrap gap-3">
      <div>
        <p class="text-xs font-semibold uppercase tracking-widest text-blue-400">Governança</p>
        <h1 class="text-2xl font-bold text-white tracking-tight">Trilha de Auditoria</h1>
        <p class="text-sm text-gray-400 mt-1">
          Quem mudou o quê, quando — usuários, filas, roles e permissões da org Genesys Cloud.
        </p>
      </div>
      <span
        v-if="entities.length"
        class="text-xs font-medium text-gray-400 bg-gray-800 rounded-full px-3 py-1"
      >
        {{ filteredEntities.length }} de {{ entities.length }} eventos
      </span>
    </div>

    <!-- Tabs de modo -->
    <div class="inline-flex rounded-lg bg-gray-800/80 p-1">
      <button
        v-for="tab in [
          { id: 'filters', label: 'Por filtros' },
          { id: 'person', label: 'Por pessoa' },
        ]"
        :key="tab.id"
        type="button"
        class="px-4 py-1.5 rounded-md text-sm font-medium transition-colors"
        :class="mode === tab.id
          ? 'bg-blue-600 text-white shadow'
          : 'text-gray-400 hover:text-gray-200'"
        @click="setMode(tab.id)"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- ══════════ Modo: por filtros ══════════ -->
    <section
      v-if="mode === 'filters'"
      class="rounded-xl border border-gray-700 bg-gray-900/80 divide-y divide-gray-800"
    >
      <div class="p-5 space-y-3">
        <p class="section-label">O que consultar</p>
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
          <label class="md:col-span-2 block">
            <span class="text-xs text-gray-500">Serviço</span>
            <select v-model="form.serviceName" class="input mt-1.5" @change="onServiceChange">
              <option disabled value="">Selecione…</option>
              <option v-for="s in services" :key="s.name" :value="s.name">{{ s.name }}</option>
            </select>
          </label>

          <label class="block">
            <span class="text-xs text-gray-500">Entidade</span>
            <select v-model="form.entityType" class="input mt-1.5" :disabled="!form.serviceName">
              <option value="">Todas</option>
              <option v-for="e in entityOptions" :key="e.name" :value="e.name">{{ e.name }}</option>
            </select>
          </label>

          <label class="block">
            <span class="text-xs text-gray-500">Ação</span>
            <select v-model="form.action" class="input mt-1.5" :disabled="!form.entityType">
              <option value="">Todas</option>
              <option v-for="a in actionOptions" :key="a" :value="a">{{ a }}</option>
            </select>
          </label>
        </div>
      </div>

      <div class="p-5 space-y-3">
        <div class="flex items-center justify-between flex-wrap gap-2">
          <p class="section-label">Período</p>
          <div class="flex gap-1.5">
            <button
              v-for="p in PERIOD_PRESETS"
              :key="p.label"
              type="button"
              class="preset-btn"
              @click="setPeriod(form, p.days)"
            >
              {{ p.label }}
            </button>
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-xl">
          <label class="block">
            <span class="text-xs text-gray-500">De</span>
            <input v-model="form.start" type="datetime-local" class="input mt-1.5" />
          </label>
          <label class="block">
            <span class="text-xs text-gray-500">Até</span>
            <input v-model="form.end" type="datetime-local" class="input mt-1.5" />
          </label>
        </div>
      </div>

      <div class="p-5 flex flex-wrap items-center gap-3">
        <button
          class="btn-primary"
          :disabled="!form.serviceName || loading"
          @click="search"
        >
          {{ loading ? 'Consultando…' : 'Pesquisar auditoria' }}
        </button>
        <p v-if="error" class="text-sm text-red-400 font-medium">{{ error }}</p>
      </div>
    </section>

    <!-- ══════════ Modo: por pessoa ══════════ -->
    <section
      v-else
      class="rounded-xl border border-gray-700 bg-gray-900/80 divide-y divide-gray-800"
    >
      <!-- 1. Pessoa -->
      <div class="p-5 space-y-3">
        <p class="section-label">Pessoa</p>
        <div class="relative max-w-2xl">
          <input
            v-model="personQuery"
            type="text"
            placeholder="Nome, e-mail ou UUID — digite 2+ letras, ou Enter com e-mail/UUID completo"
            class="input"
            @keydown.enter="selectPersonByExactQuery"
          />
          <ul
            v-if="personSuggestions.length"
            class="absolute z-20 mt-1 w-full max-h-56 overflow-y-auto rounded-lg border border-gray-700 bg-gray-900 shadow-xl"
          >
            <li
              v-for="u in personSuggestions"
              :key="u.id"
              class="px-3 py-2 text-sm text-gray-200 hover:bg-gray-800 cursor-pointer"
              @click="selectPerson(u)"
            >
              <p class="font-medium">{{ u.name }}</p>
              <p class="text-xs text-gray-500">{{ u.email }} · {{ u.state }}</p>
            </li>
          </ul>
        </div>

        <!-- Confirmação da pessoa selecionada -->
        <div
          v-if="personSelected"
          class="flex items-center gap-3 rounded-lg border border-green-800/40 bg-green-900/10 px-3 py-2 max-w-2xl"
        >
          <span
            class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-green-700
                   text-xs font-bold text-white"
          >
            {{ initialsOf(personSelected.name) }}
          </span>
          <div class="min-w-0 flex-1">
            <p class="text-sm font-medium text-green-300 truncate">{{ personSelected.name }}</p>
            <p class="text-xs text-gray-500 font-mono truncate">
              {{ personSelected.email || personSelected.id }}
            </p>
          </div>
          <button
            type="button"
            class="text-gray-500 hover:text-gray-200 text-lg leading-none px-1"
            title="Remover seleção"
            @click="clearPerson"
          >
            ×
          </button>
        </div>
      </div>

      <!-- 2. Direção -->
      <div class="p-5 space-y-3">
        <p class="section-label">Direção da investigação</p>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-2xl">
          <button
            type="button"
            class="direction-card"
            :class="direction === 'did' ? 'direction-active' : 'direction-idle'"
            @click="direction = 'did'"
          >
            <p class="text-sm font-semibold">O que a pessoa fez</p>
            <p class="text-xs text-gray-500 mt-0.5">Eventos em que ela é a autora da mudança</p>
          </button>
          <button
            type="button"
            class="direction-card"
            :class="direction === 'target' ? 'direction-active' : 'direction-idle'"
            @click="direction = 'target'"
          >
            <p class="text-sm font-semibold">O que fizeram com a pessoa</p>
            <p class="text-xs text-gray-500 mt-0.5">Eventos em que ela é o alvo da mudança</p>
          </button>
        </div>
        <label
          v-if="direction === 'target'"
          class="flex items-center gap-2 text-xs text-gray-400 max-w-2xl"
        >
          <input type="checkbox" v-model="deepSearch" />
          Busca profunda — mais lenta, mas encontra entrada/saída de filas e roles
          (onde o UUID da pessoa fica embutido no evento)
        </label>
      </div>

      <!-- 3. Período -->
      <div class="p-5 space-y-3">
        <div class="flex items-center justify-between flex-wrap gap-2 max-w-xl">
          <p class="section-label">Período</p>
          <div class="flex gap-1.5">
            <button
              v-for="p in PERIOD_PRESETS"
              :key="p.label"
              type="button"
              class="preset-btn"
              @click="setPeriod(personPeriod, p.days)"
            >
              {{ p.label }}
            </button>
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-xl">
          <label class="block">
            <span class="text-xs text-gray-500">De</span>
            <input v-model="personPeriod.start" type="datetime-local" class="input mt-1.5" />
          </label>
          <label class="block">
            <span class="text-xs text-gray-500">Até</span>
            <input v-model="personPeriod.end" type="datetime-local" class="input mt-1.5" />
          </label>
        </div>
      </div>

      <!-- 4. Serviços -->
      <div class="p-5 space-y-3">
        <div class="flex items-center justify-between flex-wrap gap-2">
          <p class="section-label">
            Serviços a consultar
            <span class="ml-1 normal-case tracking-normal font-medium text-gray-500">
              · {{ selectedServices.length }} selecionado{{ selectedServices.length === 1 ? '' : 's' }}
            </span>
          </p>
          <div class="flex gap-3 text-xs">
            <button class="link-btn" @click="selectCuratedServices">essenciais</button>
            <button class="link-btn" @click="selectAllServices">marcar todos</button>
            <button class="link-btn" @click="selectedServices = []">limpar</button>
          </div>
        </div>

        <!-- Serviços com eventos confirmados na org, sempre visíveis -->
        <div>
          <p class="text-[11px] text-gray-500 mb-1.5">Com eventos na org:</p>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="s in curatedServices"
              :key="s.name"
              type="button"
              class="service-chip"
              :class="selectedServices.includes(s.name) ? 'chip-on' : 'chip-off'"
              @click="toggleService(s.name)"
            >
              <span v-if="selectedServices.includes(s.name)" class="mr-1">✓</span>{{ s.name }}
            </button>
          </div>
        </div>

        <!-- Demais serviços, colapsados por padrão -->
        <div v-if="otherServices.length">
          <button
            type="button"
            class="link-btn text-xs flex items-center gap-1"
            @click="showAllServices = !showAllServices"
          >
            <svg
              class="h-3 w-3 transition-transform"
              :class="{ 'rotate-180': showAllServices }"
              viewBox="0 0 20 20" fill="currentColor"
            >
              <path fill-rule="evenodd" clip-rule="evenodd"
                d="M5.3 7.3a1 1 0 011.4 0L10 10.6l3.3-3.3a1 1 0 111.4 1.4l-4 4a1 1 0 01-1.4 0l-4-4a1 1 0 010-1.4z" />
            </svg>
            {{ showAllServices ? 'ocultar' : 'mostrar' }} os demais serviços ({{ otherServices.length }})
          </button>
          <div v-if="showAllServices" class="mt-2 flex flex-wrap gap-2">
            <button
              v-for="s in otherServices"
              :key="s.name"
              type="button"
              class="service-chip"
              :class="selectedServices.includes(s.name) ? 'chip-on' : 'chip-off'"
              @click="toggleService(s.name)"
            >
              <span v-if="selectedServices.includes(s.name)" class="mr-1">✓</span>{{ s.name }}
            </button>
          </div>
        </div>
      </div>

      <div class="p-5 flex flex-wrap items-center gap-3">
        <button
          class="btn-primary"
          :disabled="!personSelected || !selectedServices.length || personSearching"
          @click="runPersonSearch"
        >
          {{ personSearching ? 'Consultando…' : 'Pesquisar auditoria da pessoa' }}
        </button>
        <p v-if="error" class="text-sm text-red-400 font-medium">{{ error }}</p>
      </div>
    </section>

    <!-- ══════════ Resultados ══════════ -->

    <!-- Progresso por serviço (modo pessoa): stat cards -->
    <div
      v-if="mode === 'person' && Object.keys(serviceStatuses).length"
      class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3"
    >
      <div
        v-for="(st, name) in serviceStatuses"
        :key="name"
        class="rounded-xl border px-3 py-2.5"
        :class="statCardClass(st)"
      >
        <p class="text-xs text-gray-400 truncate" :title="name">{{ name }}</p>
        <div class="mt-1 flex items-baseline gap-2">
          <span
            v-if="st.status === 'loading'"
            class="h-4 w-4 rounded-full border-2 border-blue-500/40 border-t-blue-400 animate-spin"
          ></span>
          <template v-else-if="st.status === 'done'">
            <span class="text-lg font-bold" :class="st.count ? 'text-gray-100' : 'text-gray-600'">
              {{ st.count }}
            </span>
            <span class="text-xs text-gray-500">evento{{ st.count === 1 ? '' : 's' }}</span>
            <span v-if="st.truncated" class="text-[10px] text-amber-400" title="Resultado truncado — reduza o período">
              truncado
            </span>
          </template>
          <span v-else-if="st.status === 'error'" class="text-xs text-red-400 truncate" :title="st.error">
            erro: {{ st.error }}
          </span>
        </div>
      </div>
    </div>

    <!-- Toolbar de exibição: filtro de nível + legenda + filtro rápido -->
    <section
      v-if="entities.length"
      class="rounded-xl border border-gray-800 bg-gray-900/60 px-4 py-3
             flex flex-wrap items-center gap-x-5 gap-y-3"
    >
      <div class="inline-flex rounded-lg bg-gray-800 p-0.5 text-xs font-medium">
        <button
          v-for="opt in levelOptions"
          :key="opt.id"
          type="button"
          class="px-3 py-1.5 rounded-md transition-colors"
          :class="levelFilter === opt.id ? 'bg-gray-600 text-white' : 'text-gray-400 hover:text-gray-200'"
          @click="levelFilter = opt.id"
        >
          {{ opt.label }} <span class="opacity-60">{{ opt.count }}</span>
        </button>
      </div>

      <!-- Legenda por tipo de ação, cores iguais aos dots da timeline -->
      <div class="flex items-center gap-3 text-xs text-gray-400">
        <span v-for="k in kindLegend" :key="k.label" class="flex items-center gap-1.5">
          <span class="h-2 w-2 rounded-full" :class="k.dot"></span>
          {{ k.count }} {{ k.label }}
        </span>
      </div>

      <input
        v-model="quickFilter"
        type="search"
        placeholder="Filtrar resultados…"
        class="input max-w-xs ml-auto !py-1.5"
      />
    </section>

    <!-- Skeleton -->
    <div v-if="busy && !entities.length" class="space-y-3">
      <div v-for="i in 4" :key="i" class="h-16 rounded-xl bg-gray-800/60 animate-pulse"></div>
    </div>

    <!-- Vazio (busca sem resultados) -->
    <div
      v-else-if="hasSearched && !entities.length"
      class="rounded-xl border border-dashed border-gray-700 p-10 text-center"
    >
      <svg class="mx-auto h-10 w-10 text-gray-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="11" cy="11" r="7" />
        <path d="M21 21l-4.3-4.3" stroke-linecap="round" />
      </svg>
      <p class="mt-3 text-gray-300 font-semibold">Nenhum evento encontrado.</p>
      <p class="text-sm text-gray-500 mt-1">
        Amplie o intervalo de datas ou revise os filtros/serviços selecionados.
      </p>
    </div>

    <!-- Timeline -->
    <section v-else-if="entities.length" class="space-y-8">
      <AuditTimeline v-if="mode === 'filters'" :entities="filteredEntities" :known-names="knownNames" />

      <!-- Por pessoa: colunas por serviço -->
      <div
        v-else
        class="grid gap-4 items-start grid-cols-1 md:grid-cols-[repeat(2,minmax(320px,1fr))] min-[1100px]:grid-cols-[repeat(3,minmax(320px,1fr))]"
      >
        <div
          v-for="group in entitiesByService"
          :key="group.serviceName"
          class="min-w-0 rounded-xl border border-gray-800 bg-gray-900/40 p-3"
        >
          <div class="flex items-center justify-between mb-3">
            <h3 class="text-sm font-bold text-gray-200 truncate" :title="group.serviceName">
              {{ group.serviceName }}
            </h3>
            <span class="shrink-0 text-xs font-medium text-gray-500 bg-gray-800 rounded-full px-2 py-0.5">
              {{ group.entities.length }} evento{{ group.entities.length === 1 ? '' : 's' }}
            </span>
          </div>
          <AuditTimeline :entities="group.entities" :known-names="knownNames" />
        </div>
      </div>

      <p
        v-if="!filteredEntities.length"
        class="rounded-xl border border-dashed border-gray-700 p-6 text-center text-sm text-gray-500"
      >
        Nenhum evento com os filtros de exibição atuais — limpe o filtro rápido
        ou volte para “Todos”.
      </p>

      <div v-if="mode === 'filters'" class="flex justify-center">
        <button
          v-if="cursor"
          class="rounded-lg border border-gray-700 bg-gray-900 px-5 py-2 text-sm font-semibold
                 text-gray-300 hover:bg-gray-800 disabled:opacity-40 transition"
          :disabled="loadingMore"
          @click="loadMore"
        >
          {{ loadingMore ? 'Carregando…' : 'Carregar mais eventos' }}
        </button>
        <p v-else class="text-xs text-gray-600">Fim dos resultados para este período.</p>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getAuditServices, searchAudits, getAuditResults, deepSearchAudits } from '../api/audits'
import { autocompleteUsers, searchUser } from '../api/genesys'
import { useToast } from '../composables/useToast'
import { actionKind } from '../utils/auditFormat'
import AuditTimeline from '../components/AuditTimeline.vue'

const { addToast } = useToast()
const route = useRoute()

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

// Confirmado empiricamente (explorar_auditoria.py) como os serviços mais
// relevantes para "governança de pessoas" na org — ficam em destaque; os
// demais colapsam atrás do toggle "mostrar os demais serviços".
const CURATED_SERVICES = ['PeoplePermissions', 'ContactCenter', 'Directory', 'Groups']

// Combos onde o UUID da pessoa está embutido em campos sem filtro nativo
// (ver _event_matches no backend). Únicos confirmados via amostragem real.
const DEEP_COMBOS = [
  { service: 'PeoplePermissions', entityType: 'Role' },
  { service: 'ContactCenter', entityType: 'Queue' },
]

const PERIOD_PRESETS = [
  { label: '24h', days: 1 },
  { label: '7 dias', days: 7 },
  { label: '30 dias', days: 30 },
]

const mode = ref('filters') // 'filters' | 'person'
const services = ref([])
const entities = ref([])
const cursor = ref(null)
const transactionId = ref(null)
const quickFilter = ref('')
const levelFilter = ref('all') // 'all' | 'user' | 'system'
const loading = ref(false)
const loadingMore = ref(false)
const searched = ref(false)
const error = ref('')

const form = reactive({
  serviceName: '',
  entityType: '',
  action: '',
  start: defaultStart(),
  end: defaultEnd(),
})

// --- modo "Por pessoa" ---
const personQuery = ref('')
const personSuggestions = ref([])
const personSelected = ref(null) // { id, name, email }
const direction = ref('did') // 'did' -> UserId | 'target' -> EntityId
const deepSearch = ref(false)
const personPeriod = reactive({ start: defaultStart(), end: defaultEnd() })
const selectedServices = ref([...CURATED_SERVICES])
const showAllServices = ref(false)
const serviceStatuses = ref({})
const personSearching = ref(false)
const personSearched = ref(false)

let suppressQueryWatch = false
let debounceTimer = null

const busy = computed(() => (mode.value === 'filters' ? loading.value : personSearching.value))
const hasSearched = computed(() => (mode.value === 'filters' ? searched.value : personSearched.value))

// datetime-local espera horário local — corrige o offset antes do slice
function toLocalInput(ts) {
  const d = new Date(ts)
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset())
  return d.toISOString().slice(0, 16)
}
function defaultStart() {
  return toLocalInput(Date.now() - 7 * 864e5)
}
function defaultEnd() {
  return toLocalInput(Date.now())
}
function setPeriod(target, days) {
  target.start = toLocalInput(Date.now() - days * 864e5)
  target.end = toLocalInput(Date.now())
}

function setMode(m) {
  mode.value = m
  entities.value = []
  cursor.value = null
  error.value = ''
  searched.value = false
  personSearched.value = false
  serviceStatuses.value = {}
  quickFilter.value = ''
  levelFilter.value = 'all'
}

onMounted(async () => {
  try {
    const data = await getAuditServices()
    services.value = data.services || []
  } catch (err) {
    error.value = 'Não foi possível carregar os serviços de auditoria.'
    addToast(error.value, 'error')
  }

  const qUserId = route.query.userId
  if (qUserId) {
    mode.value = 'person'
    const name = route.query.name || qUserId
    // O card de confirmação já exibe a pessoa — o input fica livre p/ nova busca
    personSelected.value = { id: qUserId, name, email: '' }
    await runPersonSearch()
  }
})

const entityOptions = computed(
  () => services.value.find((s) => s.name === form.serviceName)?.entities || [],
)
const actionOptions = computed(
  () => entityOptions.value.find((e) => e.name === form.entityType)?.actions || [],
)

const curatedServices = computed(() =>
  services.value.filter((s) => CURATED_SERVICES.includes(s.name)),
)
const otherServices = computed(() =>
  services.value
    .filter((s) => !CURATED_SERVICES.includes(s.name))
    .sort((a, b) => a.name.localeCompare(b.name)),
)

// Nomes já conhecidos → alimentam o cache de resolução UUID→nome da timeline
const knownNames = computed(() =>
  personSelected.value?.id && personSelected.value?.name
    ? { [personSelected.value.id]: personSelected.value.name }
    : {},
)

function onServiceChange() {
  form.entityType = ''
  form.action = ''
}

async function search() {
  loading.value = true
  error.value = ''
  entities.value = []
  cursor.value = null
  try {
    const filters = []
    if (form.entityType) filters.push({ property: 'EntityType', value: form.entityType })
    if (form.action) filters.push({ property: 'Action', value: form.action })

    const data = await searchAudits({
      interval_start: new Date(form.start).toISOString(),
      interval_end: new Date(form.end).toISOString(),
      service_name: form.serviceName,
      filters,
      page_size: 200,
    })
    transactionId.value = data.transactionId
    cursor.value = data.cursor || null
    entities.value = data.entities || []
  } catch (err) {
    error.value = err.message
    addToast(err.message, 'error')
  } finally {
    loading.value = false
    searched.value = true
  }
}

async function loadMore() {
  if (!cursor.value || !transactionId.value) return
  loadingMore.value = true
  try {
    const data = await getAuditResults(transactionId.value, cursor.value, 200)
    entities.value.push(...(data.entities || []))
    cursor.value = data.cursor || null
  } catch (err) {
    error.value = err.message
    addToast(err.message, 'error')
  } finally {
    loadingMore.value = false
  }
}

// --- Por pessoa: autocomplete ---
watch(personQuery, (q) => {
  if (suppressQueryWatch) {
    suppressQueryWatch = false
    return
  }
  clearTimeout(debounceTimer)
  personSelected.value = null
  const trimmed = q.trim()
  if (trimmed.length < 2 || UUID_RE.test(trimmed.replace(/[{}]/g, ''))) {
    personSuggestions.value = []
    return
  }
  debounceTimer = setTimeout(async () => {
    try {
      const data = await autocompleteUsers(trimmed)
      personSuggestions.value = data.results || []
    } catch {
      personSuggestions.value = []
    }
  }, 300)
})

function selectPerson(u) {
  personSelected.value = u
  // Só suprime o watcher se o input realmente mudar (senão o flag ficaria
  // pendurado e engoliria a próxima digitação)
  if (personQuery.value !== '') {
    suppressQueryWatch = true
    personQuery.value = ''
  }
  personSuggestions.value = []
}

function clearPerson() {
  personSelected.value = null
  personQuery.value = ''
  personSuggestions.value = []
}

const initialsOf = (name) =>
  name ? name.split(' ').map((p) => p[0]).slice(0, 2).join('').toUpperCase() : '?'

async function selectPersonByExactQuery() {
  const raw = personQuery.value.trim()
  const clean = raw.replace(/[{}]/g, '')
  const isUuid = UUID_RE.test(clean)
  const isEmail = raw.includes('@')
  // Fallback para busca exata (UUID ou e-mail) via /users/search, independente
  // do autocomplete por CONTAINS estar disponível ou não.
  if (!isUuid && !isEmail) return
  try {
    const data = await searchUser(isUuid ? clean : raw)
    if (data.found) {
      selectPerson({ id: data.user.id, name: data.user.name, email: data.user.email })
    } else {
      error.value = isUuid ? 'UUID não encontrado.' : 'E-mail não encontrado.'
    }
  } catch (err) {
    error.value = err.message
    addToast(err.message, 'error')
  }
}

function toggleService(name) {
  const i = selectedServices.value.indexOf(name)
  if (i >= 0) selectedServices.value.splice(i, 1)
  else selectedServices.value.push(name)
}
function selectAllServices() {
  selectedServices.value = services.value.map((s) => s.name)
}
function selectCuratedServices() {
  selectedServices.value = [...CURATED_SERVICES]
}

async function runPool(items, limit, worker) {
  let idx = 0
  async function next() {
    if (idx >= items.length) return
    const item = items[idx++]
    await worker(item)
    return next()
  }
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, next))
}

async function fetchAllPages(serviceName, filters, intervalStart, intervalEnd, maxPages = 5) {
  const first = await searchAudits({
    interval_start: intervalStart,
    interval_end: intervalEnd,
    service_name: serviceName,
    filters,
    page_size: 500,
  })
  const collected = [...(first.entities || [])]
  let cursorVal = first.cursor
  const tid = first.transactionId
  let page = 1
  while (cursorVal && page < maxPages) {
    const next = await getAuditResults(tid, cursorVal, 500)
    collected.push(...(next.entities || []))
    cursorVal = next.cursor
    page++
  }
  return { entities: collected, truncated: !!cursorVal }
}

function mergeEntities(list) {
  const map = new Map()
  for (const ev of list) map.set(ev.id, ev)
  return [...map.values()].sort((a, b) => (b.eventDate || '').localeCompare(a.eventDate || ''))
}

function statCardClass(st) {
  if (st.status === 'loading') return 'border-blue-800/40 bg-blue-900/10'
  if (st.status === 'error') return 'border-red-800/40 bg-red-900/10'
  if (st.status === 'done' && !st.count) return 'border-gray-800 bg-gray-900/40 opacity-60'
  return 'border-gray-700 bg-gray-900/80'
}

async function runPersonSearch() {
  if (!personSelected.value) return
  personSearching.value = true
  personSearched.value = true
  error.value = ''
  const collected = []

  const statuses = {}
  for (const s of selectedServices.value) statuses[s] = { status: 'loading' }
  const runDeep = direction.value === 'target' && deepSearch.value
  if (runDeep) {
    for (const c of DEEP_COMBOS) statuses[`${c.service}/${c.entityType} (profunda)`] = { status: 'loading' }
  }
  serviceStatuses.value = statuses
  entities.value = []

  const intervalStart = new Date(personPeriod.start).toISOString()
  const intervalEnd = new Date(personPeriod.end).toISOString()
  const filterProperty = direction.value === 'did' ? 'UserId' : 'EntityId'

  await runPool(selectedServices.value, 3, async (svc) => {
    try {
      const { entities: evs, truncated } = await fetchAllPages(
        svc,
        [{ property: filterProperty, value: personSelected.value.id }],
        intervalStart,
        intervalEnd,
      )
      collected.push(...evs)
      serviceStatuses.value = { ...serviceStatuses.value, [svc]: { status: 'done', count: evs.length, truncated } }
    } catch (err) {
      serviceStatuses.value = { ...serviceStatuses.value, [svc]: { status: 'error', error: err.message } }
    }
    entities.value = mergeEntities(collected)
  })

  if (runDeep) {
    await runPool(DEEP_COMBOS, 2, async (combo) => {
      const key = `${combo.service}/${combo.entityType} (profunda)`
      try {
        const data = await deepSearchAudits({
          interval_start: intervalStart,
          interval_end: intervalEnd,
          service_name: combo.service,
          filters: [{ property: 'EntityType', value: combo.entityType }],
          match_value: personSelected.value.id,
          page_size: 500,
          max_pages: 10,
        })
        collected.push(...(data.entities || []))
        serviceStatuses.value = {
          ...serviceStatuses.value,
          [key]: { status: 'done', count: (data.entities || []).length, truncated: data.truncated },
        }
      } catch (err) {
        serviceStatuses.value = { ...serviceStatuses.value, [key]: { status: 'error', error: err.message } }
      }
      entities.value = mergeEntities(collected)
    })
  }

  personSearching.value = false
}

// --- Exibição: filtros sobre os eventos carregados ---

const userCount = computed(() => entities.value.filter((ev) => ev.level === 'USER').length)
const systemCount = computed(() => entities.value.length - userCount.value)

const levelOptions = computed(() => [
  { id: 'all', label: 'Todos', count: entities.value.length },
  { id: 'user', label: 'Ação humana', count: userCount.value },
  { id: 'system', label: 'Sistema', count: systemCount.value },
])

const KIND_LEGEND_META = [
  { kind: 'create', label: 'criações', dot: 'bg-green-500' },
  { kind: 'update', label: 'atualizações', dot: 'bg-blue-500' },
  { kind: 'delete', label: 'remoções', dot: 'bg-red-500' },
  { kind: 'other', label: 'outras', dot: 'bg-gray-500' },
]
const kindLegend = computed(() => {
  const counts = { create: 0, update: 0, delete: 0, other: 0 }
  for (const ev of entities.value) counts[actionKind(ev.action)]++
  return KIND_LEGEND_META.filter((k) => counts[k.kind]).map((k) => ({ ...k, count: counts[k.kind] }))
})

const filteredEntities = computed(() => {
  let list = entities.value
  if (levelFilter.value === 'user') list = list.filter((ev) => ev.level === 'USER')
  else if (levelFilter.value === 'system') list = list.filter((ev) => ev.level !== 'USER')

  const q = quickFilter.value.trim().toLowerCase()
  if (!q) return list
  return list.filter((ev) =>
    [ev.user?.name, ev.action, ev.entityType, ev.entity?.name, ev.entity?.id, ev.serviceName]
      .filter(Boolean)
      .some((v) => String(v).toLowerCase().includes(q)),
  )
})

// Resultados "Por pessoa" em colunas por serviço — cada serviço presente
// ganha coluna própria (curados primeiro na ordem de sempre, demais em ordem
// alfabética). Constrói sobre filteredEntities (não entities.value bruto),
// então levelFilter/quickFilter continuam valendo antes das colunas serem
// montadas; sem re-sort dentro de cada grupo (já vem mais-recente-primeiro).
const entitiesByService = computed(() => {
  const groups = new Map()
  for (const ev of filteredEntities.value) {
    const key = ev.serviceName || 'Outros'
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key).push(ev)
  }
  const priority = (name) => {
    const i = CURATED_SERVICES.indexOf(name)
    return i === -1 ? CURATED_SERVICES.length : i
  }
  return [...groups.entries()]
    .sort(([a], [b]) => priority(a) - priority(b) || a.localeCompare(b))
    .map(([serviceName, evs]) => ({ serviceName, entities: evs }))
})
</script>

<style scoped>
.input {
  @apply w-full bg-gray-800 border border-gray-700 text-gray-200 rounded-lg px-3 py-2.5 text-sm
         focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50;
}
.section-label {
  @apply text-[11px] font-semibold uppercase tracking-wider text-gray-500;
}
.btn-primary {
  @apply px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed
         text-white text-sm font-medium rounded-lg transition-colors;
}
.link-btn {
  @apply text-xs text-blue-400 hover:text-blue-300 transition-colors;
}
.preset-btn {
  @apply px-2 py-1 rounded-md text-xs font-medium bg-gray-800 border border-gray-700
         text-gray-400 hover:text-gray-200 hover:border-gray-500 transition-colors;
}
.service-chip {
  @apply px-2.5 py-1 rounded-full text-xs font-medium border transition-colors;
}
.chip-on {
  @apply bg-blue-600/20 border-blue-700 text-blue-300;
}
.chip-off {
  @apply bg-gray-800 border-gray-700 text-gray-400 hover:text-gray-200;
}
.direction-card {
  @apply rounded-lg border px-4 py-3 text-left transition-colors;
}
.direction-active {
  @apply border-blue-600 bg-blue-600/10 text-gray-100;
}
.direction-idle {
  @apply border-gray-700 bg-gray-800/60 text-gray-300 hover:border-gray-500;
}
</style>
