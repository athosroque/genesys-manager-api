<template>
  <div class="max-w-5xl mx-auto space-y-8">

    <!-- Título -->
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-white tracking-tight">Consulta e Ações</h1>
      <p class="text-sm text-gray-400 mt-1">Busque um usuário para visualizar seus dados e executar ações na Genesys Cloud.</p>
    </div>

    <!-- Barra de Busca -->
    <SearchBar :loading="searchLoading" @search="handleSearch" />

    <!-- Estado Vazio Inicial -->
    <div v-if="!searched" class="flex flex-col items-center justify-center py-24 text-center">
      <div class="text-6xl mb-5 select-none">🔷</div>
      <h2 class="text-xl font-semibold text-gray-300 mb-2">Busque um usuário para começar</h2>
      <p class="text-sm text-gray-500">Aceita matrícula, e-mail ou UUID</p>
    </div>

    <!-- Aviso: Não Encontrado -->
    <div v-else-if="searched && !foundUser && !searchError && !searchLoading" class="rounded-xl border border-purple-800/60 bg-purple-900/20 p-5 flex items-start gap-4 text-purple-300">
      <svg class="w-5 h-5 mt-0.5 shrink-0 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <div>
        <p class="font-semibold text-purple-200">Usuário não encontrado</p>
        <p class="text-sm text-purple-400 mt-0.5">Nenhum resultado para: <strong class="font-mono">{{ lastQuery }}</strong></p>
      </div>
    </div>

    <!-- Aviso: Erro -->
    <div v-else-if="searchError" class="rounded-xl border border-red-800/60 bg-red-900/20 p-5 flex items-start gap-4 text-red-300">
      <svg class="w-5 h-5 mt-0.5 shrink-0 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <div>
        <p class="font-semibold text-red-200">Erro na busca</p>
        <p class="text-sm text-red-400 font-mono mt-0.5">{{ searchError }}</p>
      </div>
    </div>

    <!-- Resultado Principal -->
    <template v-else-if="user">

      <!-- Card do Usuário -->
      <UserCard 
        :user="user" 
        :queues="queues" 
        :loading="queuesLoading"
        @remove-from-queue="onRemoveFromQueue"
        @remove-all-queues="showQueuesConfirm = true"
      />

      <!-- Confirm: Remoção Individual de Fila -->
      <ConfirmDialog
        v-if="queueToRemove"
        :title="`Remover da fila: ${queueToRemove.name}`"
        message="Esta ação remove o usuário apenas desta fila. Deseja confirmar?"
        confirm-label="Remover"
        type="warning"
        :loading="actionLoading"
        @cancel="queueToRemove = null"
        @confirm="handleRemoveSingleQueue"
      />

      <!-- ──────────────────────────── SEÇÕES DE AÇÃO ──────────────────────────── -->
      <div class="space-y-4">
        <h2 class="text-xs font-bold text-gray-500 uppercase tracking-widest flex items-center gap-2">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
          Ações Disponíveis
        </h2>

        <!-- A) Reativação (apenas se INATIVO) -->
        <div v-if="user.state === 'inactive'" class="rounded-xl border border-yellow-800/60 bg-yellow-900/10 p-5">
          <div class="flex items-center justify-between">
            <div>
              <p class="font-semibold text-yellow-300 flex items-center gap-2">🔒 Usuário Inativo</p>
              <p class="text-sm text-yellow-500 mt-1">Este usuário está desativado na Genesys Cloud.</p>
            </div>
            <button
              v-if="!showReactivateConfirm"
              @click="showReactivateConfirm = true"
              class="px-4 py-2 bg-yellow-600 hover:bg-yellow-500 text-white text-sm font-medium rounded-lg transition-colors whitespace-nowrap flex-shrink-0 ml-4"
            >
              🔄 Reativar Usuário
            </button>
          </div>

          <ConfirmDialog
            v-if="showReactivateConfirm"
            title="Reativar Usuário"
            :message="`Deseja reativar ${user.name}? Suas roles precisarão ser revisadas após a reativação.`"
            confirm-label="Reativar"
            type="warning"
            :loading="actionLoading"
            @cancel="showReactivateConfirm = false"
            @confirm="handleReactivate"
          />
        </div>

        <!-- B) Remover de Todas as Filas (REMOVIDO CONFORME SOLICITAÇÃO) -->

        <!-- C) Remover de um Grupo -->
        <div v-if="user.groups && user.groups.length > 0" class="rounded-xl border border-gray-700 bg-gray-900/80 overflow-hidden">
          <!-- Header -->
          <div class="flex items-center gap-3 px-5 py-4 bg-gray-950/30">
            <div class="p-2 rounded-lg bg-gray-900 border border-gray-700">
              <svg class="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            </div>
            <div>
              <p class="text-sm font-semibold text-gray-200">
                Grupos do Usuário (<span class="text-purple-400">{{ user.groups.length }}</span>)
              </p>
              <p class="text-xs text-gray-500 mt-0.5">Remoção individual por grupo</p>
            </div>
          </div>

          <!-- Tabela -->
          <div class="border-t border-gray-800">
            <table class="min-w-full divide-y divide-gray-800/50">
              <thead class="bg-gray-950/80">
                <tr>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 tracking-wider">Nome do Grupo</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 tracking-wider">System ID (UUID)</th>
                  <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 tracking-wider">Ação</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-800/30">
                <tr v-for="g in user.groups" :key="typeof g === 'string' ? g : g.id" class="hover:bg-gray-800/30 transition-colors">
                  <td class="px-6 py-3 whitespace-nowrap text-sm font-medium text-purple-200">
                    {{ typeof g === 'string' ? g.substring(0, 12) : (g.name || '—') }}
                  </td>
                  <td class="px-6 py-3 whitespace-nowrap text-xs text-gray-500 font-mono">
                    {{ typeof g === 'string' ? g : g.id }}
                  </td>
                  <td class="px-6 py-3 whitespace-nowrap text-right">
                    <button
                      @click="groupToRemove = g"
                      class="inline-flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-red-400 bg-red-900/20 border border-red-800/40 rounded-md hover:bg-red-900/40 transition-all"
                    >
                      <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                      Remover
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Confirm: Remoção de Grupo Individual -->
        <ConfirmDialog
          v-if="groupToRemove"
          :title="`Remover do grupo: ${typeof groupToRemove === 'string' ? groupToRemove.substring(0,12) : (groupToRemove.name || groupToRemove.id)}`"
          message="O usuário será removido deste grupo. Deseja confirmar?"
          confirm-label="Remover"
          type="warning"
          :loading="groupActionLoading"
          @cancel="groupToRemove = null"
          @confirm="handleRemoveGroup"
        />

        <!-- D) Migração (sempre visível após busca) -->
        <div class="rounded-xl border border-blue-800/40 bg-blue-900/10 p-5">
          <p class="font-semibold text-blue-300 mb-1">🚀 Executar Migração</p>
          <p class="text-sm text-gray-400 mb-4">Atribuir divisão, role e/ou adicionar ao grupo de migração.</p>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
            <div>
              <label class="block text-xs text-gray-500 mb-1.5">Operação</label>
              <select
                v-model="migrationOp"
                class="w-full bg-gray-800 border border-gray-700 text-gray-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="1">1 — Divisão Home + Role Employee</option>
                <option value="2">2 — Adicionar ao Grupo</option>
                <option value="3">3 — Divisão + Role + Grupo</option>
              </select>
            </div>

            <div v-if="migrationOp === '2' || migrationOp === '3'">
              <label class="block text-xs text-gray-500 mb-1.5">Grupo de Migração</label>
              <select
                v-model="migrationGroupId"
                class="w-full bg-gray-800 border border-gray-700 text-gray-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">— escolha um grupo —</option>
                <option 
                  v-for="g in migrationGroups" 
                  :key="g.id" 
                  :value="g.id"
                >
                  {{ g.nome }}
                </option>
              </select>
            </div>
          </div>

          <button
            v-if="!showMigrationConfirm"
            @click="showMigrationConfirm = true"
            :disabled="(migrationOp === '2' || migrationOp === '3') && !migrationGroupId"
            class="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors"
          >
            🚀 Executar Migração
          </button>

          <ConfirmDialog
            v-if="showMigrationConfirm"
            title="Confirmar Migração"
            type="info"
            confirm-label="Executar"
            :loading="actionLoading"
            @cancel="showMigrationConfirm = false"
            @confirm="handleMigration"
          >
            <div class="text-sm text-gray-300 space-y-2 mb-4">
              <div class="bg-gray-950/60 border border-gray-800 rounded-lg p-4 space-y-1.5 text-xs font-mono">
                <p><span class="text-gray-500">Usuário:</span> {{ user.name }}</p>
                <p><span class="text-gray-500">E-mail:</span> {{ user.email }}</p>
                <p><span class="text-gray-500">UUID:</span> {{ user.id }}</p>
                <p><span class="text-gray-500">Operação:</span> {{ migrationOpLabel }}</p>
                <p v-if="migrationGroupId"><span class="text-gray-500">Grupo:</span> {{ migrationGroupLabel }}</p>
              </div>
            </div>
          </ConfirmDialog>

          <!-- Resultado da migração por step -->
          <div v-if="migrationSteps.length > 0" class="mt-4 space-y-1.5">
            <p class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Resultado da Migração:</p>
            <div
              v-for="(step, i) in migrationSteps"
              :key="i"
              class="flex items-start gap-2 text-sm px-3 py-2 rounded-lg"
              :class="{
                'bg-green-900/20 text-green-300 border border-green-800/30': step.status === 'ok',
                'bg-yellow-900/20 text-yellow-300 border border-yellow-800/30': step.status === 'skip',
                'bg-red-900/20 text-red-300 border border-red-800/30': step.status === 'error',
              }"
            >
              <span class="shrink-0 mt-0.5">{{ step.status === 'ok' ? '✅' : step.status === 'skip' ? '⚠️' : '❌' }}</span>
              <div>
                <p class="font-medium leading-tight">{{ step.label }}</p>
                <p class="text-xs opacity-60 mt-0.5">{{ step.detail }}</p>
              </div>
            </div>
          </div>
        </div>

      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import SearchBar from '../components/SearchBar.vue'
