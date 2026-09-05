<template>
  <section class="card divide-y divide-gray-100">
    <!-- Pessoas -->
    <div class="p-5 space-y-3">
      <div class="flex items-center justify-between">
        <p class="section-label">Pessoas (até 10)</p>
        <button
          v-if="selectedUsers.length > 1"
          type="button"
          class="text-xs text-gray-400 hover:text-red-500 transition-colors"
          :disabled="anyLoading"
          @click="clearAllUsers"
        >
          Limpar todos
        </button>
      </div>

      <!-- Chips de Usuários Selecionados -->
      <div v-if="selectedUsers.length" class="space-y-2 max-w-3xl">
        <div class="flex flex-wrap gap-2">
          <div
            v-for="(u, idx) in selectedUsers"
            :key="u.id || idx"
            class="flex items-center gap-2.5 rounded-xl border border-gray-200 bg-white px-3 py-1.5 transition-all text-xs shadow-xs"
          >
            <span
              class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[10px] font-bold text-white bg-brand"
            >
              {{ initialsOf(u.name) }}
            </span>
            <div class="min-w-0">
              <div class="flex items-center gap-1.5">
                <p class="font-medium text-ink truncate max-w-[150px] sm:max-w-[200px]">{{ u.name }}</p>
                <span
                  v-if="selectedUsers.length > 1 && idx === 0"
                  class="rounded bg-gray-100 px-1.5 py-0.5 text-[9px] font-semibold text-gray-600 tracking-wider"
                  title="Será consultado na busca de divisão"
                >
                  1º (Divisão)
                </span>
              </div>
              <p class="text-[11px] text-gray-500 font-mono truncate max-w-[150px] sm:max-w-[200px]">
                {{ u.email || u.id }}
              </p>
            </div>
            <button
              type="button"
              class="text-gray-400 hover:text-red-600 text-base leading-none ml-1 px-1"
              title="Remover pessoa"
              :disabled="anyLoading"
              @click="removeUser(idx)"
            >
              ×
            </button>
          </div>
        </div>

        <p v-if="selectedUsers.length > 1" class="text-[11px] text-gray-500">
          💡 <strong>Filas, Roles e Grupos:</strong> consultam as {{ selectedUsers.length }} pessoas simultaneamente. · <strong>Divisão:</strong> consulta a 1ª pessoa ({{ selectedUsers[0]?.name }}).
        </p>
      </div>

      <!-- Campo de Busca / Adição -->
      <div v-if="selectedUsers.length < 10" class="relative max-w-2xl">
        <input
          v-model="query"
          type="text"
          :placeholder="selectedUsers.length ? 'Adicionar outra pessoa (digite 2+ letras)...' : 'Nome, e-mail ou UUID — digite 2+ letras'"
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

    <!-- Ações de Consulta (Executar Consulta) -->
    <div class="p-5 space-y-4">
      <div class="flex items-center justify-between">
        <p class="section-label">Opções de Busca</p>
        <button
          v-if="anyLoading"
          type="button"
          class="btn-cancel"
          data-testid="cancel-search"
          @click="emit('cancel')"
        >
          Cancelar consulta
        </button>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-4xl">
        <!-- Card 1: Divisão (Individual) -->
        <div class="rounded-2xl border border-gray-200 bg-gray-50/60 p-4 flex flex-col justify-between space-y-3">
          <div class="space-y-1">
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold text-ink uppercase tracking-wider">Divisão</span>
              <span class="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-gray-200 text-gray-700">
                1 pessoa · Rápido
              </span>
            </div>
            <p class="text-xs text-gray-500 leading-snug">
              Consulta mudanças de divisão direto na Genesys.
              <span v-if="selectedUsers.length > 1" class="text-ink font-medium block mt-0.5">
                Pesquisará: {{ selectedUsers[0]?.name }}
              </span>
            </p>
          </div>
          <button
            type="button"
            class="w-full btn-primary"
            :disabled="!selectedUsers.length || anyLoading"
            @click="emitSearch"
          >
            {{ loadingBase ? 'Consultando divisão…' : 'Buscar Divisão' }}
          </button>
        </div>

        <!-- Card 2: Buscas em Lote (Multi-usuário) -->
        <div class="rounded-2xl border border-brand/25 bg-brand-soft/20 p-4 flex flex-col justify-between space-y-3">
          <div class="space-y-1">
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold text-brand uppercase tracking-wider">Filas · Roles · Grupos</span>
              <span class="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-brand/15 text-brand">
                {{ selectedUsers.length || 0 }} {{ selectedUsers.length === 1 ? 'pessoa' : 'pessoas' }} · Máx. 48h
              </span>
            </div>
            <p class="text-xs text-gray-600 leading-snug">
              Varre o histórico da organização buscando todas as pessoas selecionadas ao mesmo tempo (máx. 48h).
            </p>
          </div>
          <div class="grid grid-cols-3 gap-2">
            <button
              type="button"
              class="btn-secondary text-xs px-2 py-2 text-center truncate"
              :disabled="!selectedUsers.length || anyLoading"
              :title="'Buscar filas para ' + (selectedUsers.length || 0) + ' pessoas'"
              @click="emitDeep('queue')"
            >
              {{ loadingCategory === 'queue' ? 'Buscando…' : (selectedUsers.length > 1 ? `Filas (${selectedUsers.length})` : 'Buscar Filas') }}
            </button>
            <button
              type="button"
              class="btn-secondary text-xs px-2 py-2 text-center truncate"
              :disabled="!selectedUsers.length || anyLoading"
              :title="'Buscar roles para ' + (selectedUsers.length || 0) + ' pessoas'"
              @click="emitDeep('role')"
            >
              {{ loadingCategory === 'role' ? 'Buscando…' : (selectedUsers.length > 1 ? `Roles (${selectedUsers.length})` : 'Buscar Roles') }}
            </button>
            <button
              type="button"
              class="btn-secondary text-xs px-2 py-2 text-center truncate"
              :disabled="!selectedUsers.length || anyLoading"
              :title="'Buscar grupos para ' + (selectedUsers.length || 0) + ' pessoas'"
              @click="emitDeep('group')"
            >
              {{ loadingCategory === 'group' ? 'Buscando…' : (selectedUsers.length > 1 ? `Grupos (${selectedUsers.length})` : 'Buscar Grupos') }}
            </button>
          </div>
        </div>
      </div>

      <p v-if="localError" class="text-sm text-red-600 font-medium">{{ localError }}</p>
    </div>

    <!-- Como funciona (expansível / rodapé informativo) -->
    <div class="p-4 bg-gray-50/50 rounded-b-2xl">
      <details class="group text-xs text-gray-600 cursor-pointer">
        <summary class="font-medium text-ink flex items-center justify-between select-none hover:text-brand transition-colors">
          <span>Como funciona a consulta de auditoria?</span>
          <span class="text-gray-400 group-open:rotate-180 transition-transform">▼</span>
        </summary>
        <div class="mt-3 space-y-2 leading-relaxed text-gray-500">
          <ul class="list-disc list-outside pl-4 space-y-1">
            <li>
              <strong class="text-ink font-medium">Buscar Divisão:</strong> pesquisa direta de transferências de divisão (de qual para qual, quem alterou e quando). Filtro nativo da Genesys para 1 pessoa (rápido).
            </li>
            <li>
              <strong class="text-ink font-medium">Buscar Filas:</strong> varre eventos de filas da organização e identifica quando qualquer uma das pessoas selecionadas entrou, saiu ou foi ativada/desativada em filas.
            </li>
            <li>
              <strong class="text-ink font-medium">Buscar Roles:</strong> varre eventos de permissões e identifica quando qualquer uma das pessoas selecionadas ganhou ou perdeu roles de acesso.
            </li>
            <li>
              <strong class="text-ink font-medium">Buscar Grupos:</strong> varre eventos de grupos e identifica adições ou remoções de membros das pessoas selecionadas.
            </li>
          </ul>
          <p class="pt-1 text-[11px] text-gray-400">
            As buscas de Filas, Roles e Grupos executam via streaming em tempo real com barra de progresso, varrendo a organização e filtrando em memória sem onerar a API.
          </p>
        </div>
      </details>
    </div>
  </section>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { autocompleteUsers, searchUser } from '../api/genesys'
