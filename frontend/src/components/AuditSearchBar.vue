<template>
  <section class="card divide-y divide-gray-100 overflow-hidden">
    <!-- Abas de Modo de Busca: Por Pessoa vs Por Fila Específica -->
    <div class="flex items-center gap-2 p-2 bg-gray-50/70 border-b border-gray-100">
      <button
        type="button"
        class="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all cursor-pointer"
        :class="activeMode === 'user' ? 'bg-white text-ink shadow-xs border border-gray-200' : 'text-gray-500 hover:text-ink hover:bg-white/50'"
        :disabled="anyLoading"
        @click="setMode('user')"
      >
        <span>👤</span>
        <span>Por Pessoa (até 10)</span>
      </button>

      <button
        type="button"
        class="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all cursor-pointer"
        :class="activeMode === 'queue' ? 'bg-white text-brand shadow-xs border border-brand/30' : 'text-gray-500 hover:text-ink hover:bg-white/50'"
        :disabled="anyLoading"
        @click="setMode('queue')"
      >
        <span>📋</span>
        <span>Por Fila Específica (até 30 dias)</span>
        <span class="rounded-full bg-brand-soft text-brand px-1.5 py-0.5 text-[10px] font-bold">Novo</span>
      </button>
    </div>

    <!-- ──────────────────────── MODO 1: POR PESSOA ──────────────────────── -->
    <template v-if="activeMode === 'user'">
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
    </template>

    <!-- ──────────────────────── MODO 2: POR FILA ESPECÍFICA ──────────────────────── -->
    <template v-else-if="activeMode === 'queue'">
      <div class="p-5 space-y-4">
        <!-- Fila Alvo -->
        <div class="space-y-2">
          <div class="flex items-center justify-between">
            <p class="section-label">Fila Alvo da Investigação</p>
            <span class="text-[11px] text-gray-400">Nome ou UUID da fila na Genesys Cloud</span>
          </div>

          <!-- Chip da Fila Selecionada -->
          <div v-if="selectedQueue" class="flex items-center gap-3 rounded-2xl border border-brand/30 bg-brand-soft/20 p-3 max-w-2xl">
            <div class="w-8 h-8 rounded-xl bg-brand text-white flex items-center justify-center font-bold text-xs shrink-0">
              📋
            </div>
            <div class="min-w-0 flex-1">
              <p class="text-sm font-bold text-ink truncate">{{ selectedQueue.name }}</p>
              <p class="text-xs font-mono text-gray-500 truncate">{{ selectedQueue.id }}</p>
            </div>
            <button
              type="button"
              class="text-gray-400 hover:text-red-600 px-2 py-1 text-sm font-bold transition-colors"
              title="Trocar fila"
              :disabled="anyLoading"
              @click="clearQueue"
            >
              × Trocar
            </button>
          </div>

          <!-- Input com Autocomplete de Fila -->
          <div v-else class="relative max-w-2xl">
            <input
              v-model="queueQuery"
              type="text"
              placeholder="Digite o nome da fila (ex: TEL_HAB...) ou cole o UUID..."
              class="input"
              :disabled="anyLoading"
              @focus="onQueueInputFocus"
              @keydown.enter="selectQueueByExactQuery"
            />
            <ul
              v-if="queueSuggestions.length"
              class="absolute z-20 mt-1 w-full max-h-60 overflow-y-auto rounded-2xl border border-gray-100 bg-white shadow-card"
            >
              <li
                v-for="q in queueSuggestions"
                :key="q.id"
                class="px-4 py-2.5 text-sm text-ink hover:bg-peach cursor-pointer border-b border-gray-50 last:border-0"
                @click="selectQueue(q)"
              >
                <p class="font-semibold text-ink">{{ q.name }}</p>
                <p class="text-xs font-mono text-gray-400 mt-0.5">{{ q.id }}</p>
              </li>
            </ul>
          </div>
        </div>

        <!-- Filtros Adicionais da Fila: Ação e Operador Específico -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-4xl pt-1">
          <!-- Filtro de Ação -->
          <div class="space-y-1.5">
            <label class="section-label block">Tipo de Alteração na Fila</label>
            <select
              v-model="selectedAction"
              class="input text-xs font-medium"
              :disabled="anyLoading"
            >
              <option value="all">🔍 Todas as alterações de membros</option>
              <option value="MemberRemove">🗑️ Apenas Remoções Definitivas (MemberRemove)</option>
              <option value="MemberUpdate">⚡ Apenas Inativações / Status (MemberUpdate)</option>
              <option value="MemberAdd">➕ Apenas Adições (MemberAdd)</option>
            </select>
            <p class="text-[11px] text-gray-400">
              Permite auditar diretamente quem removeu ou inativou membros desta fila.
            </p>
          </div>

          <!-- Filtro Opcional de Operador Afetado -->
          <div class="space-y-1.5">
            <div class="flex items-center justify-between">
              <label class="section-label block">Operador Específico (Opcional)</label>
              <button
                v-if="selectedTargetUser"
                type="button"
                class="text-[11px] text-gray-400 hover:text-red-500"
                @click="clearTargetUser"
              >
                Limpar
              </button>
            </div>

            <!-- Chip do operador alvo se selecionado -->
            <div
              v-if="selectedTargetUser"
              class="flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-3 py-2 text-xs"
            >
              <span class="text-gray-400">👤</span>
              <span class="font-medium text-ink truncate">{{ selectedTargetUser.name || selectedTargetUser.email || selectedTargetUser.id }}</span>
              <button
                type="button"
                class="ml-auto text-gray-400 hover:text-red-600 text-sm leading-none"
                @click="clearTargetUser"
              >
                ×
              </button>
            </div>

            <!-- Input de busca do operador alvo -->
            <div v-else class="relative">
              <input
                v-model="targetUserQuery"
                type="text"
                placeholder="Filtrar por pessoa nesta fila (opcional)..."
                class="input text-xs"
                :disabled="anyLoading"
                @keydown.enter="selectTargetUserByExact"
              />
              <ul
                v-if="targetUserSuggestions.length"
                class="absolute z-20 mt-1 w-full max-h-48 overflow-y-auto rounded-xl border border-gray-100 bg-white shadow-card text-xs"
              >
                <li
                  v-for="u in targetUserSuggestions"
                  :key="u.id"
                  class="px-3 py-2 text-ink hover:bg-peach cursor-pointer"
                  @click="selectTargetUser(u)"
                >
                  <p class="font-medium">{{ u.name }}</p>
                  <p class="text-[11px] text-gray-400 font-mono">{{ u.email || u.id }}</p>
                </li>
              </ul>
            </div>
            <p class="text-[11px] text-gray-400">
              Deixe vazio para auditar todos os operadores alterados na fila.
            </p>
          </div>
        </div>
      </div>
    </template>

    <!-- ──────────────────────── PERÍODO (COMUM AOS DOIS MODOS) ──────────────────────── -->
    <div class="p-5 space-y-3">
      <div class="flex items-center justify-between flex-wrap gap-2 max-w-xl">
        <p class="section-label">Período</p>
        <div class="flex gap-1.5 flex-wrap">
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

    <!-- ──────────────────────── AÇÕES DE CONSULTA ──────────────────────── -->
    <div class="p-5 space-y-4">
      <div class="flex items-center justify-between">
        <p class="section-label">Execução da Consulta</p>
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

      <!-- Ações do Modo 1: Por Pessoa -->
      <div v-if="activeMode === 'user'" class="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-4xl">
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

      <!-- Ações do Modo 2: Por Fila Específica -->
      <div v-else-if="activeMode === 'queue'" class="max-w-xl">
        <div class="rounded-2xl border border-brand/30 bg-brand-soft/20 p-4 space-y-3">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-brand uppercase tracking-wider">Auditoria da Fila</span>
            <span class="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-brand/15 text-brand">
              Até 30 dias · Direto na Genesys
            </span>
          </div>
          <p class="text-xs text-gray-600 leading-snug">
            Consulta imediata via filtro nativo da Genesys Cloud Platform Audit API. Identifica quem removeu, inativou ou adicionou membros na fila.
          </p>
          <button
            type="button"
            class="w-full btn-primary"
            :disabled="(!selectedQueue && !queueQuery.trim()) || anyLoading"
            @click="emitQueueSearch"
          >
            {{ loadingBase ? 'Consultando fila…' : 'Auditar Fila Específica' }}
          </button>
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
              <strong class="text-ink font-medium">Por Fila Específica:</strong> audita diretamente uma fila com filtro nativo na Genesys, permitindo investigar remoções definitivas e inativações em janelas de até 30 dias com alta velocidade.
            </li>
            <li>
              <strong class="text-ink font-medium">Por Pessoa (Divisão):</strong> pesquisa direta de transferências de divisão da pessoa (rápido).
            </li>
            <li>
              <strong class="text-ink font-medium">Por Pessoa (Filas, Roles e Grupos):</strong> varre eventos da organização buscando até 10 pessoas simultaneamente em janelas de até 48 horas.
            </li>
          </ul>
        </div>
      </details>
    </div>
  </section>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { autocompleteUsers, searchUser } from '../api/genesys'
