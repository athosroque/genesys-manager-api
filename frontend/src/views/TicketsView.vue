<template>
  <div class="tickets-view p-6 bg-gray-50 min-h-screen">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-3xl font-bold text-gray-800">Smart Tickets</h1>
      <button 
        @click="syncTickets" 
        :disabled="isSyncing"
        class="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition flex items-center space-x-2 disabled:opacity-50"
      >
        <span v-if="isSyncing" class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></span>
        <span>{{ isSyncing ? 'Sincronizando...' : 'Sincronizar Chamados' }}</span>
      </button>
    </div>

    <!-- Tabs -->
    <div class="border-b border-gray-200 mb-6">
      <nav class="-mb-px flex space-x-8">
        <a 
          v-for="tab in tabs" 
          :key="tab.id"
          @click.prevent="activeTab = tab.id"
          :class="[
            activeTab === tab.id 
              ? 'border-indigo-500 text-indigo-600'
              : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700',
            'whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm cursor-pointer transition'
          ]"
        >
          {{ tab.name }}
        </a>
      </nav>
    </div>

    <!-- Tab Contents -->
    <div v-if="activeTab === 'dashboard'" class="space-y-6">
      <div class="bg-white p-6 rounded-lg shadow">
        <h2 class="text-xl font-semibold mb-4 text-gray-700">Métricas Principais</h2>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div class="bg-indigo-50 p-4 rounded-lg">
            <p class="text-sm text-indigo-600 font-medium">Total de Chamados</p>
            <p class="text-3xl font-bold text-indigo-900">{{ tickets.length }}</p>
          </div>
          <div class="bg-green-50 p-4 rounded-lg">
            <p class="text-sm text-green-600 font-medium">No FAQ</p>
            <p class="text-3xl font-bold text-green-900">{{ tickets.filter(t => t.is_faq).length }}</p>
          </div>
          <div class="bg-blue-50 p-4 rounded-lg">
            <p class="text-sm text-blue-600 font-medium">Classificações Automáticas</p>
            <p class="text-3xl font-bold text-blue-900">
              {{ tickets.filter(t => t.classification && t.classification !== 'Outros').length }}
            </p>
          </div>
        </div>
      </div>
      
      <!-- Chart section could go here with vue-chartjs -->
      <div class="bg-white p-6 rounded-lg shadow">
        <h2 class="text-xl font-semibold mb-4 text-gray-700">Distribuição de Status</h2>
        <div style="height: 300px; width: 100%; position: relative;">
            <Bar 
              v-if="chartData.labels.length"
              :data="chartData" 
              :options="chartOptions" 
            />
            <p v-else class="text-gray-500 mt-10 text-center">Carregando dados do gráfico...</p>
        </div>
      </div>
    </div>

    <div v-else-if="activeTab === 'classification'" class="bg-white rounded-lg shadow overflow-hidden">
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Título / Descrição</th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Classificação (Auto)</th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Ações</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr v-for="ticket in tickets" :key="ticket.id" class="hover:bg-gray-50 transition">
              <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                {{ ticket.external_id }}
              </td>
              <td class="px-6 py-4 text-sm text-gray-500">
                <div class="font-semibold text-gray-800">{{ ticket.title }}</div>
                <div class="text-xs mt-1 truncate max-w-xs">{{ ticket.description }}</div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">
                  {{ ticket.classification || 'N/A' }}
                </span>
                <span v-if="ticket.is_faq" class="ml-2 px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                  FAQ
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                <button @click="openEditModal(ticket)" class="text-indigo-600 hover:text-indigo-900">Revisar</button>
              </td>
            </tr>
            <tr v-if="tickets.length === 0">
              <td colspan="4" class="px-6 py-10 text-center text-gray-500">
                Nenhum chamado encontrado. Clique em "Sincronizar Chamados".
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-else-if="activeTab === 'kb'" class="space-y-6">
      <div class="bg-white p-6 rounded-lg shadow">
        <h2 class="text-xl font-semibold mb-4 text-gray-700">Top Categorias FAQ</h2>
        <ul class="divide-y divide-gray-200">
          <li v-for="cat in kbMetrics.top_categories" :key="cat.classification" class="py-3 flex justify-between items-center">
            <span class="font-medium text-gray-800">{{ cat.classification }}</span>
            <span class="bg-gray-100 text-gray-800 py-1 px-3 rounded-full text-xs font-semibold">{{ cat.count }} ocorrências</span>
          </li>
          <li v-if="!kbMetrics.top_categories?.length" class="py-3 text-gray-500 text-sm">
            Sem dados suficientes no momento.
          </li>
        </ul>
      </div>
      
      <div class="bg-white p-6 rounded-lg shadow">
        <h2 class="text-xl font-semibold mb-4 text-gray-700">Respostas Padrão Recentes</h2>
        <div class="space-y-4">
          <div v-for="faq in kbMetrics.recent_faqs" :key="faq.external_id" class="border border-gray-200 rounded-md p-4">
            <div class="flex justify-between items-start mb-2">
              <h3 class="text-md font-semibold text-gray-800">{{ faq.title }}</h3>
              <span class="text-xs bg-indigo-100 text-indigo-800 px-2 py-1 rounded">{{ faq.classification }}</span>
            </div>
            <p class="text-sm text-gray-600 bg-gray-50 p-3 rounded border-l-4 border-indigo-400">
              {{ faq.suggested_response }}
            </p>
          </div>
          <div v-if="!kbMetrics.recent_faqs?.length" class="text-gray-500 text-sm">
            Sem respostas padrão recentes.
          </div>
        </div>
      </div>
    </div>

    <!-- Edit Modal -->
    <div v-if="showModal" class="fixed z-10 inset-0 overflow-y-auto" aria-labelledby="modal-title" role="dialog" aria-modal="true">
      <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" @click="showModal = false" aria-hidden="true"></div>
        <span class="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
        <div class="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
          <div class="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
            <div class="sm:flex sm:items-start">
              <div class="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left w-full">
                <h3 class="text-lg leading-6 font-medium text-gray-900" id="modal-title">
                  Revisar Classificação: {{ selectedTicket?.external_id }}
                </h3>
                <div class="mt-4 space-y-4">
                  <div>
                    <p class="text-sm font-bold text-gray-700">Título</p>
                    <p class="text-sm text-gray-600">{{ selectedTicket?.title }}</p>
                  </div>
                  <div>
                    <p class="text-sm font-bold text-gray-700">Descrição</p>
                    <p class="text-sm text-gray-600 bg-gray-50 p-2 rounded">{{ selectedTicket?.description }}</p>
                  </div>
                  <div>
                    <p class="text-sm font-bold text-gray-700 mb-1">Classificação</p>
                    <input type="text" v-model="editForm.classification" class="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md py-2 px-3 border" />
                  </div>
                  <div class="flex items-center">
                    <input id="is_faq" name="is_faq" type="checkbox" v-model="editForm.is_faq" class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded">
                    <label for="is_faq" class="ml-2 block text-sm text-gray-900">
                      Adicionar à Base de Conhecimento (FAQ)
                    </label>
                  </div>
                  <div>
                    <p class="text-sm font-bold text-gray-700 mb-1">Resposta Sugerida (Apenas Leitura)</p>
                    <p class="text-sm text-gray-600 bg-gray-50 p-2 rounded italic border-l-4 border-blue-400">
                      {{ selectedTicket?.suggested_response || 'Sem sugestão' }}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
            <button @click="saveTicket" type="button" class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:ml-3 sm:w-auto sm:text-sm">
              Salvar
            </button>
            <button @click="showModal = false" type="button" class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm">
              Cancelar
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { request } from '../api/http';

