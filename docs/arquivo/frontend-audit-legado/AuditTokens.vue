<template>
  <span>
    <template v-for="(tok, i) in tokens" :key="i">
      <span v-if="tok.t === 'text'" class="text-gray-400">{{ tok.v }}</span>

      <span v-else-if="tok.t === 'strong'" class="font-medium text-gray-100">{{ tok.v }}</span>

      <!-- UUID de usuário resolvido para nome via cache -->
      <span v-else-if="tok.t === 'user' && nameOf(tok.id)" class="font-medium text-gray-100">
        {{ nameOf(tok.id) }}
      </span>

      <!-- role/grupo resolvido via mapa bulk: nome + copiar UUID -->
      <span
        v-else-if="tok.t === 'uuid' && entityNameOf(tok)"
        class="font-medium text-gray-100 border-b border-dotted border-gray-600 cursor-pointer hover:border-gray-400"
        :title="`${tok.hint}: ${entityNameOf(tok)} (UUID ${tok.id}) — clique para copiar`"
        @click.stop="copy(tok.id)"
      >{{ entityNameOf(tok) }}</span>

      <!-- UUID sem nome (ainda) resolvido: abreviado + tooltip + copiar -->
      <button
        v-else-if="tok.id"
        type="button"
        class="inline-flex items-center gap-1 rounded border border-gray-700 bg-gray-800/80
               px-1.5 py-px font-mono text-[11px] text-gray-300 align-baseline
               hover:border-gray-500 hover:text-gray-100 transition-colors"
        :title="titleOf(tok)"
        @click.stop="copy(tok.id)"
      >
        <template v-if="copied === tok.id">copiado ✓</template>
        <template v-else>
          {{ shortUuid(tok.id) }}
          <svg class="h-3 w-3 opacity-60" viewBox="0 0 20 20" fill="currentColor">
            <path d="M7 5a2 2 0 012-2h6a2 2 0 012 2v6a2 2 0 01-2 2h-1v-1.5H15a.5.5 0 00.5-.5V5a.5.5 0 00-.5-.5H9a.5.5 0 00-.5.5v1H7V5z" />
            <rect x="3" y="7" width="10" height="10" rx="2" fill="none" stroke="currentColor" stroke-width="1.5" />
          </svg>
        </template>
      </button>

      <span v-else class="text-gray-500">—</span>
    </template>
  </span>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { shortUuid, copyText } from './auditFormat'
import { useUserNames } from '../composables/useUserNames'
import { useRoleNames, useGroupNames, useDivisionNames } from '../composables/useEntityNames'

const props = defineProps({
  // Lista de tokens produzida por describeEvent()/formatChanges()
  tokens: { type: Array, default: () => [] },
})

const { nameOf, resolveMany } = useUserNames()
const roleNames = useRoleNames()
const groupNames = useGroupNames()
const divisionNames = useDivisionNames()
const copied = ref(null)
let copyTimer = null

// Nome resolvido de um token de role/grupo/divisão (via mapa bulk), ou null.
function entityNameOf(tok) {
  if (tok.t !== 'uuid') return null
  if (tok.hint === 'role') return roleNames.nameOf(tok.id)
  if (tok.hint === 'group') return groupNames.nameOf(tok.id)
  if (tok.hint === 'division') return divisionNames.nameOf(tok.id)
  return null
}

// Pede resolução dos UUIDs de usuário presentes na frase; o cache global
// deduplica e limita a concorrência, então isso é barato mesmo com N eventos.
function requestNames() {
  resolveMany(props.tokens.filter((t) => t.t === 'user' && t.id).map((t) => t.id))
}

// Dispara o fetch do mapa de roles/grupos/divisões (uma vez por sessão,
// guardado) só quando há um token daquele tipo na frase — resolução
// automática, sem clique.
function ensureMaps() {
  if (props.tokens.some((t) => t.t === 'uuid' && t.hint === 'role')) roleNames.ensureBulk()
  if (props.tokens.some((t) => t.t === 'uuid' && t.hint === 'group')) groupNames.ensureBulk()
  if (props.tokens.some((t) => t.t === 'uuid' && t.hint === 'division')) divisionNames.ensureBulk()
}

onMounted(() => {
  requestNames()
  ensureMaps()
})
watch(
  () => props.tokens,
  () => {
    requestNames()
    ensureMaps()
  },
)

function titleOf(tok) {
  const kind = tok.t === 'user' ? 'UUID do usuário' : tok.hint ? `UUID (${tok.hint})` : 'UUID'
  return `${kind}: ${tok.id} — clique para copiar`
}

async function copy(id) {
  if (await copyText(id)) {
    copied.value = id
    clearTimeout(copyTimer)
    copyTimer = setTimeout(() => (copied.value = null), 1500)
  }
}
</script>
