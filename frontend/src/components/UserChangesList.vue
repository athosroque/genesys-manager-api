<template>
  <div class="space-y-4">
    <!-- Filtro por Pessoa (se múltiplos usuários) -->
    <div v-if="userChips.length > 1" class="flex flex-wrap items-center gap-2 pb-1 border-b border-gray-100">
      <span class="text-xs text-gray-400 font-medium mr-1">Pessoa:</span>
      <button
        v-for="chip in userChips"
        :key="chip.id"
        type="button"
        class="category-chip"
        :class="userFilter === chip.id ? 'chip-on' : 'chip-off'"
        @click="userFilter = chip.id"
      >
        {{ chip.label }}
        <span v-if="chip.count != null" class="opacity-60">{{ chip.count }}</span>
      </button>
    </div>

    <!-- Chips de categoria -->
    <div class="flex flex-wrap items-center gap-2">
      <button
        v-for="chip in categoryChips"
        :key="chip.id"
        type="button"
        class="category-chip"
        :class="categoryFilter === chip.id ? 'chip-on' : 'chip-off'"
        @click="categoryFilter = chip.id"
      >
        {{ chip.label }}
        <span v-if="chip.count != null" class="opacity-60">{{ chip.count }}</span>
      </button>
      <span
        v-if="changes.length"
        class="ml-auto text-xs font-medium text-gray-500 bg-white border border-gray-200 rounded-full px-3 py-1"
      >
        {{ filtered.length }} de {{ changes.length }} alteração{{ changes.length === 1 ? '' : 'ões' }}
      </span>
    </div>

    <div
      v-if="truncated || truncatedCategoryLabels.length"
      class="space-y-1 text-xs text-amber-700"
      data-testid="truncated-warning"
    >
      <p v-if="truncatedCategoryLabels.length">
        Varredura parcial em
        <span class="font-medium text-amber-800">{{ truncatedCategoryLabels.join(', ') }}</span>:
        a leitura parou ao atingir o teto (~2.500 eventos da organização por pedaço de tempo).
      </p>
      <p v-else>
        Varredura parcial: em pelo menos um serviço e pedaço de tempo, a leitura
        parou ao atingir o teto (~2.500 eventos da organização).
      </p>
      <p>
        Os cards já encontrados continuam listados; mudanças do usuário além do
        que foi lido podem faltar.
      </p>
    </div>

    <!-- Lista vertical -->
    <div v-if="filtered.length" class="space-y-3">
      <article
        v-for="card in filtered"
        :key="card.id"
        class="card px-4 py-3.5 space-y-3"
      >
        <!-- Membership binária (role/fila/grupo add|remove|activate|deactivate): só a frase -->
        <template v-if="isNarrativeCard(card)">
          <div class="flex items-start gap-2.5">
            <span
              class="shrink-0 rounded-md px-2 py-0.5 text-[11px] font-medium border mt-0.5"
              :class="categoryBadgeClass(card.category)"
            >
              {{ categoryLabel(card.category) }}
            </span>
            <span
              v-if="card.target_user?.name || card.target_user?.email"
              class="shrink-0 rounded-md px-2 py-0.5 text-[11px] font-medium bg-gray-100 text-gray-700 border border-gray-200 mt-0.5"
            >
              👤 {{ card.target_user.name || card.target_user.email }}
            </span>
            <p class="text-sm text-ink leading-snug break-words">
              {{ narrativeSentence(card) }}
            </p>
          </div>
        </template>

        <!-- Divisão (e updates com Antes→Depois): layout de diff -->
        <template v-else>
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0 flex items-center gap-2.5">
              <span
                class="shrink-0 rounded-md px-2 py-0.5 text-[11px] font-medium border"
                :class="categoryBadgeClass(card.category)"
              >
                {{ categoryLabel(card.category) }}
              </span>
              <span
                v-if="card.target_user?.name || card.target_user?.email"
                class="shrink-0 rounded-md px-2 py-0.5 text-[11px] font-medium bg-gray-100 text-gray-700 border border-gray-200"
              >
                👤 {{ card.target_user.name || card.target_user.email }}
              </span>
              <div class="min-w-0">
                <p class="text-sm font-semibold text-ink truncate">
                  {{ card.resource?.name || card.resource?.id || 'Recurso' }}
                </p>
                <p v-if="card.action" class="text-xs text-gray-400 mt-0.5">
                  {{ actionLabel(card.action) }}
                </p>
              </div>
            </div>
          </div>

          <div class="flex flex-wrap items-stretch gap-2 text-xs sm:gap-3">
            <div class="min-w-[8rem] flex-1 rounded-xl bg-gray-50 border border-gray-100 px-3 py-2">
              <p class="text-[10px] uppercase tracking-wider text-gray-400 mb-1">Antes</p>
              <p class="text-ink break-words">{{ displayValue(card.before) }}</p>
            </div>
            <div class="hidden sm:flex items-center text-gray-300 shrink-0" aria-hidden="true">→</div>
            <div class="min-w-[8rem] flex-1 rounded-xl bg-gray-50 border border-gray-100 px-3 py-2">
              <p class="text-[10px] uppercase tracking-wider text-gray-400 mb-1">Depois</p>
              <p class="text-ink break-words">{{ displayValue(card.after) }}</p>
            </div>
          </div>

          <div class="flex flex-wrap items-center justify-between gap-2 text-xs text-gray-500">
            <p>
              <span class="text-gray-400">Alterado por</span>
              {{ changedByLabel(card.changed_by) }}
            </p>
            <p class="font-mono text-gray-400">{{ formatEventDate(card.event_date) }}</p>
          </div>
        </template>
      </article>
    </div>

    <div
      v-else
      class="rounded-2xl border border-dashed border-gray-200 bg-white p-6 text-center text-sm text-gray-400"
    >
      Nenhuma alteração encontrada para os filtros selecionados.
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  changes: { type: Array, default: () => [] },
  truncated: { type: Boolean, default: false },
  /** Truncamento por categoria: { queue: true, role: false, ... } */
  truncatedByCategory: { type: Object, default: () => ({}) },
  /**
   * Categorias deep já buscadas nesta sessão (ex.: ['queue','group']).
   * Controla quais chips de fila/role/grupo ficam visíveis além da divisão.
   */
  fetchedDeepCategories: { type: Array, default: () => [] },
  /** Lista de usuários consultados no lote: [{ id, name, email }] */
  queriedUsers: { type: Array, default: () => [] },
})