import { datetimeLocalToIso, presetPeriodRange } from '../utils/datetimeLocal'

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
  { label: '48h', id: '48h' },
  { label: '7 dias', id: '7d' },
  { label: '30 dias', id: '30d' },
]

const query = ref('')
const suggestions = ref([])
const selectedUsers = ref([])
const selected = computed({
  get: () => selectedUsers.value[0] || null,
  set: (u) => {
    selectedUsers.value = u ? [u] : []
  },
})
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
  if (!user?.id && !user?.email) return
  const alreadyIn = selectedUsers.value.some(
    (u) => (user.id && u.id === user.id) || (user.email && u.email?.toLowerCase() === user.email.toLowerCase()),
  )
  if (alreadyIn) {
    localError.value = 'Esta pessoa já foi adicionada.'
    suggestions.value = []
    return
  }
  if (selectedUsers.value.length >= 10) {
    localError.value = 'Limite de 10 pessoas por busca atingido.'
    suggestions.value = []
    return
  }

  selectedUsers.value.push(user)
  localError.value = ''
  if (query.value !== '') {
    suppressQueryWatch = true
    query.value = ''
  }
  suggestions.value = []
}

function removeUser(index) {
  selectedUsers.value.splice(index, 1)
  localError.value = ''
  if (!selectedUsers.value.length) {
    emit('clear')
  }
}

