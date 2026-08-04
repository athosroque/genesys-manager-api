import { request } from './http'

export const getAuditServices = () => request('/audits/services')

export const searchAudits = (body) =>
    request('/audits/search', {
        method: 'POST',
        body: JSON.stringify(body)
    })

export const getAuditResults = (transactionId, cursor, pageSize = 50) =>
    request(
        `/audits/search/${transactionId}/results?cursor=${encodeURIComponent(cursor)}&page_size=${pageSize}`
    )

export const deepSearchAudits = (body) =>
    request('/audits/search/deep', {
        method: 'POST',
        body: JSON.stringify(body)
    })

/**
 * Alterações focadas em um usuário no intervalo.
 * Body: { user, interval_start, interval_end, deep_categories?: string[], deep_search?: bool }
 * deep_categories: 'queue' | 'role' | 'group' (default []). Compat: deep_search true = as 3.
 */
export const getUserChanges = (body, options = {}) =>
    request('/audits/user-changes', {
        method: 'POST',
        body: JSON.stringify(body),
        ...options,
    })
