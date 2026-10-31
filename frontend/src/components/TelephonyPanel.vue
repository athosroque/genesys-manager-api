<template>
  <div class="card overflow-hidden" data-testid="telephony-panel">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 px-5 py-4 border-b border-gray-100 bg-white">
      <div class="flex items-center gap-3">
        <div class="p-2.5 rounded-xl bg-purple-50 text-purple-600 shrink-0">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
          </svg>
        </div>
        <div>
          <div class="flex items-center gap-2">
            <h3 class="text-sm font-semibold text-ink">Telefonia e Ramal</h3>
            <span
              v-if="telephony && !loading"
              class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold tracking-wide"
              :class="telephony.is_healthy ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'"
            >
              <span
                class="w-1.5 h-1.5 rounded-full"
                :class="telephony.is_healthy ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'"
              />
              {{ telephony.is_healthy ? 'Cenário 1: Íntegro' : 'Cenário 2: Inconsistente' }}
            </span>
          </div>
          <p class="text-xs text-gray-400 mt-0.5">Diagnóstico WebRTC · Estação Efetiva · Status da Conexão · Telefone Base</p>
        </div>
      </div>

      <div class="flex items-center gap-2 shrink-0">
        <button
          v-if="telephony"
          type="button"
          @click="openDeleteDialog"
          class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-red-700 bg-red-50 border border-red-200 rounded-xl hover:bg-red-100 transition-colors"
          data-testid="open-delete-phone"
        >
          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
          Excluir Ramal
        </button>

        <button
          type="button"
          :disabled="loading"
          @click="fetchTelephony"
          class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-brand bg-brand-soft rounded-xl hover:bg-brand-soft/80 transition-colors disabled:opacity-50"
        >
          <svg
            class="w-3.5 h-3.5"
            :class="{ 'animate-spin': loading }"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          {{ loading ? 'Atualizando…' : 'Recarregar' }}
        </button>
      </div>
    </div>

    <!-- Body Content -->
    <div class="p-5 space-y-4">
      <!-- Loading State -->
      <div v-if="loading" class="flex items-center justify-center gap-3 py-8 text-brand">
        <div class="w-5 h-5 [&_svg]:w-5 [&_svg]:h-5">
          <LoadingSpinner />
        </div>
        <span class="text-sm text-gray-500">Consultando diagnóstico de telefonia no Genesys Cloud...</span>
      </div>

      <!-- Error State -->
      <div
        v-else-if="error"
        class="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 flex items-start justify-between gap-3"
      >
        <div>
          <p class="font-semibold text-red-800">Falha ao consultar telefonia</p>
          <p class="mt-1 font-mono text-xs text-red-600">{{ error }}</p>
        </div>
        <button
          @click="fetchTelephony"
          class="px-2.5 py-1 text-xs font-medium bg-red-100 hover:bg-red-200 text-red-800 rounded-lg shrink-0 transition-colors"
        >
          Tentar novamente
        </button>
      </div>

      <!-- Telephony Data -->
      <template v-else-if="telephony">
        <!-- Grid dos 3 Pilares -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
          <!-- Pilar 1: Estação Atribuída -->
          <div class="rounded-xl border border-gray-100 bg-gray-50/60 p-3.5 space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-[11px] font-bold uppercase tracking-wider text-gray-400">1. Estação / Ramal</span>
              <span
                class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold"
                :class="telephony.summary?.station_assigned ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'"
              >
                <span class="w-1.5 h-1.5 rounded-full" :class="telephony.summary?.station_assigned ? 'bg-emerald-500' : 'bg-rose-500'" />
                {{ telephony.summary?.station_assigned ? 'Atribuída' : 'Não Atribuída' }}
              </span>
            </div>

            <div>
              <p class="text-sm font-semibold text-ink truncate" :title="telephony.station?.name || 'Sem estação'">
                {{ telephony.station?.name || 'Nenhuma Estação' }}
              </p>
              <div class="mt-1 space-y-0.5 text-xs text-gray-500">
                <p v-if="telephony.station?.type">
                  <span class="text-gray-400">Tipo:</span> <span class="font-mono">{{ telephony.station.type }}</span>
                </p>
                <p v-if="telephony.station?.id">
                  <span class="text-gray-400">ID:</span> <span class="font-mono text-[11px] text-gray-400">{{ telephony.station.id.slice(0, 8) }}…</span>
                </p>
                <p v-if="!telephony.station" class="text-xs text-rose-600 font-medium">
                  Usuário sem ramal atribuído.
                </p>
              </div>
            </div>
          </div>

          <!-- Pilar 2: Conexão da Estação -->
          <div class="rounded-xl border border-gray-100 bg-gray-50/60 p-3.5 space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-[11px] font-bold uppercase tracking-wider text-gray-400">2. Conexão</span>
              <span
                class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold"
                :class="telephony.summary?.station_associated ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'"
              >
                <span
                  class="w-1.5 h-1.5 rounded-full"
                  :class="telephony.summary?.station_associated ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'"
                />
                {{ telephony.station?.status || 'DESCONECTADO' }}
              </span>
            </div>

            <div>
              <p class="text-sm font-semibold text-ink">
                {{ telephony.station?.is_associated ? 'Estação Conectada' : (telephony.station?.status || 'Sem Conexão') }}
              </p>
              <div class="mt-1 space-y-0.5 text-xs text-gray-500">
                <p v-if="telephony.station?.line_appearance_id">
                  <span class="text-gray-400">Line:</span> <span class="font-mono text-[11px]">{{ telephony.station.line_appearance_id.slice(0, 12) }}…</span>
                </p>
                <p v-if="telephony.station?.status === 'DISASSOCIATED'" class="text-xs text-amber-700">
                  Desconectada (concorrência de aba/sessão).
                </p>
                <p v-else-if="!telephony.station" class="text-xs text-gray-400">
                  Aguardando atribuição de estação.
                </p>
              </div>
            </div>
          </div>

          <!-- Pilar 3: Telefone Base -->
          <div class="rounded-xl border border-gray-100 bg-gray-50/60 p-3.5 space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-[11px] font-bold uppercase tracking-wider text-gray-400">3. Telefone Base</span>
              <span
                class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold"
                :class="telephony.summary?.phone_active ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'"
              >
                <span class="w-1.5 h-1.5 rounded-full" :class="telephony.summary?.phone_active ? 'bg-emerald-500' : 'bg-rose-500'" />
                {{ telephony.summary?.phone_active ? 'Ativo com Site' : 'Inconsistente' }}
              </span>
            </div>

            <div>
              <p class="text-sm font-semibold text-ink truncate" :title="telephony.phone?.name || 'Sem telefone'">
                {{ telephony.phone?.name || 'Nenhum Telefone Base' }}
              </p>
              <div class="mt-1 space-y-0.5 text-xs text-gray-500">
                <p v-if="telephony.phone?.site">
                  <span class="text-gray-400">Site:</span> <span class="font-medium text-ink">{{ telephony.phone.site.name }}</span>
                </p>
                <p v-else class="text-rose-600 font-medium">
                  Sem Site vinculado
                </p>
                <p v-if="telephony.phone?.phone_base_settings">
                  <span class="text-gray-400">Template:</span> <span class="text-gray-600">{{ telephony.phone.phone_base_settings.name }}</span>
                </p>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- Exclusão de Ramal -->
    <ConfirmDialog
      v-if="showDeleteDialog"
      title="Excluir Ramal"
      type="danger"
      confirm-label="Excluir"
      :loading="deleteLoading"
      @cancel="closeDeleteDialog"
      @confirm="handleDeletePhone"
    >
      <div class="space-y-3" data-testid="delete-phone-dialog">
        <!-- Ramal atribuído ao agente -->
        <template v-if="deleteMode === 'assigned'">
          <p>Ramal atribuído a <span class="font-semibold text-ink">{{ telephony?.user_name || 'este agente' }}</span>:</p>
          <div class="rounded-xl border border-red-200 bg-red-50/60 p-3">
            <p class="text-sm font-semibold text-ink">{{ telephony.phone.name }}</p>
            <p v-if="telephony.phone.site" class="text-xs text-gray-500">Site: {{ telephony.phone.site.name }}</p>
          </div>
          <button
            type="button"
            class="text-xs font-medium text-brand hover:underline"
            @click="deleteMode = 'search'"
          >
            Excluir outro ramal
          </button>
        </template>

        <!-- Sem ramal atribuído: solicita o ramal -->
        <template v-else>
          <p v-if="!telephony?.phone" class="text-xs text-amber-700">
            Este agente não possui ramal atribuído. Informe o ramal que deve ser excluído.
          </p>
          <form class="flex gap-2" @submit.prevent="runPhoneSearch">
            <input
              v-model="phoneQuery"
              type="text"
              placeholder="Nome do ramal (ex.: p523303)"
              class="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand/30"
              data-testid="phone-search-input"
            />
            <button
              type="submit"
              :disabled="phoneQuery.trim().length < 2 || searchLoading"
              class="btn-secondary disabled:opacity-50"
            >
              {{ searchLoading ? 'Buscando…' : 'Buscar' }}
            </button>
          </form>

          <p v-if="searchError" class="text-xs text-red-600">{{ searchError }}</p>
          <p v-else-if="searched && !phoneResults.length" class="text-xs text-gray-500">Nenhum ramal encontrado.</p>

          <ul v-if="phoneResults.length" class="max-h-56 overflow-y-auto space-y-1.5">
            <li v-for="p in phoneResults" :key="p.id">
              <label
                class="flex items-start gap-2 p-2.5 rounded-xl border cursor-pointer transition-colors"
                :class="selectedPhone?.id === p.id ? 'border-red-300 bg-red-50/60' : 'border-gray-100 hover:bg-gray-50'"
              >
                <input v-model="selectedPhone" type="radio" :value="p" class="mt-1" />
                <span class="min-w-0">
                  <span class="block text-sm font-semibold text-ink truncate">{{ p.name }}</span>
                  <span class="block text-xs text-gray-500">
                    {{ p.web_rtc_user?.name ? `Atribuído a ${p.web_rtc_user.name}` : 'Sem usuário vinculado' }}
                    <template v-if="p.site"> · {{ p.site.name }}</template>
                  </span>
                </span>
              </label>
            </li>
          </ul>

          <button
            v-if="telephony?.phone"
            type="button"
            class="text-xs font-medium text-brand hover:underline"
            @click="deleteMode = 'assigned'"
          >
            Voltar ao ramal atribuído
          </button>
        </template>

        <p class="text-xs text-red-700 font-medium">
          A exclusão é permanente e remove também a estação vinculada.
        </p>
      </div>
    </ConfirmDialog>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import LoadingSpinner from './LoadingSpinner.vue'