import UserCard from '../components/UserCard.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import LoadingSpinner from '../components/LoadingSpinner.vue'
import { useToast } from '../composables/useToast'
import {
  searchUser,
  getUserQueues,
  reactivateUser,
  removeFromAllQueues,
  removeFromQueue,
  removeFromGroup,
  runMigration,
  getGroupsConfig
} from '../api/genesys'

const { addToast } = useToast()

// ─── Estado de busca ───────────────────────────────────────────────────────
const lastQuery    = ref('')
const searchLoading = ref(false)
const searched     = ref(false)
const foundUser    = ref(false)
const searchError  = ref('')
const user         = ref(null)
const queues       = ref([])
const queuesLoading = ref(false)

// ─── Modais e loading das ações ───────────────────────────────────────────
const actionLoading          = ref(false)
const groupActionLoading     = ref(false)
const showReactivateConfirm  = ref(false)
const showMigrationConfirm   = ref(false)
const migrationSteps         = ref([])
const queueToRemove          = ref(null)  // fila selecionada para remoção individual
const groupToRemove          = ref(null)  // grupo selecionado para remoção individual (tabela)
const showQueuesConfirm      = ref(false) // mantido para lógica interna se necessário

// ─── Grupos e migração ────────────────────────────────────────────────────
const migrationOp      = ref('1')
const migrationGroupId = ref('')
const migrationGroups  = ref([])

