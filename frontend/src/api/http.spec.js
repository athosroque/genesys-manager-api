import { describe, it, expect, vi, beforeEach } from 'vitest'
import { streamRequest } from './http'

describe('streamRequest', () => {
    beforeEach(() => {
        vi.restoreAllMocks()
    })

    function createMockStream(chunks) {
        const encoder = new TextEncoder()
        let idx = 0
        return new ReadableStream({
            pull(controller) {
                if (idx < chunks.length) {
                    controller.enqueue(encoder.encode(chunks[idx]))
                    idx++
                } else {
                    controller.close()
                }
            }
        })
    }

    it('processes SSE events and silently ignores : keep-alive comments', async () => {
        const chunks = [
            'data: {"type": "init", "total_chunks": 1}\n\n',
            ': keep-alive\n\n',
            ': ping\n\n',
            'data: {"type": "done", "changes": [{"id": "c1"}]}\n\n',
        ]

        vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
            ok: true,
            status: 200,
            body: createMockStream(chunks),
        }))

        const events = []
        const result = await streamRequest('/test/stream', {
            onEvent: (ev) => events.push(ev),
        })

        expect(events).toEqual([
            { type: 'init', total_chunks: 1 },
            { type: 'done', changes: [{ id: 'c1' }] },
        ])
        expect(result).toEqual({ type: 'done', changes: [{ id: 'c1' }] })
    })

    it('throws descriptive error if stream ends without done event', async () => {
        const chunks = [
            'data: {"type": "init", "total_chunks": 1}\n\n',
            ': keep-alive\n\n',
        ]

        vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
            ok: true,
            status: 200,
            body: createMockStream(chunks),
        }))

        await expect(
            streamRequest('/test/stream', {})
        ).rejects.toThrow(/encerrada antes da conclusão/i)
    })

    it('throws descriptive error if stream is aborted by QUIC / network error', async () => {
        const mockStream = new ReadableStream({
            pull(controller) {
                controller.error(new TypeError('net::ERR_QUIC_PROTOCOL_ERROR'))
            }
        })

        vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
            ok: true,
            status: 200,
            body: mockStream,
        }))

        await expect(
            streamRequest('/test/stream', {})
        ).rejects.toThrow(/interrompida durante a transmissão dos dados/i)
    })
})