import ConfirmDialog from './ConfirmDialog.vue'
import { getUserTelephony, searchPhones, deletePhone } from '../api/genesys'
import { useToast } from '../composables/useToast'

const props = defineProps({
  userId: {
    type: String,
    required: true,
  },
})

const { addToast } = useToast()

const loading = ref(false)
const telephony = ref(null)
const error = ref('')

async function fetchTelephony() {
  if (!props.userId) return
  loading.value = true
  error.value = ''
  try {
    telephony.value = await getUserTelephony(props.userId)
  } catch (err) {
    error.value = err.message || 'Erro ao carregar dados de telefonia'
    telephony.value = null
  } finally {
    loading.value = false
  }
}

watch(
  () => props.userId,
  (newId) => {
    if (newId) {
      fetchTelephony()
    } else {
      telephony.value = null
      error.value = ''
    }
  },
  { immediate: true },
)

// Permite à Consulta recarregar o painel após ações que mexem no ramal.
defineExpose({ refresh: fetchTelephony })

// ── Exclusão de ramal ──
// Com ramal atribuído, oferece excluí-lo direto; sem ramal (ou "Excluir outro
// ramal"), solicita o nome e o operador escolhe entre os resultados da busca.
const showDeleteDialog = ref(false)
const deleteMode = ref('assigned') // 'assigned' | 'search'
const deleteLoading = ref(false)
const phoneQuery = ref('')
const phoneResults = ref([])
const selectedPhone = ref(null)
const searchLoading = ref(false)
const searchError = ref('')
const searched = ref(false)