import { useQueueNames, useUserNames } from '../composables/useEntityNames'
import { datetimeLocalToIso, presetPeriodRange, toDatetimeLocalValue } from '../utils/datetimeLocal'

const props = defineProps({
  /** Loading da consulta (Pesquisar). */
  loading: { type: Boolean, default: false },
  /** Categoria deep em andamento: 'queue' | 'role' | 'group' | null */
  loadingCategory: { type: String, default: null },
})

const emit = defineEmits(['search', 'deep-search', 'queue-search', 'clear', 'cancel'])

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

const PERIOD_PRESETS = [
  { label: '24h', id: '24h' },
  { label: '48h', id: '48h' },
  { label: '7 dias', id: '7d' },
  { label: '15 dias', id: '15d' },
  { label: '30 dias', id: '30d' },
]

const activeMode = ref('user') // 'user' | 'queue'
const localError = ref('')
const activePreset = ref('7d')
const period = reactive({ ...presetPeriodRange('7d') })

const loadingBase = computed(() => !!props.loading)
const anyLoading = computed(() => !!props.loading || !!props.loadingCategory)

// ----------------------------------------------------
// MODO 1: PESSOAS
// ----------------------------------------------------
const query = ref('')
const suggestions = ref([])
const selectedUsers = ref([])
const selected = computed({
  get: () => selectedUsers.value[0] || null,
  set: (u) => {
    selectedUsers.value = u ? [u] : []
  },
})

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

