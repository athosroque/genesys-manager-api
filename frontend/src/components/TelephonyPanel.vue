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
          @click="copyDiagnostic"
          class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-600 bg-gray-50 border border-gray-200 rounded-xl hover:bg-gray-100 hover:text-ink transition-colors"
          title="Copiar resumo para atendimento"
        >
          <svg class="w-3.5 h-3.5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
          </svg>
          Copiar Laudo
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
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import LoadingSpinner from './LoadingSpinner.vue'
import { getUserTelephony } from '../api/genesys'
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

async function copyDiagnostic() {
  if (!telephony.value) return

  const t = telephony.value
  const statusLine = t.is_healthy
    ? '🟢 CENÁRIO 1: Backend Íntegro (Problema Local na Máquina)'
    : '🔴 CENÁRIO 2: Inconsistência no Genesys Cloud'

  const stationName = t.station?.name || 'Nenhuma estação atribuída'
  const stationStatus = t.station?.status || 'Desconectada'
  const phoneName = t.phone?.name || 'Nenhum telefone'
  const phoneSite = t.phone?.site?.name || 'Sem Site'

  const lines = [
    `[DIAGNÓSTICO DE TELEFONIA / RAMAL - GENESYS CLOUD]`,
    `Usuário: ${t.user_name || '—'} (${t.user_id})`,
    `Diagnóstico: ${statusLine}`,
    `----------------------------------------------------`,
    `1. Estação: ${stationName} (${t.station?.type || '—'})`,
    `2. Conexão: ${stationStatus}`,
    `3. Telefone Base: ${phoneName} | Estado: ${t.phone?.state || '—'} | Site: ${phoneSite}`,
    `----------------------------------------------------`,
    `Parecer Técnico:`,
    `${t.diagnosis}`,
  ]

  if (t.issues && t.issues.length > 0) {
    lines.push(`\nInconsistências Identificadas:`)
    t.issues.forEach((issue) => lines.push(`- ${issue}`))
  }

  if (t.recommendations && t.recommendations.length > 0) {
    lines.push(`\nRecomendações:`)
    t.recommendations.forEach((rec, i) => lines.push(`${i + 1}. ${rec}`))
  }

  const fullText = lines.join('\n')

  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(fullText)
    } else {
      const textarea = document.createElement('textarea')
      textarea.value = fullText
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
    }
    addToast('Laudo de telefonia copiado para a área de transferência!', 'success')
  } catch (err) {
    console.error('Falha ao copiar:', err)
    addToast('Não foi possível copiar automaticamente.', 'error')
  }
}
</script>
