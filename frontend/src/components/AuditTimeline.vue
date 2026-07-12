<template>
  <section v-if="entities.length" class="space-y-8">
    <div v-for="group in groupedByDay" :key="group.day">
      <h2
        class="sticky top-0 z-10 bg-gray-950/90 backdrop-blur text-sm font-bold
               text-gray-300 py-2 border-b border-gray-800"
      >
        {{ group.label }}
        <span class="ml-2 text-xs font-medium text-gray-500">
          {{ group.items.length }} evento{{ group.items.length === 1 ? '' : 's' }}
        </span>
      </h2>

      <ol class="relative ml-3 border-l-2 border-gray-800">
        <li v-for="item in group.items" :key="item.ev.id" class="ml-5 py-3">
          <span
            class="absolute -left-[7px] mt-2.5 h-3 w-3 rounded-full ring-4 ring-gray-950"
            :class="dotClass(item.kind)"
          ></span>

          <article
            class="rounded-xl border transition cursor-pointer"
            :class="item.system
              ? 'border-gray-800 bg-gray-900/50 hover:bg-gray-900/80'
              : 'border-gray-700 bg-gray-900/80 hover:bg-gray-900'"
            @click="toggle(item.ev.id)"
          >
            <div class="flex items-start gap-3 px-4 py-3">
              <span class="font-mono text-xs text-gray-500 w-16 shrink-0 mt-0.5">
                {{ timeOf(item.ev.eventDate) }}
              </span>

              <!-- Avatar: iniciais do autor humano; engrenagem para SYSTEM -->
              <span
                class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[11px] font-bold text-white mt-0.5"
                :class="item.system ? 'bg-gray-700' : avatarClass(item.author)"
              >
                <svg v-if="item.system" class="h-4 w-4 text-gray-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" clip-rule="evenodd"
                    d="M11.5 2.6a1.5 1.5 0 00-3 0l-.1.8a5.9 5.9 0 00-1.2.7l-.8-.3a1.5 1.5 0 00-1.8 2.2l.5.7a6 6 0 000 1.4l-.5.7a1.5 1.5 0 001.8 2.2l.8-.3c.4.3.8.5 1.2.7l.1.8a1.5 1.5 0 003 0l.1-.8c.4-.2.8-.4 1.2-.7l.8.3a1.5 1.5 0 001.8-2.2l-.5-.7a6 6 0 000-1.4l.5-.7a1.5 1.5 0 00-1.8-2.2l-.8.3a5.9 5.9 0 00-1.2-.7l-.1-.8zM10 12a2 2 0 100-4 2 2 0 000 4z" />
                </svg>
                <template v-else>{{ initials(item.author) }}</template>
              </span>

              <div class="min-w-0 flex-1">
                <p class="text-sm leading-snug break-words">
                  <span
                    class="font-semibold"
                    :class="item.system ? 'text-gray-400' : 'text-gray-100'"
                  >{{ item.author || (item.viaApi ? 'Integração' : 'Sistema') }}</span>
                  <span
                    v-if="item.viaApi"
                    class="ml-1.5 rounded-full px-1.5 py-0.5 text-[10px] font-semibold
                           bg-purple-900/30 text-purple-300 border border-purple-800/40 align-middle"
                  >via API</span>
                  {{ ' ' }}
                  <AuditTokens :tokens="item.phrase" />
                </p>

                <!-- Badge de status + chevron: linha própria, nunca sobrepõe o texto acima -->
                <div class="mt-1 flex items-center justify-between gap-2">
                  <p class="text-[11px] text-gray-500 truncate">
                    {{ item.ev.serviceName }} · {{ item.ev.entityType }}
                    <span v-if="item.system" class="text-gray-600">· automático</span>
                  </p>

                  <div class="flex items-center gap-2 shrink-0">
                    <span
                      class="rounded-full px-2.5 py-0.5 text-xs font-semibold shrink-0"
                      :class="badgeClass(item.kind)"
                    >
                      {{ item.ev.action }}
                    </span>

                    <svg
                      class="h-4 w-4 text-gray-500 transition-transform shrink-0"
                      :class="{ 'rotate-180': expanded.has(item.ev.id) }"
                      viewBox="0 0 20 20" fill="currentColor"
                    >
                      <path fill-rule="evenodd" clip-rule="evenodd"
                        d="M5.3 7.3a1 1 0 011.4 0L10 10.6l3.3-3.3a1 1 0 111.4 1.4l-4 4a1 1 0 01-1.4 0l-4-4a1 1 0 010-1.4z" />
                    </svg>
                  </div>
                </div>
              </div>
            </div>

            <!-- Detalhe expandido -->
            <div
              v-if="expanded.has(item.ev.id)"
              class="border-t border-gray-800 px-4 py-4 space-y-4"
              @click.stop
            >
              <!-- Diff de propriedades, já traduzido/formatado -->
              <div v-if="changesOf(item.ev).length" class="space-y-2">
                <p class="text-xs font-semibold uppercase tracking-wide text-gray-500">
                  O que mudou
                </p>
                <div
                  v-for="(row, i) in changesOf(item.ev)"
                  :key="i"
                  class="rounded-lg border p-3"
                  :class="row.noise
                    ? 'bg-gray-950/30 border-gray-800/60 opacity-60'
                    : 'bg-gray-950/60 border-gray-800'"
                >
                  <p class="text-xs break-all">
                    <AuditTokens :tokens="row.label" />
                    <span v-if="row.noise" class="ml-1.5 text-gray-600 italic">
                      contador interno — muda a cada sincronização
                    </span>
                  </p>
                  <div class="mt-2 flex flex-wrap items-start gap-2 text-xs">
                    <template v-if="row.old.length">
                      <template v-for="(v, j) in row.old" :key="'o' + j">
                        <pre
                          v-if="v.json"
                          class="w-full overflow-x-auto rounded bg-red-900/10 border border-red-800/30 px-2 py-1.5 font-mono text-red-300/90 whitespace-pre-wrap"
                        >{{ v.text }}</pre>
                        <span
                          v-else
                          class="rounded bg-red-900/20 border border-red-800/40 px-2 py-0.5 font-mono text-red-300 line-through break-all"
                          :title="v.title"
                        >{{ v.text }}</span>
                      </template>
                    </template>
                    <span v-else class="text-gray-600 italic">vazio</span>

                    <span class="text-gray-500 pt-0.5">→</span>

                    <template v-if="row.new.length">
                      <template v-for="(v, j) in row.new" :key="'n' + j">
                        <pre
                          v-if="v.json"
                          class="w-full overflow-x-auto rounded bg-green-900/10 border border-green-800/30 px-2 py-1.5 font-mono text-green-300/90 whitespace-pre-wrap"
                        >{{ v.text }}</pre>
                        <span
                          v-else
                          class="rounded bg-green-900/20 border border-green-800/40 px-2 py-0.5 font-mono text-green-300 break-all"
                          :title="v.title"
                        >{{ v.text }}</span>
                      </template>
                    </template>
                    <span v-else class="text-gray-600 italic">vazio</span>
                  </div>
                </div>
              </div>

              <!-- PeoplePermissions não envia diff: a ação + alvo é a informação -->
              <p
                v-else-if="item.ev.entityType === 'Role'"
                class="text-xs text-gray-500 rounded-lg border border-gray-800 bg-gray-950/40 p-3"
              >
                Este serviço não envia diff de propriedades — o evento em si já é a
                informação completa: <AuditTokens :tokens="item.phrase" />.
              </p>
              <p v-else class="text-xs text-gray-500 italic">
                Evento sem diff de propriedades (ex.: criação/remoção direta).
              </p>

              <!-- Metadados e IDs técnicos -->
              <div class="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-gray-500 pt-1 border-t border-gray-800/60">
                <span>
                  <span class="font-semibold text-gray-400">Origem:</span>
                  {{ item.system ? 'sistema / automação' : 'ação humana' }}
                </span>
                <span v-if="item.ev.remoteIp?.length">
                  <span class="font-semibold text-gray-400">IP:</span>
                  {{ item.ev.remoteIp.join(', ') }}
                </span>
                <span>
                  <span class="font-semibold text-gray-400">Serviço:</span>
                  {{ item.ev.serviceName }}
                </span>
                <button
                  v-if="item.ev.entity?.id"
                  type="button"
                  class="font-mono text-gray-600 hover:text-gray-300 transition-colors"
                  :title="`UUID da entidade: ${item.ev.entity.id} — clique para copiar`"
                  @click="copyMeta(item.ev.id + ':entity', item.ev.entity.id)"
                >
                  entidade: {{ copiedMeta === item.ev.id + ':entity' ? 'copiado ✓' : shortUuid(item.ev.entity.id) }}
                </button>
                <button
                  type="button"
                  class="font-mono text-gray-600 hover:text-gray-300 transition-colors"
                  :title="`ID do evento de auditoria: ${item.ev.id} — clique para copiar`"
                  @click="copyMeta(item.ev.id + ':audit', item.ev.id)"
                >
                  audit: {{ copiedMeta === item.ev.id + ':audit' ? 'copiado ✓' : shortUuid(item.ev.id) }}
                </button>
              </div>
            </div>
          </article>
        </li>
      </ol>
    </div>
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import AuditTokens from './AuditTokens.vue'
import { useUserNames } from '../composables/useUserNames'
import {
  actionKind,
  copyText,
  describeEvent,
  formatChanges,
  shortUuid,
} from '../utils/auditFormat'