// ----------------------------------------------------
// MODO 2: FILA ESPECÍFICA
// ----------------------------------------------------
const queueCache = useQueueNames()
const userCache = useUserNames()
const selectedQueue = ref(null)
const queueQuery = ref('')
const queueSuggestions = ref([])
const selectedAction = ref('all')
const selectedTargetUser = ref(null)
const targetUserQuery = ref('')
const targetUserSuggestions = ref([])

let queueDebounceTimer = null
watch(queueQuery, (q) => {
  clearTimeout(queueDebounceTimer)
  localError.value = ''
  const trimmed = q.trim()
  if (!trimmed) {
    queueSuggestions.value = []
    return
  }
  queueDebounceTimer = setTimeout(async () => {
    await queueCache.ensureBulk()
    queueSuggestions.value = queueCache.search(trimmed, 12)
  }, 150)
})

async function onQueueInputFocus() {
  await queueCache.ensureBulk()
  if (queueQuery.value.trim()) {
    queueSuggestions.value = queueCache.search(queueQuery.value.trim(), 12)
  }
}

function selectQueue(q) {
  if (!q?.id) return
  selectedQueue.value = { id: q.id, name: q.name || q.id }
  queueQuery.value = ''
  queueSuggestions.value = []
  localError.value = ''
}

