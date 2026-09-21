<template>
  <div class="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden mt-6">
    <div class="p-5 border-b border-slate-100 flex items-center justify-between bg-slate-50">
      <div>
        <h2 class="text-lg font-bold text-slate-800 flex items-center gap-2">
          <svg class="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path></svg>
          Auditoria Avançada
        </h2>
        <p class="text-sm text-slate-500 mt-1">Busca aprofundada de configurações (Filas, ACW, Copilot e Permissões)</p>
      </div>
      <button 
        @click="runAudit" 
        :disabled="isAuditing"
        class="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg text-sm font-semibold shadow-sm transition-colors flex items-center gap-2 disabled:opacity-50"
      >
        <svg v-if="isAuditing" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
        {{ isAuditing ? 'Analisando...' : 'Gerar JSON de Auditoria' }}
      </button>
    </div>

    <div v-if="auditResult" class="p-5 border-b border-slate-100 bg-amber-50" v-show="showMultipleWarning">
      <div class="flex items-start gap-3 text-amber-800">
        <svg class="w-5 h-5 mt-0.5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
        <div class="flex-1">
          <p class="font-bold text-sm">Múltiplos IDs Identificados</p>
          <p class="text-xs mt-1 text-amber-700">Foram identificadas múltiplas filas ou múltiplos usuários nesta interação. A auditoria utilizou o primeiro ID de cada, mas você pode sobrescrever abaixo se desejar re-executar.</p>
          
          <div class="mt-3 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold mb-1 text-amber-900">Fila Selecionada</label>
              <select v-model="selectedQueueId" class="w-full text-xs p-2 rounded border border-amber-300 bg-white">
                <option v-for="q in auditResult.found_queues" :key="q.id" :value="q.id">{{ q.name }}</option>
                <option value="">Sem fila</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-semibold mb-1 text-amber-900">Usuário Selecionado</label>
              <select v-model="selectedUserId" class="w-full text-xs p-2 rounded border border-amber-300 bg-white">
                <option v-for="u in auditResult.found_users" :key="u.id" :value="u.id">{{ u.name }}</option>
                <option value="">Sem usuário</option>
              </select>
            </div>
          </div>
          <button @click="runAuditWithCustomIds" class="mt-3 text-xs bg-amber-600 text-white px-3 py-1.5 rounded hover:bg-amber-700 transition-colors font-medium">Re-executar Auditoria com IDs selecionados</button>
        </div>
      </div>
    </div>

    <div v-if="error" class="p-5 text-sm text-red-600 bg-red-50 border-t border-red-100">
      Erro: {{ error }}
    </div>

    <div v-if="auditResult" class="p-0 border-t border-slate-100">
      <div class="bg-slate-900 text-green-400 p-4 overflow-x-auto text-xs font-mono relative max-h-96">
        <div class="absolute top-4 right-4 flex gap-2">
          <button @click="downloadJson" class="bg-slate-700 hover:bg-slate-600 text-slate-200 px-3 py-1 rounded text-xs border border-slate-500 transition-colors">
            Download JSON
          </button>
          <button @click="copyJson" class="bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1 rounded text-xs border border-slate-600 transition-colors">
            {{ copied ? 'Copiado!' : 'Copiar JSON' }}
          </button>
        </div>
        <pre>{{ formattedJson }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { request } from '../api/http';

const props = defineProps({
  conversationId: {
    type: String,
    required: true
  }
});

const isAuditing = ref(false);
const auditResult = ref(null);
const error = ref('');
const copied = ref(false);

const selectedQueueId = ref('');
const selectedUserId = ref('');

const showMultipleWarning = computed(() => {
  if (!auditResult.value) return false;
  return (auditResult.value.found_queues?.length > 1) || (auditResult.value.found_users?.length > 1);
});

const formattedJson = computed(() => {
  if (!auditResult.value) return '';
  return JSON.stringify(auditResult.value.audit_data, null, 2);
});

const runAudit = async () => {
  await executeRequest({});
};

const runAuditWithCustomIds = async () => {
  await executeRequest({
    queue_id: selectedQueueId.value,
    user_id: selectedUserId.value
  });
};

const executeRequest = async (params) => {
  isAuditing.value = true;
  error.value = '';
  
  try {
    const queryParts = [];
    if (params.queue_id) queryParts.push(`queue_id=${params.queue_id}`);
    if (params.user_id) queryParts.push(`user_id=${params.user_id}`);
    
    const queryString = queryParts.length > 0 ? `?${queryParts.join('&')}` : '';
    const res = await request(`/diagnostics/${props.conversationId}/advanced-audit${queryString}`);
    
    auditResult.value = res;
    
    // Set initial values if not set
    if (!selectedQueueId.value && res.used_queue_id) {
      selectedQueueId.value = res.used_queue_id;
    }
    if (!selectedUserId.value && res.used_user_id) {
      selectedUserId.value = res.used_user_id;
    }
    
  } catch (err) {
    console.error(err);
    error.value = err.message;
  } finally {
    isAuditing.value = false;
  }
};

const copyJson = async () => {
  try {
    await navigator.clipboard.writeText(formattedJson.value);
    copied.value = true;
    setTimeout(() => copied.value = false, 2000);
  } catch (err) {
    console.error('Failed to copy: ', err);
  }
};

const downloadJson = () => {
  const blob = new Blob([formattedJson.value], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `audit_${props.conversationId}.json`;
  a.click();
  URL.revokeObjectURL(url);
};
</script>