const CATEGORY_ORDER = ['group', 'role', 'division', 'queue']
const DEEP_ONLY_CATEGORIES = new Set(['group', 'role', 'queue'])
const CATEGORY_LABELS = {
  group: 'Grupo',
  role: 'Role',
  division: 'Divisão',
  queue: 'Fila',
}
const ACTION_LABELS = {
  add: 'Adicionado',
  remove: 'Removido',
  update: 'Atualizado',
  activate: 'Ativado',
  deactivate: 'Desativado',
}

// Membership muda são binárias — Antes/Depois vazios (ou sentinelas) não ajudam.
const NARRATIVE_CATEGORIES = new Set(['queue', 'role', 'group'])
const NARRATIVE_ACTIONS = new Set(['add', 'remove', 'activate', 'deactivate'])

/** Prefixo da frase por categoria + ação (ex.: "Removido da role"). */
const NARRATIVE_PREFIX = {
  role: {
    add: 'Adicionado à role',
    remove: 'Removido da role',
  },
  queue: {
    add: 'Adicionado à fila',
    remove: 'Removido da fila',
    activate: 'Ativado na fila',
    deactivate: 'Desativado na fila',
  },
  group: {
    add: 'Adicionado ao grupo',
    remove: 'Removido do grupo',
  },
}

const categoryFilter = ref('all')
const userFilter = ref('all')

watch(
  () => props.changes,
  () => {
    categoryFilter.value = 'all'
    userFilter.value = 'all'
  },
)

const userChips = computed(() => {
  const usersMap = new Map()
  for (const u of props.queriedUsers || []) {
    if (u?.id) {
      usersMap.set(u.id, { id: u.id, label: u.name || u.email || u.id, count: 0 })
    }
  }
  for (const c of props.changes) {
    const tu = c?.target_user
    if (tu?.id) {
      if (!usersMap.has(tu.id)) {
        usersMap.set(tu.id, { id: tu.id, label: tu.name || tu.email || tu.id, count: 0 })
      }
      usersMap.get(tu.id).count++
    }
  }

  const list = [...usersMap.values()]
  if (list.length <= 1) return []

  return [
    { id: 'all', label: 'Todas as pessoas', count: props.changes.length },
    ...list,
  ]
})