function clearQueue() {
  selectedQueue.value = null
  queueQuery.value = ''
  queueSuggestions.value = []
  emit('clear')
}

// Resolve o texto digitado numa fila concreta: UUID colado, nome exato
// (case-insensitive) ou, em último caso, a melhor sugestão do cache.
async function resolveQueueFromQuery() {
  const raw = queueQuery.value.trim().replace(/[{}]/g, '')
  if (!raw) return null
  if (UUID_RE.test(raw)) {
    return { id: raw, name: queueCache.nameOf(raw) || raw }
  }
  await queueCache.ensureBulk()
  const matches = queueCache.search(raw, 12)
  const exact = matches.find((q) => q.name?.toLowerCase() === raw.toLowerCase())
  return exact || matches[0] || null
}

async function selectQueueByExactQuery() {
  const resolved = await resolveQueueFromQuery()
  if (resolved) {
    selectQueue(resolved)
  } else if (queueQuery.value.trim()) {
    localError.value = 'Fila não encontrada. Verifique o nome ou cole o UUID da fila.'
  }
}

// Autocomplete do Operador Alvo Opcional
let targetUserDebounce = null
watch(targetUserQuery, (q) => {
  clearTimeout(targetUserDebounce)
  const trimmed = q.trim()
  if (trimmed.length < 2 || UUID_RE.test(trimmed.replace(/[{}]/g, ''))) {
    targetUserSuggestions.value = []
    return
  }
  targetUserDebounce = setTimeout(async () => {
    try {
      const data = await autocompleteUsers(trimmed)
      targetUserSuggestions.value = data.results || []
    } catch {
      targetUserSuggestions.value = []
    }
  }, 300)
})

function selectTargetUser(u) {
  if (!u?.id) return
  selectedTargetUser.value = u
  targetUserQuery.value = ''
  targetUserSuggestions.value = []
}

function clearTargetUser() {
  selectedTargetUser.value = null
  targetUserQuery.value = ''
  targetUserSuggestions.value = []
}

async function selectTargetUserByExact() {
  const raw = targetUserQuery.value.trim()
  const clean = raw.replace(/[{}]/g, '')
  const isUuid = UUID_RE.test(clean)
  const isEmail = raw.includes('@')
  if (!isUuid && !isEmail) return
  try {
    const data = await searchUser(isUuid ? clean : raw)
    if (data.found) {
      selectTargetUser({ id: data.user.id, name: data.user.name, email: data.user.email })
    }
  } catch {
    // Silencioso se não encontrar
  }
}

// ----------------------------------------------------
// EXECUÇÃO E VALIDAÇÃO DE PERÍODO
// ----------------------------------------------------
function applyPreset(presetId) {
  activePreset.value = presetId
  const range = presetPeriodRange(presetId)
  period.start = range.start
  period.end = range.end
}

function setMode(newMode) {
  if (activeMode.value === newMode) return
  activeMode.value = newMode
  localError.value = ''
  emit('clear')
}

function validatePeriod(maxDays) {
  const startIso = datetimeLocalToIso(period.start)
  const endIso = datetimeLocalToIso(period.end)
  const diffSeconds = (new Date(endIso).getTime() - new Date(startIso).getTime()) / 1000
  if (diffSeconds <= 0) {
    throw new Error('A data final deve ser posterior à data inicial.')
  }
  if (diffSeconds > maxDays * 86400 + 3600) {
    throw new Error(`O intervalo máximo para esta consulta é de ${maxDays} dias.`)
  }
  return { startIso, endIso }
}

function refreshPeriodIfPreset() {
  if (activePreset.value) {
    applyPreset(activePreset.value)
  }
}

function emitSearch() {
  if (!selectedUsers.value.length) return
  localError.value = ''
  refreshPeriodIfPreset()
  try {
    validatePeriod(30)
  } catch (err) {
    localError.value = err.message || 'Data inválida.'
    return
  }
  emit('search', {
    user: selectedUsers.value[0] || null,
    users: [...selectedUsers.value],
    start: period.start,
    end: period.end,
  })
}

