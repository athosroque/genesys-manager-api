// Interpretação dos eventos da Platform Audit API para exibição legível.
// As regras por serviço vêm do comportamento real da org, documentado em
// "refencia retornos/DICIONARIO-AUDITORIA.md" (§4 — perfil por serviço).

import { useDivisionNames } from '../composables/useEntityNames'
import { useUserNames } from '../composables/useUserNames'

const UUID_PART = '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'

export const UUID_RE = new RegExp(`^${UUID_PART}$`, 'i')

// ContactCenter/Queue: o UUID da pessoa afetada não vem em campo próprio —
// está embutido na chave do diff: QueueMember/<uuid-fila>:<uuid-usuario>[:joined]
const QUEUE_MEMBER_RE = new RegExp(`^QueueMember/(${UUID_PART}):(${UUID_PART})(?::(joined))?$`, 'i')

// PeoplePermissions/Role: entity.name NÃO é o nome da role — é a chave
// composta {uuid-usuario}--{uuid-role}--{uuid-org}
const ROLE_KEY_RE = new RegExp(`^(${UUID_PART})--(${UUID_PART})--(${UUID_PART})$`, 'i')

// Groups/DirectoryGroup: o propertyChange "group-membership" traz os UUIDs
// dos membros afetados como uma única string "[uuid1, uuid2]" — não é JSON
// válido (UUIDs sem aspas), então extraímos por regex. Confirmado empírico
// (explorar_auditoria.py --amostra Groups): a Genesys sempre manda também um
// propertyChange irmão "individuals" para o mesmo evento/timestamp, mas esse
// vem com oldValues/newValues vazios em 100% dos casos (104/104 numa amostra
// de 30 dias) — é ruído puro da API, o UUID do membro só existe aqui.
const GROUP_MEMBERSHIP_UUID_RE = new RegExp(UUID_PART, 'gi')

export function parseGroupMembershipIds(value = '') {
  return String(value).match(GROUP_MEMBERSHIP_UUID_RE) || []
}

// Valores-sentinela literais devolvidos pela API (vêm assim mesmo, não são
// placeholders de documentação)
const SENTINELS = {
  '<queue member added>': 'Membro adicionado à fila',
  '<queue member deleted>': 'Membro removido da fila',
}

export const isUuid = (v) =>
  typeof v === 'string' && UUID_RE.test(v.trim().replace(/[{}]/g, ''))

export const shortUuid = (id = '') =>
  id.length > 13 ? `${id.slice(0, 8)}…${id.slice(-4)}` : id

export function parseQueueMemberProp(property = '') {
  const m = QUEUE_MEMBER_RE.exec(property)
  return m ? { queueId: m[1], userId: m[2], joined: !!m[3] } : null
}

export function parseRoleKey(name = '') {
  const m = ROLE_KEY_RE.exec(name)
  return m ? { userId: m[1], roleId: m[2], orgId: m[3] } : null
}

// Classificação da ação → cor (create=verde, update=azul, delete=vermelho)
export function actionKind(action = '') {
  const a = action.toLowerCase()
  if (a.includes('create') || a.includes('add')) return 'create'
  if (a.includes('delete') || a.includes('remove') || a.includes('deactivat')) return 'delete'
  if (a.includes('update') || a.includes('edit') || a.includes('activat')) return 'update'
  return 'other'
}

// oldValues/newValues podem trazer JSON serializado como string (ex.: addresses
// no Directory). Devolve a versão indentada, ou null se não for JSON.
export function tryPrettyJson(value) {
  if (typeof value !== 'string') return null
  const s = value.trim()
  if (!s.startsWith('{') && !s.startsWith('[')) return null
  try {
    return JSON.stringify(JSON.parse(s), null, 2)
  } catch {
    return null
  }
}

// ---------------------------------------------------------------------------
// Frase legível do evento, como lista de tokens:
//   { t: 'text',   v }        texto corrido
//   { t: 'strong', v }        nome conhecido (destaque)
//   { t: 'user',   id }       UUID de usuário — resolvível p/ nome via cache
//   { t: 'uuid',   id, hint } UUID sem resolução possível (ex.: role) — exibir
//                             abreviado com tooltip + copiar
// ---------------------------------------------------------------------------

const text = (v) => ({ t: 'text', v })
const strong = (v) => ({ t: 'strong', v })
const user = (id) => ({ t: 'user', id })
const uuid = (id, hint) => ({ t: 'uuid', id, hint })

// Junta tokens de usuário em lista legível: "A", "A e B", "A, B e C"
function joinTokens(toks) {
  if (toks.length <= 1) return toks
  const out = []
  toks.forEach((t, i) => {
    if (i > 0) out.push(text(i === toks.length - 1 ? ' e ' : ', '))
    out.push(t)
  })
  return out
}

const GENERIC_VERBS = { create: 'criou', update: 'atualizou', delete: 'excluiu' }

const ENTITY_LABELS = {
  Queue: 'a fila',
  Role: 'a role',
  User: 'o usuário',
  Organization: 'a organização',
  WrapupCode: 'o wrapup code',
  Team: 'o time',
  SkillGroup: 'o skill group',
  DirectoryGroup: 'o grupo',
  OAuthClient: 'o OAuth client',
}

