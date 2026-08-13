<template>
  <section class="card divide-y divide-gray-100">
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
          class="absolute z-20 mt-1 w-full max-h-56 overflow-y-auto rounded-2xl border border-gray-100 bg-white shadow-card"
        >
          <li
            v-for="u in suggestions"
            :key="u.id"
            class="px-3 py-2 text-sm text-ink hover:bg-peach cursor-pointer"
            @click="selectUser(u)"
          >
            <p class="font-medium">{{ u.name }}</p>
            <p v-if="u.email || u.state" class="text-xs text-gray-400">
              {{ u.email }}<span v-if="u.email && u.state"> · </span>{{ u.state }}
            </p>
          </li>
        </ul>
      </div>

      <div
        v-if="selected"
        class="flex items-center gap-3 rounded-xl border border-green-200 bg-green-50 px-3 py-2 max-w-2xl"
      >
        <span
          class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-green-600
                 text-xs font-bold text-white"
        >
          {{ initialsOf(selected.name) }}
        </span>
        <div class="min-w-0 flex-1">
          <p class="text-sm font-medium text-green-800 truncate">{{ selected.name }}</p>
          <p class="text-xs text-gray-500 font-mono truncate">
            {{ selected.email || selected.id }}
          </p>
        </div>
        <button
          type="button"
          class="text-gray-400 hover:text-ink text-lg leading-none px-1"
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
          <span class="text-xs text-gray-400">De</span>
          <input
            v-model="period.start"
            type="datetime-local"
            class="input mt-1.5"
            :disabled="anyLoading"
            @input="activePreset = null"
          />
        </label>
        <label class="block">
          <span class="text-xs text-gray-400">Até</span>
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
        class="max-w-2xl rounded-xl border border-gray-100 bg-gray-50 px-3 py-2.5
               text-xs leading-relaxed text-gray-600 space-y-2"
        role="note"
      >
        <ul class="list-disc list-outside pl-4 space-y-1.5">
          <li>
            <span class="font-medium text-ink">Pesquisar (divisão):</span>
            mudanças de divisão do usuário (de qual divisão para qual), quem alterou e quando.
            Filtro direto na Genesys — rápido.
          </li>
          <li>
            <span class="font-medium text-ink">Buscar filas:</span>
            quando o usuário foi adicionado/removido/ativado/desativado em filas;
            quem fez e quando; qual fila.
          </li>
          <li>
            <span class="font-medium text-ink">Buscar roles:</span>
            quando o usuário ganhou/perdeu roles; quem atribuiu/removeu e quando; qual role.
          </li>
          <li>
            <span class="font-medium text-ink">Buscar grupos:</span>
            quando o usuário foi adicionado/removido de grupos; quem fez e quando; qual grupo.
          </li>
        </ul>
        <p class="text-gray-600 border-t border-gray-200 pt-2">
          Filas, roles e grupos são
          <span class="font-medium text-ink">buscas profundas</span>
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
        <p v-if="localError" class="text-sm text-red-600 font-medium">{{ localError }}</p>
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
  @apply w-full bg-white border border-gray-200 text-ink rounded-xl px-3 py-2.5 text-sm
         focus:outline-none focus:ring-2 focus:ring-brand/25 focus:border-brand disabled:opacity-50;
}
.section-label {
  @apply text-[11px] font-semibold uppercase tracking-wider text-gray-400;
}
.btn-primary {
  @apply px-5 py-2 bg-brand hover:bg-brand-hover disabled:opacity-40 disabled:cursor-not-allowed
         text-white text-sm font-semibold rounded-full transition-colors;
}
.btn-secondary {
  @apply px-4 py-1.5 bg-white hover:bg-gray-50 border border-gray-200
         disabled:opacity-40 disabled:cursor-not-allowed
         text-ink text-sm font-semibold rounded-full transition-colors;
}
.btn-cancel {
  @apply px-5 py-2 bg-white hover:bg-gray-50 border border-gray-200
         text-ink text-sm font-semibold rounded-full transition-colors;
}
.preset-btn {
  @apply px-2.5 py-1 rounded-full text-xs font-medium bg-white border border-gray-200
         text-gray-500 hover:text-ink hover:border-gray-300 transition-colors;
}
.preset-active {
  @apply bg-brand-soft border-brand/30 text-brand;
}
</style>