const props = defineProps({
  entities: { type: Array, default: () => [] },
  // { uuid: nome } — nomes já conhecidos pelo chamador (ex.: pessoa buscada),
  // alimenta o cache e evita chamadas de resolução
  knownNames: { type: Object, default: () => ({}) },
})

const { prime } = useUserNames()

// Alimenta o cache de nomes de graça: pessoa conhecida do chamador + autores
// que já vêm nomeados pelo expand=user do backend (muitas vezes são as mesmas
// pessoas que aparecem como membros em outros eventos).
watch(
  [() => props.entities, () => props.entities.length, () => props.knownNames],
  () => {
    for (const [id, name] of Object.entries(props.knownNames || {})) prime(id, name)
    for (const ev of props.entities) prime(ev.user?.id, ev.user?.name)
  },
  { immediate: true },
)

const expanded = ref(new Set())

function toggle(id) {
  const s = new Set(expanded.value)
  s.has(id) ? s.delete(id) : s.add(id)
  expanded.value = s
}

const groupedByDay = computed(() => {
  const map = new Map()
  for (const ev of props.entities) {
    const day = (ev.eventDate || '').slice(0, 10)
    if (!map.has(day)) map.set(day, [])
    map.get(day).push({
      ev,
      phrase: describeEvent(ev),
      kind: actionKind(ev.action),
      system: ev.level !== 'USER',
      viaApi: !ev.user?.id && !!ev.client?.id,
      author: ev.user?.name || null,
    })
  }
  return [...map.entries()].map(([day, items]) => ({
    day,
    label: new Date(day + 'T12:00:00').toLocaleDateString('pt-BR', {
      weekday: 'long', day: '2-digit', month: 'long', year: 'numeric',
    }),
    items,
  }))
})

