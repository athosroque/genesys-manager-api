const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// Wrapper único de fetch para o backend. Envia sempre o cookie HttpOnly
// (credentials: 'include'), trata 502 como falha de auth com a Genesys e
// extrai `detail`/`message` do corpo em erros.
export async function request(path, options = {}) {
    let response

    try {
        response = await fetch(`${BASE}${path}`, {
            credentials: 'include', // Necessário para cookies HttpOnly
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        })
    } catch (err) {
        // Abort via AbortController (cancelamento do usuário ou troca de busca) —
        // preserva a identidade para o caller tratar sem toast de erro.
        if (err?.name === 'AbortError') {
            throw err
        }
        if (/timeout/i.test(err?.message || '')) {
            throw new Error(
                'A busca demorou demais e foi cancelada (timeout). ' +
                'Na busca profunda, tente um intervalo menor (ex.: 7 dias) ou desative o toggle.'
            )
        }
        throw new Error('Sem conexão com o backend. Verifique se o servidor está ativo.')
    }

    if (response.status === 502) {
        throw new Error('Falha de autenticação com Genesys. Verifique as credenciais.')
    }

    if (response.status === 504 || response.status === 408) {
        throw new Error(
            'A busca demorou demais e o servidor encerrou a conexão (timeout). ' +
            'Na busca profunda, tente um intervalo menor (ex.: 7 dias) ou desative o toggle.'
        )
    }

    if (!response.ok) {
        let detail = `[HTTP ${response.status}]`
        try {
            const body = await response.json()
            detail += ' ' + (body.detail || body.message || JSON.stringify(body))
        } catch {
            detail += ' ' + response.statusText
        }
        throw new Error(detail)
    }

    return response.json()
}

export async function streamRequest(path, options = {}) {
    const { onEvent, ...fetchOptions } = options
    let response

    try {
        response = await fetch(`${BASE}${path}`, {
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                ...fetchOptions.headers,
            },
            ...fetchOptions,
        })
    } catch (err) {
        if (err?.name === 'AbortError') {
            throw err
        }
        if (/timeout/i.test(err?.message || '')) {
            throw new Error('A busca demorou demais e foi cancelada (timeout).')
        }
        throw new Error('Sem conexão com o backend. Verifique se o servidor está ativo.')
    }

    if (response.status === 502) {
        throw new Error('Falha de autenticação com Genesys. Verifique as credenciais.')
    }
    if (response.status === 504 || response.status === 408) {
        throw new Error('A busca demorou demais e o servidor encerrou a conexão (timeout).')
    }
    if (!response.ok) {
        let detail = `[HTTP ${response.status}]`
        try {
            const body = await response.json()
            detail += ' ' + (body.detail || body.message || JSON.stringify(body))
        } catch {
            detail += ' ' + response.statusText
        }
        throw new Error(detail)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''
    let finalResult = null

    try {
        while (true) {
            const { value, done } = await reader.read()
            if (done) break
            buffer += decoder.decode(value, { stream: true })
            const lines = buffer.split('\n')
            buffer = lines.pop()

            for (const line of lines) {
                const trimmed = line.trim()
                if (!trimmed.startsWith('data:')) continue
                const jsonStr = trimmed.slice(5).trim()
                if (!jsonStr) continue
                try {
                    const event = JSON.parse(jsonStr)
                    if (event.type === 'error') {
                        throw new Error(event.message || 'Erro durante a varredura.')
                    }
                    if (event.type === 'done') {
                        finalResult = event
                    }
                    if (onEvent) {
                        onEvent(event)
                    }
                } catch (jsonErr) {
                    if (jsonErr.message && !jsonErr.message.includes('JSON')) {
                        throw jsonErr
                    }
                }
            }
        }
    } catch (streamErr) {
        if (streamErr?.name === 'AbortError') {
            throw streamErr
        }
        const msg = (streamErr?.message || '').toLowerCase()
        if (msg.includes('quic') || msg.includes('network') || msg.includes('failed to fetch')) {
            throw new Error(
                'A conexão com o servidor foi interrompida durante a transmissão dos dados. ' +
                'Caso esteja usando HTTP/3 (QUIC), instabilidades de rede ou timeouts de proxy podem derrubar a conexão.'
            )
        }
        throw streamErr
    }

    if (!finalResult) {
        throw new Error('A transmissão de eventos foi encerrada antes da conclusão da auditoria.')
    }

    return finalResult
}
