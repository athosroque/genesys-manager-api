import { reactive } from 'vue'
import { getUserName, listRoles, listGroups, listDivisions } from '../api/genesys'

// Caches globais UUID → nome, compartilhados entre telas (module scope): o
// mesmo UUID nunca é buscado duas vezes na sessão. Dois modos:
//
//  - Cache per-UUID (usuário): resolve sob demanda, um lookup por UUID, com
//    pool de concorrência e teto de chamadas. Alimentado de graça por prime()
//    (autores via expand=user, pessoa buscada). Não dá para listar todos os
//    usuários da org, então continua per-UUID.
//  - Cache bulk (role/group): busca o mapa {id, name} inteiro numa chamada
//    (poucas dezenas de roles / conjunto limitado de grupos) via ensureBulk(),
//    uma vez por sessão, e todos os chips daquele tipo resolvem de graça.
//
// Em ambos, `null` no cache = já tentado e não resolvido → não tentar de novo.

function createPerUuidCache(fetcher, { maxConcurrent = 3, maxLookups = 60 } = {}) {
  const names = reactive(new Map())
  const pending = new Set()
  const queue = []
  let active = 0
  let lookups = 0

  function prime(id, name) {
    if (id && name && !names.get(id)) names.set(id, name)
  }

  function resolveMany(ids = []) {
    for (const id of ids) {
      if (!id || names.has(id) || pending.has(id)) continue
      if (lookups >= maxLookups) return
      lookups++
      pending.add(id)
      queue.push(id)
    }
    pump()
  }

  function pump() {
    while (active < maxConcurrent && queue.length) {
      const id = queue.shift()
      active++
      fetcher(id)
        .then((data) => names.set(id, data?.found ? data.name || null : null))
        .catch(() => names.set(id, null))
        .finally(() => {
          pending.delete(id)
          active--
          pump()
        })
    }
  }

  return {
    prime,
    resolveMany,
    nameOf: (id) => names.get(id) || null,
  }
}

function createBulkCache(loader) {
  const names = reactive(new Map())
  let loaded = false
  let inFlight = null

  // Busca o mapa inteiro uma única vez por sessão. Chamadas concorrentes
  // compartilham a mesma promessa; erro/aviso marca `loaded` para não
  // retentar em loop (chips ficam como UUID abreviado).
  function ensureBulk() {
    if (loaded || inFlight) return inFlight || Promise.resolve()
    inFlight = loader()
      .then((items) => {
        for (const it of items || []) {
          if (it?.id && it?.name) names.set(it.id, it.name)
        }
      })
      .catch(() => {})
      .finally(() => {
        loaded = true
        inFlight = null
      })
    return inFlight
  }

  return {
    ensureBulk,
    nameOf: (id) => names.get(id) || null,
  }
}

const userCache = createPerUuidCache(getUserName, { maxConcurrent: 3, maxLookups: 60 })
const roleCache = createBulkCache(async () => (await listRoles()).roles)
const groupCache = createBulkCache(async () => (await listGroups()).groups)
const divisionCache = createBulkCache(async () => (await listDivisions()).divisions)

export function useUserNames() {
  return userCache
}

export function useRoleNames() {
  return roleCache
}

export function useGroupNames() {
  return groupCache
}

export function useDivisionNames() {
  return divisionCache
}
