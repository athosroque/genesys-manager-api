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

/** Solicita magic link por e-mail. Não estabelece sessão — isso ocorre no POST /auth/verify. */
export const requestLoginLink = (email) =>
    request('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email })
    })

/** Consome o magic link (POST seta o cookie de sessão). Chamado automaticamente ao abrir ?token=. */
export const confirmMagicLink = (token) =>
    request('/auth/verify', {
        method: 'POST',
        body: JSON.stringify({ token })
    })

export const logout = () => request('/auth/logout', { method: 'POST' })

export const getMe = () => request('/auth/me')

// Gestão de usuários locais — somente admin (backend valida via role)
export const listLocalUsers = () => request('/auth/users')

export const createLocalUser = ({ email, full_name, role = 'user', username }) =>
    request('/auth/users', {
        method: 'POST',
        body: JSON.stringify({
            email,
            full_name,
            role,
            ...(username ? { username } : {}),
        }),
    })

export const deleteLocalUser = (username) =>
    request(`/auth/users/${encodeURIComponent(username)}`, {
        method: 'DELETE',
    })
