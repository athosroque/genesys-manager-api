const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

/**
 * Função utilitária para chamadas de autenticação.
 * 'credentials: include' é obrigatório para lidar com cookies HttpOnly.
 */
async function request(endpoint, options = {}) {
    const url = `${BASE_URL}${endpoint}`
    const response = await fetch(url, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
        credentials: 'include', // Permite envio/recebimento de cookies
    })

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        const error = new Error(errorData.detail || 'Falha na autenticação')
        error.status = response.status
        throw error
    }

    return response.json()
}

export const login = (username, password) =>
    request('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password })
    })

export const logout = () => request('/auth/logout', { method: 'POST' })

export const getMe = () => request('/auth/me')
