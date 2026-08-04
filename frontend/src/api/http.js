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