// Diff calculado só quando o evento está expandido (chamado no template)
const changesOf = (ev) => formatChanges(ev)

const timeOf = (iso) =>
  iso
    ? new Date(iso).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : '—'

const initials = (name) =>
  name ? name.split(' ').map((p) => p[0]).slice(0, 2).join('').toUpperCase() : '?'

const badgeClass = (kind) =>
  ({
    create: 'bg-green-900/30 text-green-300 border border-green-800/40',
    delete: 'bg-red-900/30 text-red-300 border border-red-800/40',
    update: 'bg-blue-900/30 text-blue-300 border border-blue-800/40',
    other: 'bg-gray-800 text-gray-300 border border-gray-700',
  })[kind]

const dotClass = (kind) =>
  ({
    create: 'bg-green-500',
    delete: 'bg-red-500',
    update: 'bg-blue-500',
    other: 'bg-gray-500',
  })[kind]

const AVATAR_COLORS = ['bg-purple-600', 'bg-indigo-600', 'bg-cyan-600', 'bg-teal-600', 'bg-amber-600']
const avatarClass = (name) =>
  name
    ? AVATAR_COLORS[[...name].reduce((s, c) => s + c.charCodeAt(0), 0) % AVATAR_COLORS.length]
    : 'bg-gray-600'

const copiedMeta = ref(null)
let copyTimer = null
async function copyMeta(key, value) {
  if (await copyText(value)) {
    copiedMeta.value = key
    clearTimeout(copyTimer)
    copyTimer = setTimeout(() => (copiedMeta.value = null), 1500)
  }
}
</script>
