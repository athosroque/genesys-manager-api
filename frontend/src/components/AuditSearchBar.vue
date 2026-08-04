<template>
  <section class="rounded-xl border border-gray-700 bg-gray-900/80 divide-y divide-gray-800">
    <!-- Pessoa -->
    <div class="p-5 space-y-3">
      <p class="section-label">Pessoa</p>
      <div class="relative max-w-2xl">
        <input
          v-model="query"
          type="text"
          placeholder="Nome, e-mail ou UUID — digite 2+ letras"
          class="input"
          :disabled="anyLoading"
          @keydown.enter="selectByExactQuery"
        />
        <ul
          v-if="suggestions.length"
          class="absolute z-20 mt-1 w-full max-h-56 overflow-y-auto rounded-lg border border-gray-700 bg-gray-900 shadow-xl"
        >
          <li
            v-for="u in suggestions"
            :key="u.id"
            class="px-3 py-2 text-sm text-gray-200 hover:bg-gray-800 cursor-pointer"
            @click="selectUser(u)"
          >
            <p class="font-medium">{{ u.name }}</p>
            <p v-if="u.email || u.state" class="text-xs text-gray-500">
              {{ u.email }}<span v-if="u.email && u.state"> · </span>{{ u.state }}
            </p>
          </li>
        </ul>
      </div>

      <div
        v-if="selected"
        class="flex items-center gap-3 rounded-lg border border-green-800/40 bg-green-900/10 px-3 py-2 max-w-2xl"
      >
        <span
          class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-green-700
                 text-xs font-bold text-white"
        >
          {{ initialsOf(selected.name) }}
        </span>
        <div class="min-w-0 flex-1">
          <p class="text-sm font-medium text-green-300 truncate">{{ selected.name }}</p>
          <p class="text-xs text-gray-500 font-mono truncate">
            {{ selected.email || selected.id }}
          </p>
        </div>
        <button
          type="button"
          class="text-gray-500 hover:text-gray-200 text-lg leading-none px-1"
          title="Remover seleção"
          :disabled="anyLoading"
          @click="clearSelected"
        >
          ×
        </button>
      </div>
    </div>

    <!-- Período -->
    <div class="p-5 space-y-3">
      <div class="flex items-center justify-between flex-wrap gap-2 max-w-xl">
        <p class="section-label">Período</p>
        <div class="flex gap-1.5">
          <button
            v-for="p in PERIOD_PRESETS"
            :key="p.id"
            type="button"
            class="preset-btn"
            :class="activePreset === p.id ? 'preset-active' : ''"
            :disabled="anyLoading"
            @click="applyPreset(p.id)"
          >
            {{ p.label }}
          </button>
        </div>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-xl">
        <label class="block">
          <span class="text-xs text-gray-500">De</span>
          <input
            v-model="period.start"
            type="datetime-local"
            class="input mt-1.5"
            :disabled="anyLoading"
            @input="activePreset = null"
          />
        </label>
        <label class="block">
          <span class="text-xs text-gray-500">Até</span>
          <input
            v-model="period.end"
            type="datetime-local"
            class="input mt-1.5"
            :disabled="anyLoading"
            @input="activePreset = null"
          />
        </label>
      </div>
    </div>

    <!-- Como funciona -->
    <div class="p-5 space-y-3">
      <p class="section-label">Como funciona</p>
      <div
        class="max-w-2xl rounded-lg border border-gray-700 bg-gray-800/50 px-3 py-2.5
               text-xs leading-relaxed text-gray-300 space-y-2"
        role="note"
      >
        <ul class="list-disc list-outside pl-4 space-y-1.5">
          <li>
            <span class="font-medium text-gray-200">Pesquisar (divisão):</span>
            mudanças de divisão do usuário (de qual divisão para qual), quem alterou e quando.
            Filtro direto na Genesys — rápido.
          </li>
          <li>
            <span class="font-medium text-gray-200">Buscar filas:</span>
            quando o usuário foi adicionado/removido/ativado/desativado em filas;
            quem fez e quando; qual fila.
          </li>
          <li>
            <span class="font-medium text-gray-200">Buscar roles:</span>
            quando o usuário ganhou/perdeu roles; quem atribuiu/removeu e quando; qual role.
          </li>
          <li>
            <span class="font-medium text-gray-200">Buscar grupos:</span>
            quando o usuário foi adicionado/removido de grupos; quem fez e quando; qual grupo.
          </li>
        </ul>
        <p class="text-gray-300 border-t border-gray-700/80 pt-2">
          Filas, roles e grupos são
          <span class="font-medium text-gray-200">buscas profundas</span>
          (opcionais e independentes): varrem o histórico da organização e só depois
          filtram a pessoa — mais lentas e, com muito volume, podem truncar parte do histórico.
          A Genesys não filtra esses serviços direto pela pessoa.
        </p>
      </div>
    </div>

    <div class="p-5 space-y-3">
      <div class="flex flex-wrap items-center gap-3">
        <button
          class="btn-primary"
          :disabled="!selected || anyLoading"
          @click="emitSearch"
        >
          {{ loadingBase ? 'Consultando divisão…' : 'Pesquisar' }}
        </button>
        <button
          v-if="anyLoading"
          type="button"
          class="btn-cancel"
          data-testid="cancel-search"
          @click="emit('cancel')"
        >
          Cancelar
        </button>
        <p v-if="localError" class="text-sm text-red-400 font-medium">{{ localError }}</p>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <button
          type="button"
          class="btn-secondary"
          :disabled="!selected || anyLoading"
          @click="emitDeep('queue')"
        >
          {{ loadingCategory === 'queue' ? 'Buscando filas…' : 'Buscar filas' }}
        </button>
        <button
          type="button"
          class="btn-secondary"
          :disabled="!selected || anyLoading"
          @click="emitDeep('role')"
        >
          {{ loadingCategory === 'role' ? 'Buscando roles…' : 'Buscar roles' }}
        </button>
        <button
          type="button"
          class="btn-secondary"
          :disabled="!selected || anyLoading"
          @click="emitDeep('group')"
        >
          {{ loadingCategory === 'group' ? 'Buscando grupos…' : 'Buscar grupos' }}
        </button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { autocompleteUsers, searchUser } from '../api/genesys'