const countsByCategory = computed(() => {
  const counts = { group: 0, role: 0, division: 0, queue: 0 }
  for (const c of props.changes) {
    if (counts[c.category] != null) counts[c.category]++
  }
  return counts
})

const fetchedDeepSet = computed(() => new Set(props.fetchedDeepCategories || []))

const truncatedCategoryLabels = computed(() => {
  const labels = []
  for (const id of CATEGORY_ORDER) {
    if (props.truncatedByCategory?.[id]) {
      labels.push(CATEGORY_LABELS[id] || id)
    }
  }
  return labels
})

const visibleCategories = computed(() =>
  CATEGORY_ORDER.filter((id) => {
    if (!DEEP_ONLY_CATEGORIES.has(id)) return true
    // Mostra chip se já buscou essa categoria OU se já há resultados dela
    return fetchedDeepSet.value.has(id) || (countsByCategory.value[id] || 0) > 0
  }),
)

const categoryChips = computed(() => [
  { id: 'all', label: 'Todas', count: props.changes.length },
  ...visibleCategories.value.map((id) => ({
    id,
    label: CATEGORY_LABELS[id],
    count: countsByCategory.value[id],
  })),
])

watch(
  () => props.fetchedDeepCategories,
  (cats) => {
    const set = new Set(cats || [])
    if (
      DEEP_ONLY_CATEGORIES.has(categoryFilter.value)
      && !set.has(categoryFilter.value)
      && !(countsByCategory.value[categoryFilter.value] > 0)
    ) {
      categoryFilter.value = 'all'
    }
  },
)

const filtered = computed(() => {
  let list = props.changes
  if (categoryFilter.value !== 'all') {
    list = list.filter((c) => c.category === categoryFilter.value)
  }
  if (userFilter.value !== 'all') {
    list = list.filter((c) => c?.target_user?.id === userFilter.value)
  }
  return [...list].sort((a, b) => (b.event_date || '').localeCompare(a.event_date || ''))
})

const categoryLabel = (c) => CATEGORY_LABELS[c] || c || 'Outro'
const actionLabel = (a) => ACTION_LABELS[a] || a || '—'
const displayValue = (v) => (v == null || v === '' ? '—' : String(v))

function isNarrativeCard(card) {
  return NARRATIVE_CATEGORIES.has(card?.category) && NARRATIVE_ACTIONS.has(card?.action)
}

function changedByLabel(by) {
  if (!by) return 'Desconhecido'
  if (by.kind === 'SYSTEM') return by.name || 'Sistema'
  if (by.kind === 'UNKNOWN' && !by.name) return 'Desconhecido'
  return by.name || by.id || 'Desconhecido'
}

function formatEventDate(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
}

/** Ex.: "Removido da role employee por Athos em 03/08/2026 13:30" */
function narrativeSentence(card) {
  const prefix =
    NARRATIVE_PREFIX[card.category]?.[card.action]
    || `${actionLabel(card.action)} — ${categoryLabel(card.category).toLowerCase()}`
  const resource = card.resource?.name || card.resource?.id || '—'
  const who = changedByLabel(card.changed_by)
  const when = formatEventDate(card.event_date)
  if (card.target_user?.name && (props.queriedUsers?.length > 1 || userChips.value.length > 1)) {
    return `${prefix} ${resource} para ${card.target_user.name} por ${who} em ${when}`
  }
  return `${prefix} ${resource} por ${who} em ${when}`
}

function categoryBadgeClass(category) {
  if (category === 'group') return 'bg-violet-50 text-violet-700 border-violet-200'
  if (category === 'role') return 'bg-brand-soft text-brand border-brand/20'
  if (category === 'division') return 'bg-amber-50 text-amber-800 border-amber-200'
  if (category === 'queue') return 'bg-teal-50 text-teal-700 border-teal-200'
  return 'bg-gray-50 text-gray-600 border-gray-200'
}
</script>

<style scoped>
.category-chip {
  @apply px-2.5 py-1 rounded-full text-xs font-medium border transition-colors inline-flex items-center gap-1.5;
}
.chip-on {
  @apply bg-brand-soft border-brand/30 text-brand;
}
.chip-off {
  @apply bg-white border-gray-200 text-gray-500 hover:text-ink;
}
</style>
