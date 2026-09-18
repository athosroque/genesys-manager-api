<template>
  <div class="min-h-screen bg-slate-50 text-slate-800 font-sans p-6 md:p-8">
    <div class="max-w-7xl mx-auto space-y-6">
      
      <!-- Cabeçalho Principal e Input -->
      <header class="mb-8">
        <h1 class="text-3xl font-extrabold tracking-tight text-slate-900">
          Dashboard de Diagnóstico <span class="text-blue-600">Genesys Cloud</span>
        </h1>
        <p class="text-slate-500 mt-1">Busque o histórico completo e métricas de qualidade de uma interação</p>
      </header>

      <SearchHeader @search="fetchInteractionData" :isLoading="isLoading" />

      <!-- Mensagem de Erro -->
      <div v-if="errorMsg" class="bg-red-50 border-l-4 border-red-500 p-4 rounded-r-xl">
        <p class="text-sm font-bold text-red-900">Erro ao buscar dados</p>
        <p class="text-xs text-red-800">{{ errorMsg }}</p>
      </div>

      <!-- Área do Dashboard -->
      <div v-if="hasData" class="space-y-6 animate-fade-in-up">
        
        <ExecutiveHeader :details="interactionData.details" :calls="interactionData.calls" />
        
        <AuditOriginBanner :details="interactionData.details" />
        
        <InteractionTimeline :details="interactionData.details" />
        
        <QualityCard :details="interactionData.details" :calls="interactionData.calls" />
        
        <AdvancedAuditPanel :conversationId="currentConversationId" />
        
        <RawDataDrawer :details="interactionData.details" />
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