function clearAllUsers() {
  selectedUsers.value = []
  query.value = ''
  suggestions.value = []
  localError.value = ''
  emit('clear')
}

function clearSelected() {
  clearAllUsers()
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
    user: selectedUsers.value[0] || null,
    users: [...selectedUsers.value],
    start: period.start,
    end: period.end,
  }
}

function emitSearch() {
  if (!selectedUsers.value.length) return
  localError.value = ''
  try {
    const startIso = datetimeLocalToIso(period.start)
    const endIso = datetimeLocalToIso(period.end)
    const diffSeconds = (new Date(endIso).getTime() - new Date(startIso).getTime()) / 1000
    if (diffSeconds <= 0) {
      localError.value = 'A data final deve ser posterior à data inicial.'
      return
    }
    if (diffSeconds > 30 * 86400 + 3600) {
      localError.value = 'O intervalo máximo para consulta de divisão é de 30 dias.'
      return
    }
  } catch (err) {
    localError.value = err.message || 'Data inválida.'
    return
  }
  emit('search', payloadBase())
}

function emitDeep(category) {
  if (!selectedUsers.value.length) return
  localError.value = ''
  try {
    const startIso = datetimeLocalToIso(period.start)
    const endIso = datetimeLocalToIso(period.end)
    const diffSeconds = (new Date(endIso).getTime() - new Date(startIso).getTime()) / 1000
    if (diffSeconds <= 0) {
      localError.value = 'A data final deve ser posterior à data inicial.'
      return
    }
    if (diffSeconds > 48 * 3600 + 120) {
      localError.value =
        'Para buscas de Filas, Roles e Grupos, o período máximo é de 48 horas (use o preset de 24h ou 48h) para garantir rapidez.'
      return
    }
  } catch (err) {
    localError.value = err.message || 'Data inválida.'
    return
  }
  emit('deep-search', { ...payloadBase(), category })
}

/** Chamado pelo pai após atualizar nome/email via resposta da API */
function updateSelected(user) {
  if (!user) return
  if (selectedUsers.value.length > 0) {
    selectedUsers.value[0] = {
      id: user.id || selectedUsers.value[0]?.id,
      name: user.name || selectedUsers.value[0]?.name,
      email: user.email || selectedUsers.value[0]?.email || '',
    }
  } else {
    selectedUsers.value = [{
      id: user.id,
      name: user.name,
      email: user.email || '',
    }]
  }
}

defineExpose({ updateSelected, selected, selectedUsers, period, emitSearch })
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