import { presetPeriodRange } from '../utils/datetimeLocal'

const props = defineProps({
  /** Loading da consulta de divisão (Pesquisar). */
  loading: { type: Boolean, default: false },
  /** Categoria deep em andamento: 'queue' | 'role' | 'group' | null */
  loadingCategory: { type: String, default: null },
  /** Prefill vindo da rota (?userId=&name=) */
  initialUser: { type: Object, default: null },
})

const emit = defineEmits(['search', 'deep-search', 'clear', 'cancel'])

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

const PERIOD_PRESETS = [
  { label: '24h', id: '24h' },
  { label: '7 dias', id: '7d' },
  { label: '30 dias', id: '30d' },
]

const query = ref('')
const suggestions = ref([])
const selected = ref(null)
const localError = ref('')
const activePreset = ref('7d')
const period = reactive({ ...presetPeriodRange('7d') })

const loadingBase = computed(() => !!props.loading)
const anyLoading = computed(() => !!props.loading || !!props.loadingCategory)

let suppressQueryWatch = false
let debounceTimer = null

watch(
  () => props.initialUser,
  (u) => {
    if (u?.id && u.id !== selected.value?.id) {
      selected.value = { id: u.id, name: u.name || u.id, email: u.email || '' }
      if (query.value !== '') {
        suppressQueryWatch = true
        query.value = ''
      }
      suggestions.value = []
    }
  },
  { immediate: true },
)

watch(query, (q) => {
  if (suppressQueryWatch) {
    suppressQueryWatch = false
    return
  }
  clearTimeout(debounceTimer)
  selected.value = null
  localError.value = ''
  const trimmed = q.trim()
  if (trimmed.length < 2 || UUID_RE.test(trimmed.replace(/[{}]/g, ''))) {
    suggestions.value = []
    return
  }
  debounceTimer = setTimeout(async () => {
    try {
      const data = await autocompleteUsers(trimmed)
      suggestions.value = data.results || []
    } catch {
      suggestions.value = []
    }
  }, 300)
})

function applyPreset(presetId) {
  activePreset.value = presetId
  const range = presetPeriodRange(presetId)
  period.start = range.start
  period.end = range.end
}

function selectUser(user) {
  selected.value = user
  localError.value = ''
  if (query.value !== '') {
    suppressQueryWatch = true
    query.value = ''
  }
  suggestions.value = []
}

function clearSelected() {
  selected.value = null
  query.value = ''
  suggestions.value = []
  localError.value = ''
  emit('clear')
}

const initialsOf = (name) =>
  name ? name.split(' ').map((p) => p[0]).slice(0, 2).join('').toUpperCase() : '?'

async function selectByExactQuery() {
  const raw = query.value.trim()
  const clean = raw.replace(/[{}]/g, '')
  const isUuid = UUID_RE.test(clean)
  const isEmail = raw.includes('@')
  if (!isUuid && !isEmail) return
  try {
    const data = await searchUser(isUuid ? clean : raw)
    if (data.found) {
      selectUser({ id: data.user.id, name: data.user.name, email: data.user.email })
    } else {
      localError.value = isUuid ? 'UUID não encontrado.' : 'E-mail não encontrado.'
    }
  } catch (err) {
    localError.value = err.message
  }
}

function payloadBase() {
  return {
    user: selected.value,
    start: period.start,
    end: period.end,
  }
}

function emitSearch() {
  if (!selected.value) return
  emit('search', payloadBase())
}

function emitDeep(category) {
  if (!selected.value) return
  emit('deep-search', { ...payloadBase(), category })
}

/** Chamado pelo pai após atualizar nome/email via resposta da API */
function updateSelected(user) {
  if (!user) return
  selected.value = {
    id: user.id || selected.value?.id,
    name: user.name || selected.value?.name,
    email: user.email || selected.value?.email || '',
  }
}

defineExpose({ updateSelected, selected, period, emitSearch })
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
.btn-secondary {
  @apply px-3 py-1.5 bg-gray-800 hover:bg-gray-700 border border-gray-600
         disabled:opacity-40 disabled:cursor-not-allowed
         text-gray-200 text-sm font-medium rounded-lg transition-colors;
}
.btn-cancel {
  @apply px-4 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-500
         text-gray-200 text-sm font-medium rounded-lg transition-colors;
}
.preset-btn {
  @apply px-2 py-1 rounded-md text-xs font-medium bg-gray-800 border border-gray-700
         text-gray-400 hover:text-gray-200 hover:border-gray-500 transition-colors;
}
.preset-active {
  @apply bg-blue-600/20 border-blue-700 text-blue-300;
}
</style>