// Chart imports
import { Bar } from 'vue-chartjs'
import { Chart as ChartJS, Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale } from 'chart.js'
ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale)

const activeTab = ref('dashboard');
const tabs = [
  { id: 'dashboard', name: 'Dashboard' },
  { id: 'classification', name: 'Classificação Automática' },
  { id: 'kb', name: 'Base de Conhecimento' }
];

const tickets = ref([]);
const isSyncing = ref(false);
const kbMetrics = ref({ top_categories: [], recent_faqs: [] });

// Modal state
const showModal = ref(false);
const selectedTicket = ref(null);
const editForm = ref({ classification: '', is_faq: false });

const loadTickets = async () => {
  try {
    const response = await request('/tickets/');
    tickets.value = response.tickets || [];
  } catch (error) {
    console.error("Error loading tickets:", error);
  }
};

const loadKbMetrics = async () => {
  try {
    const response = await request('/tickets/knowledge-base');
    kbMetrics.value = response || { top_categories: [], recent_faqs: [] };
  } catch (error) {
    console.error("Error loading KB metrics:", error);
  }
};

const syncTickets = async () => {
  isSyncing.value = true;
  try {
    await request('/tickets/sync', { method: 'POST' });
    await loadTickets();
    await loadKbMetrics();
  } catch (error) {
    console.error("Error syncing tickets:", error);
  } finally {
    isSyncing.value = false;
  }
};

const openEditModal = (ticket) => {
  selectedTicket.value = ticket;
  editForm.value = {
    classification: ticket.classification || '',
    is_faq: !!ticket.is_faq
  };
  showModal.value = true;
};

const saveTicket = async () => {
  try {
    await request(`/tickets/${selectedTicket.value.external_id}`, {
      method: 'PUT',
      body: JSON.stringify({
        classification: editForm.value.classification,
        is_faq: editForm.value.is_faq
      })
    });
    showModal.value = false;
    await loadTickets();
    await loadKbMetrics();
  } catch (error) {
    console.error("Error saving ticket:", error);
  }
};

// Chart Data Computed
const chartData = computed(() => {
  const statusCounts = {};
  tickets.value.forEach(t => {
    const status = t.status || 'Desconhecido';
    statusCounts[status] = (statusCounts[status] || 0) + 1;
  });
  
  return {
    labels: Object.keys(statusCounts),
    datasets: [
      {
        label: 'Quantidade de Chamados',
        backgroundColor: '#4f46e5', // indigo-600
        data: Object.values(statusCounts)
      }
    ]
  };
});

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
};

onMounted(() => {
  loadTickets();
  loadKbMetrics();
});
</script>
