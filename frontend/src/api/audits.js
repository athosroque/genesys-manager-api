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