// entityTypes do serviço Groups (ver DICIONARIO-AUDITORIA.md §1). Normalizamos
// todos para o hint 'group' para o chip resolver via mapa de grupos.
const GROUP_ENTITY_TYPES = new Set(['DirectoryGroup', 'SkillGroup', 'Team', 'SkillGroupDefinition'])

function entityToken(ev, hint) {
  if (ev.entity?.name) return strong(ev.entity.name)
  if (ev.entity?.id) return uuid(ev.entity.id, GROUP_ENTITY_TYPES.has(hint) ? 'group' : hint)
  return text('—')
}

function genericPhrase(ev) {
  const verb = GENERIC_VERBS[actionKind(ev.action)]
  const label = ENTITY_LABELS[ev.entityType] || ev.entityType || 'entidade'
  if (verb) return [text(`${verb} ${label} `), entityToken(ev, ev.entityType)]
  return [text('executou '), strong(ev.action || '?'), text(` em ${label} `), entityToken(ev, ev.entityType)]
}

export function describeEvent(ev = {}) {
  const action = ev.action || ''

  // ContactCenter/Queue — membership: a pessoa está no diff (QueueMember/...)
  if (ev.entityType === 'Queue') {
    let member = null
    let joinedChange = null
    for (const pc of ev.propertyChanges || []) {
      const p = parseQueueMemberProp(pc.property)
      if (!p) continue
      if (p.joined && !joinedChange) joinedChange = { ...p, newValue: (pc.newValues || [])[0] }
      if (!member) member = p
    }
    const queueTok = ev.entity?.name ? strong(ev.entity.name) : uuid(ev.entity?.id, 'fila')
    if (joinedChange && action === 'MemberUpdate') {
      const verb =
        joinedChange.newValue === 'false' ? 'desativou'
        : joinedChange.newValue === 'true' ? 'ativou'
        : 'atualizou'
      return [text(`${verb} `), user(joinedChange.userId), text(' na fila '), queueTok]
    }
    if (member) {
      if (action === 'MemberAdd') return [text('adicionou '), user(member.userId), text(' à fila '), queueTok]
      if (action === 'MemberRemove') return [text('removeu '), user(member.userId), text(' da fila '), queueTok]
      return [text('atualizou '), user(member.userId), text(' na fila '), queueTok]
    }
    return genericPhrase(ev)
  }

  // PeoplePermissions/Role — a pessoa está na chave composta de entity.name.
  // O UUID da role é resolvido para nome via mapa de roles (GET /roles),
  // primado automaticamente pelo AuditTokens.vue.
  if (ev.entityType === 'Role') {
    const key = parseRoleKey(ev.entity?.name)
    if (key) {
      const roleTok = uuid(key.roleId, 'role')
      if (action === 'MemberAdd') return [text('atribuiu a role '), roleTok, text(' a '), user(key.userId)]
      if (action === 'MemberRemove') return [text('removeu a role '), roleTok, text(' de '), user(key.userId)]
      const verb = GENERIC_VERBS[actionKind(action)] || 'alterou'
      return [text(`${verb} a role `), roleTok, text(' de '), user(key.userId)]
    }
    return genericPhrase(ev)
  }

  // Groups (DirectoryGroup/SkillGroup/Team/...) — o membro afetado está
  // embutido na string do propertyChange "group-membership", não em campo
  // próprio (ver parseGroupMembershipIds acima). A Genesys NÃO expõe se foi
  // adição ou remoção nesse propertyChange — newValues sempre traz o(s)
  // UUID(s) afetado(s), oldValues sempre vazio, nos dois casos. A direção
  // real vem do backend (`_groupMembershipDirection`, ver
  // _enrich_group_membership_direction em routes/audits.py), inferida do
  // memberCount irmão. Sem essa anotação, não afirmamos direção.
  if (GROUP_ENTITY_TYPES.has(ev.entityType)) {
    const membership = (ev.propertyChanges || []).find((pc) => pc.property === 'group-membership')
    if (membership) {
      const ids = [
        ...parseGroupMembershipIds((membership.oldValues || [])[0]),
        ...parseGroupMembershipIds((membership.newValues || [])[0]),
      ]
      if (ids.length) {
        const groupTok = entityToken(ev, ev.entityType)
        const direction = ev._groupMembershipDirection
        const verb = direction === 'add' ? 'adicionou' : direction === 'remove' ? 'removeu' : 'alterou a associação de'
        const prep = direction === 'add' ? ' ao grupo ' : direction === 'remove' ? ' do grupo ' : ' com o grupo '
        return [text(`${verb} `), ...joinTokens(ids.map(user)), text(prep), groupTok]
      }
    }
  }

  // Directory/User — o alvo do evento é a própria pessoa (entity.id).
  // Mudança de divisão é a mais relevante pro card colapsado — mostra direto
  // no título (resolvida via mapa de divisões) em vez do genérico "atualizou
  // o perfil de", que só aparece no diff expandido.
  if (ev.serviceName === 'Directory' && ev.entityType === 'User' && ev.entity?.id) {
    if (actionKind(action) === 'update') {
      const divisionChange = (ev.propertyChanges || []).find((pc) => pc.property === 'divisionId')
      const oldDivisionId = divisionChange?.oldValues?.[0]
      const newDivisionId = divisionChange?.newValues?.[0]
      if (oldDivisionId && newDivisionId) {
        return [
          text('moveu '), user(ev.entity.id), text(' de '),
          uuid(oldDivisionId, 'division'), text(' para '), uuid(newDivisionId, 'division'),
        ]
      }
    }
    const verb = {
      create: 'criou o usuário',
      update: 'atualizou o perfil de',
      delete: 'excluiu o usuário',
    }[actionKind(action)]
    if (verb) return [text(`${verb} `), user(ev.entity.id)]
  }

  return genericPhrase(ev)
}