function openDeleteDialog() {
  deleteMode.value = telephony.value?.phone?.id ? 'assigned' : 'search'
  phoneQuery.value = ''
  phoneResults.value = []
  selectedPhone.value = null
  searchError.value = ''
  searched.value = false
  showDeleteDialog.value = true
}

function closeDeleteDialog() {
  if (deleteLoading.value) return
  showDeleteDialog.value = false
}

async function runPhoneSearch() {
  const q = phoneQuery.value.trim()
  if (q.length < 2) return
  searchLoading.value = true
  searchError.value = ''
  selectedPhone.value = null
  try {
    const data = await searchPhones(q)
    phoneResults.value = data.results || []
  } catch (err) {
    searchError.value = err.message || 'Erro ao buscar ramais'
    phoneResults.value = []
  } finally {
    searched.value = true
    searchLoading.value = false
  }
}

async function handleDeletePhone() {
  const target = deleteMode.value === 'assigned' ? telephony.value?.phone : selectedPhone.value
  if (!target?.id) {
    addToast('Selecione o ramal que deve ser excluído.', 'error')
    return
  }
  deleteLoading.value = true
  try {
    await deletePhone(target.id)
    addToast(`Ramal ${target.name || target.id} excluído com sucesso.`, 'success')
    showDeleteDialog.value = false
    await fetchTelephony()
  } catch (err) {
    addToast(err.message || 'Erro ao excluir ramal', 'error')
  } finally {
    deleteLoading.value = false
  }
}
</script>
