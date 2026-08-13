<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/40 backdrop-blur-sm">
    <div 
      class="bg-white border border-black/[0.06] rounded-3xl shadow-card w-full max-w-md overflow-hidden flex flex-col"
      role="dialog"
      aria-modal="true"
    >
      <!-- Header -->
      <div 
        class="px-6 py-4 border-b border-gray-100 flex items-center gap-3"
        :class="{
          'text-amber-600': type === 'warning',
          'text-red-600': type === 'danger',
          'text-green-600': type === 'success',
          'text-brand': type === 'info',
        }"
      >
        <svg v-if="type === 'warning' || type === 'danger'" class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <svg v-else-if="type === 'success'" class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <svg v-else class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        
        <h2 class="text-lg font-semibold text-ink">{{ title }}</h2>
      </div>

      <!-- Body -->
      <div class="px-6 py-4 text-gray-600 text-sm">
        <p v-if="message" class="mb-4">{{ message }}</p>
        <slot></slot>
      </div>

      <!-- Footer/Actions -->
      <div class="px-6 py-4 bg-gray-50/80 border-t border-gray-100 flex justify-end gap-3">
        <button 
          @click="$emit('cancel')"
          :disabled="loading"
          class="btn-secondary disabled:opacity-50"
        >
          {{ cancelLabel }}
        </button>
        <button 
          @click="$emit('confirm')"
          :disabled="loading"
          class="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-semibold text-white rounded-full transition-colors disabled:opacity-50"
          :class="{
            'bg-brand hover:bg-brand-hover': type === 'info',
            'bg-amber-500 hover:bg-amber-600': type === 'warning',
            'bg-red-600 hover:bg-red-500': type === 'danger',
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
  type: { type: String, default: 'warning' }, // warning, danger, success, info
  loading: { type: Boolean, default: false }
})

defineEmits(['confirm', 'cancel'])
</script>
