<template>
  <div class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
    <!-- Header da Gaveta -->
    <div 
      class="p-4 bg-slate-50 border-b border-slate-200 flex justify-between items-center cursor-pointer hover:bg-slate-100 transition-colors"
      @click="isOpen = !isOpen"
    >
      <h3 class="text-base font-bold text-slate-800 flex items-center gap-2">
        <span class="text-xl">🗂️</span> Gaveta de Dados Brutos (JSON)
      </h3>
      <button class="text-slate-500 hover:text-slate-700 font-bold">
        {{ isOpen ? 'Ocultar ▲' : 'Exibir Detalhes ▼' }}
      </button>
    </div>
    
    <!-- Conteúdo da Gaveta (Sanfona) -->
    <div v-show="isOpen" class="p-0 border-t border-slate-200 bg-slate-900">
      <div class="flex border-b border-slate-700 bg-slate-800">
        <button 
          class="px-4 py-2 text-sm font-medium focus:outline-none text-blue-400 border-b-2 border-blue-400"
        >
          _details.json
        </button>
        <div class="ml-auto p-2 flex gap-2">
           <button 
             @click="downloadJson"
             class="bg-slate-600 hover:bg-slate-500 text-white text-xs px-3 py-1 rounded transition-colors"
           >
             Download JSON
           </button>
           <button 
             @click="copyJson"
             class="bg-blue-600 hover:bg-blue-500 text-white text-xs px-3 py-1 rounded transition-colors"
           >
             Copiar JSON
           </button>
        </div>
      </div>
      <div class="p-4 max-h-96 overflow-y-auto custom-scrollbar">
        <pre class="text-xs text-green-400 font-mono"><code>{{ formattedJson }}</code></pre>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';

const props = defineProps({
  details: {
    type: Object,
    default: () => ({})
  }
});

const isOpen = ref(false);

const formattedJson = computed(() => {
  return JSON.stringify(props.details, null, 2);
});

const copyJson = () => {
  navigator.clipboard.writeText(formattedJson.value);
};

const downloadJson = () => {
  const blob = new Blob([formattedJson.value], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  const conversationId = props.details.conversationId || 'interacao';
  a.download = `details_${conversationId}.json`;
  a.click();
  URL.revokeObjectURL(url);
};
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: #1e293b; 
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #475569; 
  border-radius: 4px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: #64748b; 
}
</style>