onMounted(async () => {
  try {
    migrationGroups.value = await getGroupsConfig()
  } catch (err) {
    console.error('Erro ao carregar grupos config:', err)
  }
})

const migrationOpLabel = computed(() => ({
  '1': 'Divisão Home + Role Employee',
  '2': 'Adicionar ao Grupo',
  '3': 'Divisão + Role + Grupo',
}[migrationOp.value]))

const migrationGroupLabel = computed(() => {
  const g = migrationGroups.value.find(x => x.id === migrationGroupId.value)
  return g ? g.nome : ''
})

// ─── Busca ────────────────────────────────────────────────────────────────
async function handleSearch(q) {
  lastQuery.value   = q
  searched.value    = true
  foundUser.value   = false
  searchError.value = ''
  user.value        = null
  queues.value      = []
  migrationSteps.value = []
  searchLoading.value  = true

  try {
    const data = await searchUser(q)
    if (!data.found) {
      foundUser.value = false
      return
    }
    foundUser.value = true
    user.value      = data.user
    fetchQueues(data.user.id)
  } catch (err) {
    searchError.value = err.message
    addToast(err.message, 'error')
  } finally {
    searchLoading.value = false
  }
}

async function fetchQueues(userId) {
  queuesLoading.value = true
  try {
    const data = await getUserQueues(userId)
    queues.value = data.queues || []
  } catch (err) {
    addToast('Erro ao buscar filas: ' + err.message, 'error')
  } finally {
    queuesLoading.value = false
  }
}

