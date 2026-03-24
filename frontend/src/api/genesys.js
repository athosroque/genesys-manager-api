const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

async function request(path, options = {}) {
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
    } catch {
        throw new Error('Sem conexão com o backend. Verifique se o servidor está ativo.')
    }

    if (response.status === 502) {
        throw new Error('Falha de autenticação com Genesys. Verifique as credenciais.')
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

export const searchUser = (q) =>
    request(`/users/search?q=${encodeURIComponent(q)}`)

export const getUserQueues = (userId) =>
    request(`/users/${userId}/queues`)

export const reactivateUser = (userId, version) =>
    request(`/users/${userId}/reactivate`, {
        method: 'POST',
        body: JSON.stringify({ version })
    })

export const removeFromAllQueues = (userId) =>
    request(`/queues/user/${userId}/all`, { method: 'DELETE' })

export const removeFromQueue = (queueId, userId) =>
    request(`/queues/${queueId}/member/${userId}`, { method: 'DELETE' })


export const removeFromGroup = (groupId, userId) =>
    request(`/groups/${groupId}/members/${userId}`, { method: 'DELETE' })

export const runMigration = (userId, op, groupId = null) =>
    request('/migration/run', {
        method: 'POST',
        body: JSON.stringify({ user_id: userId, op, group_id: groupId })
    })

export const getGroupsConfig = () => request('/config/groups')
