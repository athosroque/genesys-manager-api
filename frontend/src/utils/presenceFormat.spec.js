import { describe, expect, it } from 'vitest'
import {
  activityWindow,
  consultationNowMinutes,
  dayPercent,
  formatClockMinutes,
  formatMinutes,
  presenceColor,
  segmentLayout,
  timeLabelFromOffsetIso,
} from './presenceFormat'

describe('presenceFormat', () => {
  it('formatMinutes cobre horas e minutos', () => {
    expect(formatMinutes(0)).toBe('0m')
    expect(formatMinutes(35)).toBe('35m')
    expect(formatMinutes(60)).toBe('1h')
    expect(formatMinutes(140.27)).toBe('2h 20m')
  })

  it('presenceColor diferencia OFFLINE e ON_QUEUE', () => {
    expect(presenceColor('AVAILABLE')).toBe('#2ecc71')
    expect(presenceColor('BUSY')).toBe('#e74c3c')
    expect(presenceColor('OFFLINE')).toBe('#4b5563')
    expect(presenceColor('ON_QUEUE')).toBe('#22d3ee')
    expect(presenceColor('CUSTOM_X')).toBe('#6b7280')
  })

  it('timeLabelFromOffsetIso extrai HH:mm', () => {
    expect(timeLabelFromOffsetIso('2026-08-05T09:00:12-03:00')).toBe('09:00')
    expect(timeLabelFromOffsetIso('2026-08-05T14:20:28-03:00')).toBe('14:20')
  })

  it('dayPercent posiciona no dia 00:00–24:00', () => {
    expect(dayPercent('2026-08-05T00:00:00-03:00')).toBe(0)
    expect(dayPercent('2026-08-05T12:00:00-03:00')).toBe(50)
    expect(dayPercent('2026-08-05T18:00:00-03:00')).toBe(75)
  })

  it('activityWindow no dia de hoje termina em now (sem padding)', () => {
    const segs = [
      {
        start: '2026-08-05T10:03:00-03:00',
        end: '2026-08-05T10:40:00-03:00',
        is_open: true,
      },
    ]
    const nowMinutes = consultationNowMinutes({ segments: segs })
    const w = activityWindow(segs, { isToday: true, nowMinutes })
    expect(w.startMin).toBe(0)
    expect(w.endMin).toBe(10 * 60 + 40)
    expect(w.zoomed).toBe(true)
    expect(formatClockMinutes(w.endMin)).toBe('10:40')
  })

  it('activityWindow em dia passado vai até 24:00', () => {
    const segs = [
      { start: '2026-08-04T10:00:00-03:00', end: '2026-08-04T11:00:00-03:00' },
    ]
    const w = activityWindow(segs, { isToday: false })
    expect(w.startMin).toBe(0)
    expect(w.endMin).toBe(24 * 60)
    expect(w.zoomed).toBe(false)
  })

  it('consultationNowMinutes prioriza segmento aberto', () => {
    const minutes = consultationNowMinutes({
      queried_at: '2026-08-05T14:11:00Z',
      segments: [
        {
          start: '2026-08-05T10:03:00-03:00',
          end: '2026-08-05T10:40:00-03:00',
          is_open: true,
        },
      ],
    })
    expect(minutes).toBe(10 * 60 + 40)
  })

  it('segmentLayout aplica largura mínima em px', () => {
    const window = { startMin: 0, endMin: 10 * 60 + 40, zoomed: true }
    const tiny = {
      start: '2026-08-05T10:00:00-03:00',
      end: '2026-08-05T10:00:30-03:00',
    }
    const layout = segmentLayout(tiny, window, { barWidthPx: 400, minPx: 4 })
    expect(layout.width).toBeGreaterThanOrEqual((4 / 400) * 100)
  })

  it('formatClockMinutes formata bordas do dia', () => {
    expect(formatClockMinutes(0)).toBe('00:00')
    expect(formatClockMinutes(90)).toBe('01:30')
    expect(formatClockMinutes(24 * 60)).toBe('24:00')
  })
})
