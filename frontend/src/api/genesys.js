import { request } from './http'

export const searchUser = (q) =>
    request(`/users/search?q=${encodeURIComponent(q)}`)

export const autocompleteUsers = (q) =>
    request(`/users/autocomplete?q=${encodeURIComponent(q)}`)

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

// Lookup leve de nome de usuário por UUID (sem expand) — fonte do cache de
// nomes da Trilha de Auditoria.
export const getUserName = (id) => request(`/users/${id}/name`)

// Mapas {id, name} completos de roles, grupos e divisões da org — resolvem os
// chips da auditoria de uma vez (ver useEntityNames.js).
export const listRoles = () => request('/roles')
export const listGroups = () => request('/groups')
export const listDivisions = () => request('/divisions')
