<template>
  <div class="min-h-screen bg-slate-50 text-slate-800 font-sans p-6 md:p-8">
    <div class="max-w-7xl mx-auto space-y-6">
      
      <!-- Cabeçalho Principal -->
      <header class="mb-4">
        <h1 class="text-3xl font-extrabold tracking-tight text-slate-900">
          Dashboard de Diagnóstico <span class="text-blue-600">Genesys Cloud</span>
        </h1>
        <p class="text-slate-500 mt-1">Busque o histórico completo ou verifique as configurações do sistema.</p>
      </header>

      <!-- Navegação por Abas -->
      <div class="flex space-x-1 rounded-xl bg-slate-200/50 p-1 mb-8 w-fit">
        <button
          @click="activeTab = 'interaction'"
          :class="[
            'px-6 py-2.5 text-sm font-medium leading-5 rounded-lg transition-colors',
            activeTab === 'interaction'
              ? 'bg-white text-blue-700 shadow shadow-slate-200/50'
              : 'text-slate-600 hover:bg-white/60 hover:text-slate-900'
          ]"
        >
          Diagnóstico de Interações
        </button>
        <button
          @click="activeTab = 'system'"
          :class="[
            'px-6 py-2.5 text-sm font-medium leading-5 rounded-lg transition-colors',
            activeTab === 'system'
              ? 'bg-white text-blue-700 shadow shadow-slate-200/50'
              : 'text-slate-600 hover:bg-white/60 hover:text-slate-900'
          ]"
        >
          Diagnóstico de Sistema (Fluxos e Scripter)
        </button>
      </div>

      <!-- Aba: Diagnóstico de Interações -->
      <div v-show="activeTab === 'interaction'">
        <SearchHeader @search="fetchInteractionData" :isLoading="isLoading" />

        <!-- Mensagem de Erro -->
        <div v-if="errorMsg" class="bg-red-50 border-l-4 border-red-500 p-4 rounded-r-xl mt-6">
          <p class="text-sm font-bold text-red-900">Erro ao buscar dados</p>
          <p class="text-xs text-red-800">{{ errorMsg }}</p>
        </div>

        <!-- Área do Dashboard -->
        <div v-if="hasData" class="space-y-6 animate-fade-in-up mt-6">
          <ExecutiveHeader :details="interactionData.details" :calls="interactionData.calls" />
          <AuditOriginBanner :details="interactionData.details" />
          <InteractionTimeline :details="interactionData.details" />
          <QualityCard :details="interactionData.details" :calls="interactionData.calls" />
          <AdvancedAuditPanel :conversationId="currentConversationId" />
          <RawDataDrawer :details="interactionData.details" />
        </div>
      </div>

      <!-- Aba: Diagnóstico de Sistema -->
      <div v-show="activeTab === 'system'">
        <SystemDiagnosticPanel />
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { request } from '../api/http';
import SearchHeader from '../components/SearchHeader.vue';
import ExecutiveHeader from '../components/ExecutiveHeader.vue';
import AuditOriginBanner from '../components/AuditOriginBanner.vue';
import InteractionTimeline from '../components/InteractionTimeline.vue';
import QualityCard from '../components/QualityCard.vue';
import AdvancedAuditPanel from '../components/AdvancedAuditPanel.vue';
import RawDataDrawer from '../components/RawDataDrawer.vue';
import SystemDiagnosticPanel from '../components/SystemDiagnosticPanel.vue';

const activeTab = ref('interaction');
const isLoading = ref(false);
const errorMsg = ref('');
const interactionData = ref(null);
const currentConversationId = ref('');

const hasData = computed(() => interactionData.value && interactionData.value.details);

const fetchInteractionData = async (conversationId) => {
  isLoading.value = true;
  errorMsg.value = '';
  interactionData.value = null;
  currentConversationId.value = conversationId;

  try {
    const data = await request(`/diagnostics/${conversationId}`);
    interactionData.value = data;
  } catch (error) {
    console.error(error);
    errorMsg.value = error.message;
  } finally {
    isLoading.value = false;
  }
};
</script>

<style>
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
.animate-fade-in-up {
  animation: fadeInUp 0.5s ease-out forwards;
}
</style>