async function refetch() {
  if (!lastQuery.value) return
  await handleSearch(lastQuery.value)
}

// ─── Ações ────────────────────────────────────────────────────────────────
async function handleReactivate() {
  actionLoading.value = true
  try {
    await reactivateUser(user.value.id, user.value.version)
    addToast('Usuário reativado com sucesso!', 'success')
    showReactivateConfirm.value = false
    await refetch()
  } catch (err) {
    addToast('Erro ao reativar: ' + err.message, 'error')
  } finally {
    actionLoading.value = false
  }
}


function onRemoveFromQueue(queue) {
  queueToRemove.value = queue
}

async function handleRemoveSingleQueue() {
  if (!queueToRemove.value) return
  actionLoading.value = true
  try {
    await removeFromQueue(queueToRemove.value.id, user.value.id)
    addToast(`Removido da fila "${queueToRemove.value.name}" com sucesso!`, 'success')
    queueToRemove.value = null
    await refetch()
  } catch (err) {
    addToast('Erro ao remover da fila: ' + err.message, 'error')
  } finally {
    actionLoading.value = false
  }
}

async function handleRemoveGroup() {
  if (!groupToRemove.value) return
  
  const gId = typeof groupToRemove.value === 'string' 
    ? groupToRemove.value 
    : groupToRemove.value.id

  groupActionLoading.value = true
  actionLoading.value = true
  try {
    await removeFromGroup(gId, user.value.id)
    addToast('Usuário removido do grupo com sucesso!', 'success')
    groupToRemove.value = null
    await refetch()
  } catch (err) {
    addToast('Erro ao remover do grupo: ' + err.message, 'error')
  } finally {
    groupActionLoading.value = false
    actionLoading.value = false
  }
}

async function handleMigration() {
  actionLoading.value = true
  try {
    const data = await runMigration(user.value.id, migrationOp.value, migrationGroupId.value || null)
    migrationSteps.value = data.steps || []
    showMigrationConfirm.value = false
    const ok = migrationSteps.value.filter(s => s.status === 'ok').length
    addToast(`Migração concluída: ${ok} passo(s) executado(s) com sucesso.`, 'success')
    await refetch()
  } catch (err) {
    addToast('Erro na migração: ' + err.message, 'error')
  } finally {
    actionLoading.value = false
  }
}
</script>
