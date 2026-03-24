<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
    <div 
      class="bg-gray-900 border border-gray-700/80 rounded-xl shadow-2xl w-full max-w-md overflow-hidden flex flex-col"
      role="dialog"
      aria-modal="true"
    >
      <!-- Header -->
      <div 
        class="px-6 py-4 border-b border-gray-800 flex items-center gap-3"
        :class="{
          'text-yellow-400': type === 'warning',
          'text-green-400': type === 'success',
          'text-blue-400': type === 'info',
        }"
      >
        <svg v-if="type === 'warning'" class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <svg v-else-if="type === 'success'" class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <svg v-else class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        
        <h2 class="text-lg font-semibold text-gray-100">{{ title }}</h2>
      </div>

      <!-- Body -->
      <div class="px-6 py-4 text-gray-300 text-sm">
        <p v-if="message" class="mb-4">{{ message }}</p>
        <slot></slot>
      </div>

      <!-- Footer/Actions -->
      <div class="px-6 py-4 bg-gray-950/50 border-t border-gray-800 flex justify-end gap-3 rounded-b-xl">
        <button 
          @click="$emit('cancel')"
          :disabled="loading"
          class="px-4 py-2 text-sm font-medium text-gray-300 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg transition-colors disabled:opacity-50"
        >
          {{ cancelLabel }}
        </button>
        <button 
          @click="$emit('confirm')"
          :disabled="loading"
          class="px-4 py-2 text-sm font-medium text-white rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50"
          :class="{
            'bg-blue-600 hover:bg-blue-500': type === 'info',
            'bg-yellow-600 hover:bg-yellow-500': type === 'warning',
            'bg-green-600 hover:bg-green-500': type === 'success',
          }"
        >
          <LoadingSpinner v-if="loading" class="w-4 h-4 text-white" />
          {{ confirmLabel }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import LoadingSpinner from './LoadingSpinner.vue'

defineProps({
  title: { type: String, required: true },
  message: { type: String, default: '' },
  confirmLabel: { type: String, default: 'Confirmar' },
  cancelLabel: { type: String, default: 'Cancelar' },
  type: { type: String, default: 'warning' }, // warning, success, info
  loading: { type: Boolean, default: false }
})

defineEmits(['confirm', 'cancel'])
</script>