// ---------------------------------------------------------------------------
// Diff legível: cada linha com label em tokens (permite resolver o membro da
// fila p/ nome) e valores já traduzidos (sentinelas, joined, JSON indentado).
// `noise` marca campos internos sem valor de negócio (version muda a cada sync).
// ---------------------------------------------------------------------------

export function formatChanges(ev = {}) {
  const divisionNames = useDivisionNames()
  const userNames = useUserNames()
  const hasDivisionChange = (ev.propertyChanges || []).some((pc) => pc.property === 'divisionId')
  // Dispara o fetch do mapa de divisões (uma vez por sessão, guardado) só
  // quando o diff realmente tem um divisionId — resolução automática, sem
  // clique, mesmo padrão do mapa de roles/grupos.
  if (hasDivisionChange) divisionNames.ensureBulk()

  const rows = (ev.propertyChanges || [])
    // "individuals" (serviço Groups) sempre vem vazio nos dois lados — ruído
    // puro da API, sem informação de negócio. O membro afetado de verdade
    // está no propertyChange irmão "group-membership", tratado abaixo.
    .filter((pc) => pc.property !== 'individuals')
    .map((pc) => {
      const qm = parseQueueMemberProp(pc.property)
      const isDivision = pc.property === 'divisionId'
      const isGroupMembership = pc.property === 'group-membership'
      const noise = pc.property === 'version'

      if (isGroupMembership) {
        // Genesys sempre traz o(s) UUID(s) afetado(s) em newValues/oldValues
        // indistintamente — junta os dois lados e usa a direção anotada pelo
        // backend (`_groupMembershipDirection`) pra decidir o lado visual
        // (vermelho/removido vs verde/adicionado), em vez de assumir que
        // "novo valor preenchido" sempre significa adição.
        const ids = [
          ...parseGroupMembershipIds((pc.oldValues || [])[0]),
          ...parseGroupMembershipIds((pc.newValues || [])[0]),
        ]
        userNames.resolveMany(ids)
        const toPill = (id) => ({
          text: userNames.nameOf(id) || shortUuid(id),
          json: false,
          title: `Usuário — UUID ${id}`,
        })
        const direction = ev._groupMembershipDirection
        const pills = ids.map(toPill)
        const label =
          direction === 'add' ? 'Membro adicionado ao grupo'
          : direction === 'remove' ? 'Membro removido do grupo'
          : 'Associação com o grupo alterada (direção não identificada)'
        return {
          property: pc.property,
          label: [text(label)],
          old: direction === 'remove' ? pills : [],
          new: direction === 'remove' ? [] : pills,
          noise: false,
        }
      }

      const label = qm
        ? [text(qm.joined ? 'Ativação na fila — membro ' : 'Vínculo com a fila — membro '), user(qm.userId)]
        : [text(pc.property || '—')]

      const mapVals = (arr) =>
        (arr || [])
          .filter((v) => v !== '' && v != null)
          .map((v) => {
            if (SENTINELS[v]) return { text: SENTINELS[v], json: false }
            if (qm?.joined) {
              const t = v === 'true' ? 'ativo na fila' : v === 'false' ? 'inativo na fila' : v
              return { text: t, json: false }
            }
            if (isDivision && isUuid(v)) {
              const name = divisionNames.nameOf(v)
              return name
                ? { text: name, json: false, title: `Divisão — UUID ${v}` }
                : { text: v, json: false }
            }
            const pretty = tryPrettyJson(v)
            return pretty ? { text: pretty, json: true } : { text: v, json: false }
          })

      return { property: pc.property, label, old: mapVals(pc.oldValues), new: mapVals(pc.newValues), noise }
    })
  // campos-ruído (version) por último
  return rows.sort((a, b) => Number(a.noise) - Number(b.noise))
}

// Copiar com fallback — clipboard API exige contexto seguro (https/localhost)
export async function copyText(value) {
  try {
    await navigator.clipboard.writeText(value)
    return true
  } catch {
    const ta = document.createElement('textarea')
    ta.value = value
    ta.style.position = 'fixed'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.select()
    let ok = false
    try {
      ok = document.execCommand('copy')
    } catch {
      ok = false
    }
    ta.remove()
    return ok
  }
}
