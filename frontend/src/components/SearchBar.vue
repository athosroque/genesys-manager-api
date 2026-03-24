<template>
  <div class="w-full max-w-2xl mx-auto">
    <form @submit.prevent="handleSearch" class="relative group">
      <div 
        class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none transition-colors"
        :class="isFocused ? 'text-blue-400' : 'text-gray-500'"
      >
        <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      </div>
      
      <input 
        v-model="query"
        type="text" 
        class="block w-full pl-11 pr-32 py-4 bg-gray-900 border border-gray-700 rounded-xl leading-5 text-gray-100 placeholder-gray-500 hover:border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all sm:text-sm shadow-sm"
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
          class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-lg text-white transition-all shadow-sm"
          :class="[
            !isValid || loading 
              ? 'bg-gray-800 text-gray-500 cursor-not-allowed border-gray-700' 
              : 'bg-blue-600 hover:bg-blue-500 hover:shadow-blue-900/20 hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 focus:ring-offset-gray-900'
          ]"
        >
          <span v-if="loading" class="flex items-center gap-2">
            <LoadingSpinner class="w-4 h-4 text-gray-400" />
            <span class="hidden sm:inline">Buscando...</span>
          </span>
          <span v-else>
            🔍 Buscar
          </span>
        </button>
      </div>
    </form>
    
    <div class="mt-3 flex items-center gap-2 text-xs text-gray-500 ml-1">
      <span class="text-yellow-500/80">💡</span>
      <span>Matrícula → <strong class="text-gray-400 font-mono">@corp.caixa.gov.br</strong> adicionado automaticamente</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import LoadingSpinner from './LoadingSpinner.vue'

const props = defineProps({
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['search'])

const query = ref('')
const isFocused = ref(false)

const isValid = computed(() => query.value.trim().length > 0)

const handleSearch = () => {
  if (isValid.value && !props.loading) {
    emit('search', query.value.trim())
  }
}
</script>
