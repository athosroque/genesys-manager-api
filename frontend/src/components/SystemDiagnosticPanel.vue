<template>
  <div class="space-y-8 animate-fade-in-up">
    <!-- Bloco de Fluxo -->
    <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
      <div class="flex flex-col md:flex-row md:items-center justify-between mb-6">
        <div>
          <h2 class="text-xl font-bold text-slate-800">Diagnóstico de Fluxo Architect</h2>
          <p class="text-sm text-slate-500 mt-1">Insira o Nome ou ID do Fluxo para analisar suas tarefas e roteamento.</p>
          <ul class="mt-2 space-y-0.5 text-[11px] font-mono text-slate-400 leading-snug">
            <li>GET /api/v2/flows?name={nome}</li>
            <li>GET /api/v2/flows/{flowId}/latestconfiguration</li>
          </ul>
        </div>
      </div>
      
      <div class="flex flex-col sm:flex-row gap-4 mb-6">
        <input 
          v-model="flowInput" 
          type="text" 
          placeholder="Ex: URA_ROTEAMENTO_TRANSFERENCIAS ou UUID"
          class="flex-1 rounded-xl border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-4 py-2 border"
          @keyup.enter="fetchFlow"
        />
        <button 
          @click="fetchFlow"
          :disabled="isFlowLoading || !flowInput"
          class="inline-flex items-center justify-center rounded-xl bg-blue-600 px-6 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span v-if="isFlowLoading" class="mr-2 animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></span>
          Consultar Fluxo
        </button>
      </div>

      <div v-if="flowError" class="mb-4 bg-red-50 border-l-4 border-red-500 p-4 rounded">
        <p class="text-sm text-red-800">{{ flowError }}</p>
      </div>

      <div v-if="flowData" class="space-y-4">
        <div class="flex justify-between items-center bg-slate-50 p-4 rounded-xl border border-slate-200">
          <div>
            <h3 class="font-semibold text-slate-800">{{ flowData.summary.name }}</h3>
            <p class="text-xs text-slate-500">ID: {{ flowData.summary.flowId }} | Tipo: {{ flowData.summary.type }}</p>
          </div>
          <button @click="downloadJson(flowData.raw, `flow_${flowData.summary.name}.json`)" class="text-sm text-blue-600 hover:text-blue-800 font-medium">
            ↓ Download JSON Completo
          </button>
        </div>

        <div class="max-h-96 overflow-y-auto pr-2 space-y-3">
          <div v-for="(task, index) in flowData.summary.tasks" :key="index" class="bg-white border border-slate-200 rounded-lg p-4">
            <h4 class="font-bold text-slate-700 mb-2 border-b pb-2">Tarefa: {{ task.name }}</h4>
            <div v-if="task.actions.length === 0" class="text-sm text-slate-400 italic">Sem ações relevantes mapeadas.</div>
            <ul v-else class="space-y-3 mt-3">
              <li v-for="(action, aIndex) in task.actions" :key="aIndex" class="text-sm bg-slate-50 p-3 rounded border border-slate-100">
                <div class="font-semibold text-slate-800 flex items-center gap-2">
                  <span class="px-2 py-0.5 rounded text-xs bg-indigo-100 text-indigo-800">{{ action.type }}</span>
                  {{ action.name }}
                </div>
                <div class="mt-2 text-slate-600 ml-2">
                  <pre class="whitespace-pre-wrap text-xs bg-white p-2 rounded border border-slate-200">{{ JSON.stringify(action.details, null, 2) }}</pre>
                </div>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>

    <!-- Bloco de Script -->
    <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
      <div class="flex flex-col md:flex-row md:items-center justify-between mb-6">
        <div>
          <h2 class="text-xl font-bold text-slate-800">Diagnóstico de Script (Scripter)</h2>
          <p class="text-sm text-slate-500 mt-1">Busque um script pelo nome exato para verificar páginas e propriedades de callback.</p>
          <ul class="mt-2 space-y-0.5 text-[11px] font-mono text-slate-400 leading-snug">
            <li>GET /api/v2/scripts?name={nome}</li>
            <li>GET /api/v2/scripts/published/{scriptId}/pages</li>
            <li>GET /api/v2/scripts/published/{scriptId}/pages/{pageId}</li>
          </ul>
        </div>
      </div>
      
      <div class="flex flex-col sm:flex-row gap-4 mb-6">
        <input 
          v-model="scriptInput" 
          type="text" 
          placeholder="Ex: Atendimento_Voz_Bolsa_Familia_Callback"
          class="flex-1 rounded-xl border-slate-300 shadow-sm focus:border-green-500 focus:ring-green-500 sm:text-sm px-4 py-2 border"
          @keyup.enter="fetchScript"
        />
        <button 
          @click="fetchScript"
          :disabled="isScriptLoading || !scriptInput"
          class="inline-flex items-center justify-center rounded-xl bg-green-600 px-6 py-2 text-sm font-semibold text-white shadow-sm hover:bg-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span v-if="isScriptLoading" class="mr-2 animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></span>
          Consultar Script
        </button>
      </div>

      <div v-if="scriptError" class="mb-4 bg-red-50 border-l-4 border-red-500 p-4 rounded">
        <p class="text-sm text-red-800">{{ scriptError }}</p>
      </div>

      <div v-if="scriptData" class="space-y-4">
        <div class="flex justify-between items-center bg-slate-50 p-4 rounded-xl border border-slate-200">
          <div>
            <h3 class="font-semibold text-slate-800">{{ scriptData.raw.name }}</h3>
            <p class="text-xs text-slate-500">ID: {{ scriptData.raw.id }}</p>
          </div>
          <button @click="downloadJson(scriptData.raw, `script_${scriptData.raw.name}.json`)" class="text-sm text-green-600 hover:text-green-800 font-medium">
            ↓ Download JSON Completo
          </button>
        </div>

        <div class="max-h-96 overflow-y-auto pr-2 space-y-3">
          <div v-if="scriptData.summary.length === 0" class="text-sm text-slate-500 italic p-4 text-center bg-white border border-slate-200 rounded-lg">
            Nenhum elemento relacionado a Callback encontrado nas páginas deste script.
          </div>
          
          <div v-for="(page, index) in scriptData.summary" :key="index" class="bg-white border border-slate-200 rounded-lg p-4">
            <h4 class="font-bold text-slate-700 mb-2 border-b pb-2">Página: {{ page.page_name }}</h4>
            <ul class="space-y-3 mt-3">
              <li v-for="(el, eIndex) in page.elements" :key="eIndex" class="text-sm bg-slate-50 p-3 rounded border border-slate-100">
                <div class="font-semibold text-slate-800 flex items-center gap-2">
                  <span class="px-2 py-0.5 rounded text-xs bg-emerald-100 text-emerald-800">{{ el.type }}</span>
                  {{ el.name }}
                </div>
                <div class="mt-2 grid grid-cols-2 gap-2 text-xs text-slate-600 ml-2">
                  <div v-if="el.text"><strong>Texto:</strong> <pre class="inline">{{ JSON.stringify(el.text) }}</pre></div>
                  <div v-if="el.visible"><strong>Visible:</strong> <pre class="inline">{{ JSON.stringify(el.visible) }}</pre></div>
                </div>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { request } from '../api/http';

const flowInput = ref('');
const isFlowLoading = ref(false);
const flowData = ref(null);
const flowError = ref('');

const scriptInput = ref('');
const isScriptLoading = ref(false);
const scriptData = ref(null);
const scriptError = ref('');

const fetchFlow = async () => {
  if (!flowInput.value) return;
  isFlowLoading.value = true;
  flowError.value = '';
  flowData.value = null;
  
  try {
    const data = await request(`/system-diagnostics/flow?name_or_id=${encodeURIComponent(flowInput.value)}`);
    flowData.value = data;
  } catch (err) {
    flowError.value = err.message || 'Erro ao buscar fluxo';
  } finally {
    isFlowLoading.value = false;
  }
};

const fetchScript = async () => {
  if (!scriptInput.value) return;
  isScriptLoading.value = true;
  scriptError.value = '';
  scriptData.value = null;
  
  try {
    const data = await request(`/system-diagnostics/script?name=${encodeURIComponent(scriptInput.value)}`);
    scriptData.value = data;
  } catch (err) {
    scriptError.value = err.message || 'Erro ao buscar script';
  } finally {
    isScriptLoading.value = false;
  }
};

const downloadJson = (data, filename) => {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};
</script>