function emitDeep(category) {
  if (!selectedUsers.value.length) return
  localError.value = ''
  refreshPeriodIfPreset()
  try {
    const startIso = datetimeLocalToIso(period.start)
    const endIso = datetimeLocalToIso(period.end, true)
    const diffSeconds = (new Date(endIso).getTime() - new Date(startIso).getTime()) / 1000
    if (diffSeconds <= 0) {
      localError.value = 'A data final deve ser posterior à data inicial.'
      return
    }
    if (diffSeconds > 48 * 3600 + 120) {
      localError.value =
        'Para buscas de Filas, Roles e Grupos por Pessoa, o período máximo é de 48 horas (use o preset de 24h ou 48h). Para períodos de até 30 dias em filas, use a aba "Por Fila Específica".'
      return
    }
  } catch (err) {
    localError.value = err.message || 'Data inválida.'
    return
  }
  emit('deep-search', {
    user: selectedUsers.value[0] || null,
    users: [...selectedUsers.value],
    start: period.start,
    end: period.end,
    category,
  })
}

async function emitQueueSearch() {
  localError.value = ''
  if (!selectedQueue.value?.id) {
    const resolved = await resolveQueueFromQuery()
    if (!resolved) {
      localError.value = queueQuery.value.trim()
        ? 'Fila não encontrada. Verifique o nome ou cole o UUID da fila.'
        : 'Selecione a fila alvo da investigação.'
      return
    }
    selectQueue(resolved)
  }

  refreshPeriodIfPreset()
  try {
    validatePeriod(30)
  } catch (err) {
    localError.value = err.message || 'Data inválida.'
    return
  }
  emit('queue-search', {
    queue: selectedQueue.value,
    action: selectedAction.value,
    targetUser: selectedTargetUser.value,
    start: period.start,
    end: period.end,
  })
}

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

async function setQueueMode({ queueId, queueName, targetUserId }) {
  activeMode.value = 'queue'
  await queueCache.ensureBulk()
  selectedQueue.value = {
    id: queueId,
    name: queueName || queueCache.nameOf(queueId) || queueId,
  }
  if (targetUserId) {
    selectedTargetUser.value = {
      id: targetUserId,
      name: userCache.nameOf(targetUserId) || '',
    }
    if (!selectedTargetUser.value.name) {
      searchUser(targetUserId)
        .then((udata) => {
          if (udata?.found && udata.user?.name && selectedTargetUser.value) {
            selectedTargetUser.value.name = udata.user.name
          }
        })
        .catch(() => {})
    }
  } else {
    selectedTargetUser.value = null
  }
  refreshPeriodIfPreset()
  localError.value = ''
  emitQueueSearch()
}

defineExpose({
  updateSelected,
  setQueueMode,
  setMode,
  selected,
  selectedUsers,
  selectedQueue,
  activeMode,
  period,
  emitSearch,
  emitQueueSearch,
})
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
  @apply px-5 py-2.5 bg-brand hover:bg-brand-hover disabled:opacity-40 disabled:cursor-not-allowed
         text-white text-sm font-semibold rounded-full transition-colors cursor-pointer;
}
.btn-secondary {
  @apply px-4 py-1.5 bg-white hover:bg-gray-50 border border-gray-200
         disabled:opacity-40 disabled:cursor-not-allowed
         text-ink text-sm font-semibold rounded-full transition-colors cursor-pointer;
}
.btn-cancel {
  @apply px-5 py-2 bg-white hover:bg-gray-50 border border-gray-200
         text-ink text-sm font-semibold rounded-full transition-colors cursor-pointer;
}
.preset-btn {
  @apply px-2.5 py-1 rounded-full text-xs font-medium bg-white border border-gray-200
         text-gray-500 hover:text-ink hover:border-gray-300 transition-colors cursor-pointer;
}
.preset-active {
  @apply bg-brand-soft border-brand/30 text-brand;
}
</style>
