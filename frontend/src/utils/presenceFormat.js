/**
 * Formatação e cores de presença (paridade Colab / ANALYTICS-PRESENCA-CONSULTA.md).
 */

export const PRESENCE_COLORS = {
  AVAILABLE: '#2ecc71',
  ON_QUEUE: '#22d3ee',
  OFFLINE: '#4b5563',
  BUSY: '#e74c3c',
  AWAY: '#f1c40f',
  BREAK: '#e67e22',
}

export const PRESENCE_ORDER = ['AVAILABLE', 'ON_QUEUE', 'BUSY', 'AWAY', 'BREAK', 'OFFLINE']

/** Largura mínima visual de um segmento na timeline (px). */
export const TIMELINE_MIN_SEGMENT_PX = 4

const FALLBACK_COLOR = '#6b7280'
const DAY_MINUTES = 24 * 60

/** Cor do status; desconhecido → cinza neutro. */
export function presenceColor(systemPresence) {
  if (!systemPresence) return FALLBACK_COLOR
  return PRESENCE_COLORS[systemPresence] || FALLBACK_COLOR
}

/** Minutos → "2h 20m" / "35m" / "0m". */
export function formatMinutes(minutes) {
  const total = Number(minutes)
  if (!Number.isFinite(total) || total <= 0) return '0m'
  const rounded = Math.round(total)
  const h = Math.floor(rounded / 60)
  const m = rounded % 60
  if (h <= 0) return `${m}m`
  if (m <= 0) return `${h}h`
  return `${h}h ${m}m`
}

/** Data civil de hoje em America/Sao_Paulo (YYYY-MM-DD). */
export function todayBrDate() {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Sao_Paulo',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date())
}

/**
 * Extrai HH:mm de um ISO com offset (ex. 2026-08-05T09:00:12-03:00).
 */
export function timeLabelFromOffsetIso(iso) {
  if (!iso || typeof iso !== 'string') return '—'
  const m = iso.match(/T(\d{2}):(\d{2})/)
  return m ? `${m[1]}:${m[2]}` : '—'
}

/** Minutos desde 00:00 a partir de ISO (só hora local do string). */
export function minutesFromMidnight(iso) {
  if (!iso) return 0
  const m = iso.match(/T(\d{2}):(\d{2})(?::(\d{2}))?/)
  if (!m) return 0
  const hh = Number(m[1])
  const mm = Number(m[2])
  const ss = Number(m[3] || 0)
  return hh * 60 + mm + ss / 60
}

/**
 * Posição percentual do instante no dia civil BR (00:00–24:00).
 * Aceita ISO com offset ou UTC Z.
 */
export function dayPercent(iso) {
  return Math.min(100, Math.max(0, (minutesFromMidnight(iso) / DAY_MINUTES) * 100))
}

/**
 * Minutos desde 00:00 BR a partir de um instante (Date ou ISO UTC/offset).
 */
export function minutesNowBr(instant = new Date()) {
  const d = instant instanceof Date ? instant : new Date(instant)
  if (Number.isNaN(d.getTime())) return null
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'America/Sao_Paulo',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(d)
  const get = (type) => Number(parts.find((p) => p.type === type)?.value || 0)
  return get('hour') * 60 + get('minute') + get('second') / 60
}

/**
 * “Agora” da consulta em minutos desde 00:00 BR.
 * Preferência: end do segmento aberto → queried_at → max end → relógio local BR.
 */
export function consultationNowMinutes(result) {
  const segs = result?.segments || []
  const open = segs.find((s) => s.is_open)
  if (open?.end) return minutesFromMidnight(open.end)

  if (result?.queried_at) {
    const fromQuery = minutesNowBr(result.queried_at)
    if (fromQuery != null) return fromQuery
  }

  let maxEnd = 0
  for (const seg of segs) {
    let e = minutesFromMidnight(seg.end)
    const s = minutesFromMidnight(seg.start)
    if (e < s) e = DAY_MINUTES
    maxEnd = Math.max(maxEnd, e)
  }
  if (maxEnd > 0) return maxEnd

  return minutesNowBr(new Date()) ?? DAY_MINUTES
}

/**
 * Escala da timeline (minutos desde 00:00).
 *
 * - Dia de hoje: 00:00 → agora da consulta (sem padding além do “até agora”).
 * - Dia passado: 00:00 → 24:00.
 */
export function activityWindow(segments, {
  isToday = false,
  nowMinutes = null,
} = {}) {
  if (isToday) {
    const end = Math.min(
      DAY_MINUTES,
      Math.max(1, nowMinutes ?? consultationNowMinutes({ segments })),
    )
    return { startMin: 0, endMin: end, zoomed: end < DAY_MINUTES }
  }
  return { startMin: 0, endMin: DAY_MINUTES, zoomed: false }
}

/** Minutos → rótulo HH:mm. */
export function formatClockMinutes(totalMinutes) {
  const clamped = Math.min(DAY_MINUTES, Math.max(0, Math.round(totalMinutes)))
  if (clamped >= DAY_MINUTES) return '24:00'
  const h = Math.floor(clamped / 60)
  const m = clamped % 60
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
}

/**
 * Posição/largura percentual de um segmento dentro de uma janela [startMin, endMin].
 * Aplica largura mínima em % equivalente a `minPx` numa barra de `barWidthPx`.
 */
export function segmentLayout(seg, window, { barWidthPx = 600, minPx = TIMELINE_MIN_SEGMENT_PX } = {}) {
  const span = Math.max(1, window.endMin - window.startMin)
  let start = minutesFromMidnight(seg.start)
  let end = minutesFromMidnight(seg.end)
  if (end < start) end = DAY_MINUTES

  start = Math.max(window.startMin, Math.min(window.endMin, start))
  end = Math.max(window.startMin, Math.min(window.endMin, end))

  let left = ((start - window.startMin) / span) * 100
  let width = ((end - start) / span) * 100

  const minPct = barWidthPx > 0 ? (minPx / barWidthPx) * 100 : 0
  if (width < minPct && width >= 0) {
    width = minPct
    if (left + width > 100) left = Math.max(0, 100 - width)
  }

  return { left, width: Math.max(0, width) }
}
