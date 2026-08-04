/**
 * Helpers para <input type="datetime-local"> no fuso do browser.
 * Valores naive (YYYY-MM-DDTHH:mm) ↔ Instant UTC (ISO) sem ambiguidade.
 */

const pad = (n) => String(n).padStart(2, '0')

/** Date → valor de datetime-local no fuso local do browser. */
export function toDatetimeLocalValue(date = new Date()) {
  const d = date instanceof Date ? date : new Date(date)
  if (Number.isNaN(d.getTime())) return ''
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}`
  )
}

/**
 * datetime-local (naive, fuso local) → ISO UTC para a API.
 * Não usa `new Date("YYYY-MM-DDTHH:mm")` (histórico ES5/UTC ambíguo).
 */
export function datetimeLocalToIso(value) {
  if (!value || typeof value !== 'string') {
    throw new Error('Data local inválida')
  }
  const [datePart, timePart = '00:00'] = value.split('T')
  const [y, m, day] = datePart.split('-').map(Number)
  const timeBits = timePart.split(':').map(Number)
  const hh = timeBits[0] || 0
  const mm = timeBits[1] || 0
  const ss = timeBits[2] || 0
  if (![y, m, day].every((n) => Number.isFinite(n))) {
    throw new Error(`Data local inválida: ${value}`)
  }
  return new Date(y, m - 1, day, hh, mm, ss).toISOString()
}

/**
 * Presets de período no fuso local:
 * - 24h: janela rolante das últimas 24 horas
 * - 7d / 30d: últimos N dias de calendário (meia-noite local de hoje-(N-1) → agora),
 *   legível e ≤ N×24h (respeita o teto de 30 dias da API)
 */
export function presetPeriodRange(presetId) {
  const end = new Date()
  if (presetId === '24h') {
    const start = new Date(end.getTime() - 24 * 3600 * 1000)
    return { start: toDatetimeLocalValue(start), end: toDatetimeLocalValue(end) }
  }
  const days = presetId === '30d' ? 30 : 7
  const start = new Date(
    end.getFullYear(),
    end.getMonth(),
    end.getDate() - (days - 1),
    0,
    0,
    0,
    0,
  )
  return { start: toDatetimeLocalValue(start), end: toDatetimeLocalValue(end) }
}
