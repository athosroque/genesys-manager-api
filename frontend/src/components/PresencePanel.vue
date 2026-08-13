<template>
  <div class="card overflow-hidden">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 px-5 py-5">
      <div class="flex items-start gap-3">
        <div class="p-2 rounded-xl bg-brand-soft">
          <svg class="w-4 h-4 text-brand" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 2m6-2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <div>
          <p class="text-sm font-semibold text-ink">Status na plataforma</p>
          <p class="text-xs text-gray-400 mt-0.5">Presença do dia (Genesys Analytics · America/Sao_Paulo)</p>
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <label class="sr-only" for="presence-date">Data</label>
        <input
          id="presence-date"
          v-model="session.selectedDate"
          type="date"
          :max="maxDate"
          class="input py-2 max-w-[11rem] rounded-full"
        />
        <button
          type="button"
          :disabled="loading || !session.selectedDate"
          @click="fetchPresence"
          class="btn-primary"
        >
          {{ loading ? 'Consultando…' : 'Consultar status' }}
        </button>
      </div>
    </div>

    <div class="p-5 space-y-5">
      <!-- Loading -->
      <div v-if="loading" class="flex items-center justify-center gap-3 py-10 text-brand">
        <div class="w-5 h-5 [&_svg]:w-5 [&_svg]:h-5">
          <LoadingSpinner />
        </div>
        <span class="text-sm text-gray-500">Carregando presença…</span>
      </div>

      <!-- Erro -->
      <div
        v-else-if="session.error"
        class="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700"
        data-testid="presence-error"
      >
        <p class="font-semibold text-red-800">Não foi possível consultar o status</p>
        <p class="mt-1 font-mono text-xs text-red-600 break-all">{{ session.error }}</p>
      </div>

      <!-- Ainda não consultou -->
      <div v-else-if="!session.result" class="py-6 text-center text-sm text-gray-400">
        Escolha a data e clique em <span class="text-brand font-medium">Consultar status</span> para ver a presença do dia.
      </div>

      <!-- Vazio -->
      <div
        v-else-if="session.result.empty"
        class="rounded-xl border border-gray-200 bg-gray-50 p-4 text-sm text-gray-500"
        data-testid="presence-empty"
      >
        Nenhum registro de presença neste dia. Pode ser ausência de atividade, escopo/divisão da integração
        (FGAC) ou histórico ainda não disponível na Analytics.
      </div>

      <!-- Resultado -->
      <template v-else>
        <!-- Cards de totais -->
        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <div
            v-for="card in statusCards"
            :key="card.key"
            class="rounded-2xl border bg-white px-3 py-3"
            :style="{ borderColor: card.color + '66' }"
          >
            <div class="flex items-center gap-2 mb-1.5">
              <span class="w-2.5 h-2.5 rounded-full shrink-0" :style="{ backgroundColor: card.color }" />
              <span class="text-[10px] font-bold uppercase tracking-wider text-gray-400">{{ card.key }}</span>
            </div>
            <p class="text-lg font-semibold text-ink tabular-nums">{{ formatMinutes(card.minutes) }}</p>
          </div>
        </div>

        <!-- Timeline -->
        <div>
          <div class="flex items-center justify-between mb-2 gap-2 flex-wrap">
            <p class="text-xs font-bold text-gray-400 uppercase tracking-wider">
              Timeline
              <span class="font-mono normal-case tracking-normal text-gray-400">
                ({{ timelineLabels[0] }} → {{ timelineLabels[timelineLabels.length - 1] }})
              </span>
              <span
                v-if="timelineWindow.zoomed"
                class="ml-1.5 text-[10px] font-medium normal-case tracking-normal text-brand/80"
              >até o momento da consulta</span>
            </p>
            <p v-if="session.result.open_segment" class="text-[10px] text-brand font-medium">
              Segmento aberto = status atual (até agora)
            </p>
          </div>
          <div
            ref="timelineEl"
            class="relative h-8 rounded-xl bg-gray-100 overflow-visible"
            data-testid="presence-timeline"
            @mouseleave="hideTooltip"
          >
            <div class="absolute inset-0 rounded-xl overflow-hidden bg-gray-100">
              <div
                v-for="(seg, i) in timelineSegments"
                :key="i"
                class="absolute top-0 bottom-0 presence-seg cursor-default"
                :class="{ 'ring-1 ring-ink/20': seg.is_open }"
                :style="{
                  left: seg.left + '%',
                  width: seg.width + '%',
                  backgroundColor: presenceColor(seg.system_presence),
                  opacity: seg.is_open ? 0.95 : 0.9,
                  zIndex: seg.width < 1 ? 2 : 1,
                }"
                @mouseenter="showTooltip($event, seg)"
                @mousemove="moveTooltip($event)"
              />
            </div>

            <!-- Tooltip customizado -->
            <div
              v-if="tooltip.visible"
              class="pointer-events-none absolute z-20 px-2.5 py-1.5 rounded-lg bg-ink border border-ink shadow-lg text-[11px] text-white whitespace-nowrap"
              :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px', transform: 'translate(-50%, calc(-100% - 8px))' }"
              data-testid="presence-tooltip"
            >
              <div class="flex items-center gap-1.5 font-semibold">
                <span
                  class="w-2 h-2 rounded-full shrink-0"
                  :style="{ backgroundColor: presenceColor(tooltip.seg.system_presence) }"
                />
                {{ tooltip.seg.system_presence }}
              </div>
              <div class="mt-0.5 font-mono text-gray-200">
                {{ timeLabelFromOffsetIso(tooltip.seg.start) }}–{{ timeLabelFromOffsetIso(tooltip.seg.end) }}
                <span v-if="tooltip.seg.is_open" class="text-brand-soft font-sans"> · até agora</span>
              </div>
              <div class="text-gray-300">{{ formatMinutes(tooltip.seg.duration_minutes) }}</div>
            </div>
          </div>
          <div class="flex justify-between mt-1 text-[10px] text-gray-400 font-mono">
            <span v-for="(label, i) in timelineLabels" :key="i">{{ label }}</span>
          </div>
        </div>

        <!-- Lista de segmentos -->
        <div>
          <button
            type="button"
            class="text-xs text-brand hover:text-brand-hover transition-colors flex items-center gap-1.5 font-medium"
            @click="session.listOpen = !session.listOpen"
          >
            <svg
              class="w-3.5 h-3.5 transition-transform"
              :class="{ 'rotate-90': session.listOpen }"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
            {{ session.listOpen ? 'Ocultar' : 'Ver' }} lista de segmentos ({{ session.result.segments.length }})
          </button>

          <div v-if="session.listOpen" class="mt-3 border border-gray-100 rounded-xl overflow-hidden">
            <table class="min-w-full divide-y divide-gray-100 text-sm">
              <thead class="bg-gray-50/80">
                <tr>
                  <th class="px-4 py-2 text-left text-xs font-medium text-gray-400">Horário (BR)</th>
                  <th class="px-4 py-2 text-left text-xs font-medium text-gray-400">Status</th>
                  <th class="px-4 py-2 text-right text-xs font-medium text-gray-400">Duração</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-50">
                <tr v-for="(seg, i) in session.result.segments" :key="i" class="hover:bg-peach/40">
                  <td class="px-4 py-2 whitespace-nowrap font-mono text-xs text-gray-500">
                    {{ timeLabelFromOffsetIso(seg.start) }}–{{ timeLabelFromOffsetIso(seg.end) }}
                    <span
                      v-if="seg.is_open"
                      class="ml-1.5 text-[10px] text-brand font-sans font-medium"
                    >até agora</span>
                  </td>
                  <td class="px-4 py-2 whitespace-nowrap">
                    <span class="inline-flex items-center gap-1.5">
                      <span
                        class="w-2 h-2 rounded-full"
                        :style="{ backgroundColor: presenceColor(seg.system_presence) }"
                      />
                      <span class="text-ink text-xs font-medium">{{ seg.system_presence }}</span>
                    </span>
                  </td>
                  <td class="px-4 py-2 whitespace-nowrap text-right text-xs text-gray-600 tabular-nums">
                    {{ formatMinutes(seg.duration_minutes) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import LoadingSpinner from './LoadingSpinner.vue'
import { getUserPresence } from '../api/genesys'
import { useToast } from '../composables/useToast'
import { getPresenceSession } from '../composables/usePresenceSession'
import {
  PRESENCE_ORDER,
  activityWindow,
  consultationNowMinutes,
  formatClockMinutes,
  formatMinutes,
  presenceColor,
  segmentLayout,
  timeLabelFromOffsetIso,
  todayBrDate,
} from '../utils/presenceFormat'

const props = defineProps({
  userId: { type: String, required: true },
})

const { addToast } = useToast()

const maxDate = todayBrDate()
const loading = ref(false)
const timelineEl = ref(null)
const barWidthPx = ref(600)

const tooltip = ref({
  visible: false,
  x: 0,
  y: 0,
  seg: null,
})

const session = computed(() => getPresenceSession(props.userId))

watch(
  () => props.userId,
  () => {
    hideTooltip()
  },
)

function measureBar() {
  if (timelineEl.value) {
    barWidthPx.value = Math.max(120, timelineEl.value.clientWidth || 600)
  }
}

let ro
function attachResizeObserver() {
  ro?.disconnect()
  ro = undefined
  if (typeof ResizeObserver === 'undefined' || !timelineEl.value) return
  ro = new ResizeObserver(measureBar)
  ro.observe(timelineEl.value)
  measureBar()
}

watch(timelineEl, () => attachResizeObserver())
onMounted(() => attachResizeObserver())
onUnmounted(() => {
  ro?.disconnect()
})

const statusCards = computed(() => {
  const totals = session.value?.result?.totals_minutes || {}
  const known = PRESENCE_ORDER.map((key) => ({
    key,
    minutes: totals[key] ?? 0,
    color: presenceColor(key),
  }))
  const extras = Object.keys(totals)
    .filter((k) => !PRESENCE_ORDER.includes(k))
    .map((key) => ({
      key,
      minutes: totals[key] ?? 0,
      color: presenceColor(key),
    }))
  return [...known, ...extras]
})

const timelineWindow = computed(() => {
  const result = session.value?.result
  const segs = result?.segments || []
  const date = result?.date || session.value?.selectedDate
  const isToday = Boolean(date && date === todayBrDate())
  const nowMinutes = isToday ? consultationNowMinutes(result) : null
  return activityWindow(segs, { isToday, nowMinutes })
})

const timelineLabels = computed(() => {
  const w = timelineWindow.value
  const span = w.endMin - w.startMin
  const steps = 4
  const labels = []
  for (let i = 0; i <= steps; i++) {
    labels.push(formatClockMinutes(w.startMin + (span * i) / steps))
  }
  return labels
})

const timelineSegments = computed(() => {
  const segs = session.value?.result?.segments || []
  const window = timelineWindow.value
  return segs.map((seg) => {
    const layout = segmentLayout(seg, window, { barWidthPx: barWidthPx.value })
    return { ...seg, ...layout }
  })
})

function showTooltip(event, seg) {
  const rect = timelineEl.value?.getBoundingClientRect()
  if (!rect) return
  tooltip.value = {
    visible: true,
    x: event.clientX - rect.left,
    y: event.clientY - rect.top,
    seg,
  }
}

function moveTooltip(event) {
  if (!tooltip.value.visible || !timelineEl.value) return
  const rect = timelineEl.value.getBoundingClientRect()
  tooltip.value.x = event.clientX - rect.left
  tooltip.value.y = event.clientY - rect.top
}

function hideTooltip() {
  tooltip.value.visible = false
  tooltip.value.seg = null
}

async function fetchPresence() {
  const s = session.value
  if (!props.userId || !s?.selectedDate) return
  loading.value = true
  s.error = ''
  try {
    s.result = await getUserPresence(props.userId, s.selectedDate)
  } catch (err) {
    s.error = err.message || 'Erro desconhecido'
    s.result = null
    addToast('Erro ao consultar status: ' + s.error, 'error')
  } finally {
    loading.value = false
    requestAnimationFrame(measureBar)
  }
}

defineExpose({
  reset: () => {
    const s = session.value
    if (!s) return
    s.result = null
    s.error = ''
    s.listOpen = false
    s.selectedDate = todayBrDate()
  },
})
</script>
