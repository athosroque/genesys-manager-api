<template>
  <div class="w-full">
    <form @submit.prevent="handleSearch" class="relative group">
      <div 
        class="absolute inset-y-0 left-0 pl-5 flex items-center pointer-events-none transition-colors"
        :class="isFocused ? 'text-brand' : 'text-gray-400'"
      >
        <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      </div>
      
      <input 
        v-model="query"
        type="text" 
        class="block w-full pl-12 pr-32 py-4 bg-white border border-gray-200 rounded-full leading-5 text-ink placeholder-gray-400 hover:border-gray-300 focus:outline-none focus:ring-2 focus:ring-brand/25 focus:border-brand transition-all sm:text-sm shadow-card"
        placeholder="Matrícula, e-mail ou ID"
        @focus="isFocused = true"
        @blur="isFocused = false"
        :disabled="loading"
        autofocus
      >
      
      <div class="absolute inset-y-2 right-2 flex items-center">
        <button
          type="submit"
          :disabled="!isValid || loading"
          class="btn-ice"
        >
          <span v-if="loading" class="flex items-center gap-2">
            <LoadingSpinner class="w-4 h-4 text-current" />
            <span class="hidden sm:inline">Buscando...</span>
          </span>
          <span v-else>Buscar</span>
        </button>
      </div>

      <!-- Sugestões por nome/e-mail (autocomplete) — clicar já dispara a busca -->
      <ul
        v-if="suggestions.length"
        class="absolute z-20 mt-2 w-full max-h-56 overflow-y-auto rounded-2xl border border-gray-100 bg-white shadow-card"
      >
        <li
          v-for="u in suggestions"
          :key="u.id"
          class="px-4 py-2.5 text-sm text-ink hover:bg-peach cursor-pointer first:rounded-t-2xl last:rounded-b-2xl"
          @click="selectSuggestion(u)"
        >
          <p class="font-medium">{{ u.name }}</p>
          <p class="text-xs text-gray-400">{{ u.email }} · {{ u.state }}</p>
        </li>
      </ul>
    </form>
    
    <div class="mt-3 flex items-center gap-2 text-xs text-gray-400 ml-1">
      <span class="text-amber-500">💡</span>
      <span>Matrícula → <strong class="text-gray-500 font-mono">@corp.caixa.gov.br</strong> adicionado automaticamente</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import LoadingSpinner from './LoadingSpinner.vue'
import { autocompleteUsers } from '../api/genesys'

const props = defineProps({
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['search'])

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

const query = ref('')
const isFocused = ref(false)
const suggestions = ref([])

const isValid = computed(() => query.value.trim().length > 0)

const handleSearch = () => {
  if (isValid.value && !props.loading) {
    suggestions.value = []
    emit('search', query.value.trim())
  }
}

// Autocomplete por nome/e-mail — mesmo padrão de AuditView.vue (aba "Por
// pessoa"): debounce de 300ms, ignora UUID completo (não tem o que sugerir).
let suppressQueryWatch = false
let debounceTimer = null

watch(query, (q) => {
  if (suppressQueryWatch) {
    suppressQueryWatch = false
    return
  }
  clearTimeout(debounceTimer)
  const trimmed = q.trim()
  if (props.loading || trimmed.length < 2 || UUID_RE.test(trimmed.replace(/[{}]/g, ''))) {
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

// Clicar numa sugestão já dispara a busca completa (auto-disparar), como se
// o UUID/e-mail exato tivesse sido digitado e o Buscar clicado.
function selectSuggestion(u) {
  suggestions.value = []
  suppressQueryWatch = true
  query.value = ''
  emit('search', u.id)
}
</script>
