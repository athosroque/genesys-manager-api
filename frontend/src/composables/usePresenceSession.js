/**
 * Cache leve de sessão de presença, keyed por userId.
 * Sobrevive a remounts do PresencePanel (ex.: refetch após ações).
 */
import { reactive } from 'vue'
import { todayBrDate } from '../utils/presenceFormat'

/** @type {Map<string, import('vue').Reactive<{ selectedDate: string, result: any, listOpen: boolean, error: string }>>} */
const sessions = new Map()

export function getPresenceSession(userId) {
  if (!userId) return null
  let session = sessions.get(userId)
  if (!session) {
    session = reactive({
      selectedDate: todayBrDate(),
      result: null,
      listOpen: false,
      error: '',
    })
    sessions.set(userId, session)
  }
  return session
}

/** Limpa sessão (ex.: busca de outro usuário — opcional; troca de key já isola). */
export function clearPresenceSession(userId) {
  if (userId) sessions.delete(userId)
}
