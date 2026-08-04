<template>
  <div class="space-y-4">
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
        class="ml-auto text-xs font-medium text-gray-400 bg-gray-800 rounded-full px-3 py-1"
      >
        {{ filtered.length }} de {{ changes.length }} alteração{{ changes.length === 1 ? '' : 'ões' }}
      </span>
    </div>

    <div
      v-if="truncated || truncatedCategoryLabels.length"
      class="space-y-1 text-xs text-amber-400/90"
      data-testid="truncated-warning"
    >
      <p v-if="truncatedCategoryLabels.length">
        Varredura parcial em
        <span class="font-medium text-amber-300">{{ truncatedCategoryLabels.join(', ') }}</span>:
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
        class="rounded-xl border border-gray-700 bg-gray-900/80 px-4 py-3.5 space-y-3"
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
            <p class="text-sm text-gray-100 leading-snug break-words">
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
              <div class="min-w-0">
                <p class="text-sm font-semibold text-gray-100 truncate">
                  {{ card.resource?.name || card.resource?.id || 'Recurso' }}
                </p>
                <p v-if="card.action" class="text-xs text-gray-500 mt-0.5">
                  {{ actionLabel(card.action) }}
                </p>
              </div>
            </div>
          </div>

          <div class="flex flex-wrap items-stretch gap-2 text-xs sm:gap-3">
            <div class="min-w-[8rem] flex-1 rounded-lg bg-gray-800/70 border border-gray-800 px-3 py-2">
              <p class="text-[10px] uppercase tracking-wider text-gray-500 mb-1">Antes</p>
              <p class="text-gray-200 break-words">{{ displayValue(card.before) }}</p>
            </div>
            <div class="hidden sm:flex items-center text-gray-600 shrink-0" aria-hidden="true">→</div>
            <div class="min-w-[8rem] flex-1 rounded-lg bg-gray-800/70 border border-gray-800 px-3 py-2">
              <p class="text-[10px] uppercase tracking-wider text-gray-500 mb-1">Depois</p>
              <p class="text-gray-200 break-words">{{ displayValue(card.after) }}</p>
            </div>
          </div>

          <div class="flex flex-wrap items-center justify-between gap-2 text-xs text-gray-400">
            <p>
              <span class="text-gray-500">Alterado por</span>
              {{ changedByLabel(card.changed_by) }}
            </p>
            <p class="font-mono text-gray-500">{{ formatEventDate(card.event_date) }}</p>
          </div>
        </template>
      </article>
    </div>

    <div
      v-else
      class="rounded-xl border border-dashed border-gray-700 p-6 text-center text-sm text-gray-500"
    >
      Nenhuma alteração nesta categoria — escolha “Todas” ou outro filtro.
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

watch(
  () => props.changes,
  () => {
    categoryFilter.value = 'all'
  },
)

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
  return `${prefix} ${resource} por ${who} em ${when}`
}

function categoryBadgeClass(category) {
  if (category === 'group') return 'bg-violet-900/40 text-violet-300 border-violet-800/50'
  if (category === 'role') return 'bg-blue-900/40 text-blue-300 border-blue-800/50'
  if (category === 'division') return 'bg-amber-900/40 text-amber-300 border-amber-800/50'
  if (category === 'queue') return 'bg-teal-900/40 text-teal-300 border-teal-800/50'
  return 'bg-gray-800 text-gray-300 border-gray-700'
}
</script>

<style scoped>
.category-chip {
  @apply px-2.5 py-1 rounded-full text-xs font-medium border transition-colors inline-flex items-center gap-1.5;
}
.chip-on {
  @apply bg-blue-600/20 border-blue-700 text-blue-300;
}
.chip-off {
  @apply bg-gray-800 border-gray-700 text-gray-400 hover:text-gray-200;
}
</style>
