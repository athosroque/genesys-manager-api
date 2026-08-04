<template>
  <div class="max-w-5xl mx-auto space-y-6">

    <!-- Cabeçalho -->
    <div class="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-white tracking-tight">Usuários da Ferramenta</h1>
        <p class="text-sm text-gray-400 mt-1">
          Gerencie operadores locais da plataforma. O acesso é por magic link no e-mail
          <span class="text-gray-300">@claro.com.br</span>.
        </p>
      </div>
      <button
        type="button"
        @click="showForm = !showForm"
        class="inline-flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 hover:bg-blue-500 rounded-lg transition-colors shrink-0"
      >
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        {{ showForm ? 'Fechar formulário' : 'Cadastrar usuário' }}
      </button>
    </div>

    <!-- Formulário de cadastro -->
    <div
      v-if="showForm"
      class="rounded-xl border border-gray-700 bg-gray-900/80 p-6 space-y-5"
    >
      <div>
        <h2 class="text-lg font-semibold text-gray-100">Cadastrar usuário</h2>
        <p class="text-xs text-gray-500 mt-1">
          O username é derivado automaticamente do e-mail (parte antes do @).
        </p>
      </div>

      <form @submit.prevent="handleCreate" class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div class="sm:col-span-2">
          <label for="create-email" class="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
            E-mail
          </label>
          <input
            id="create-email"
            v-model="form.email"
            type="email"
            required
            autocomplete="off"
            placeholder="nome.sobrenome@claro.com.br"
            class="w-full bg-gray-800 border border-gray-700 text-gray-100 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all placeholder:text-gray-600"
          />
        </div>

        <div>
          <label for="create-name" class="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
            Nome completo
          </label>
          <input
            id="create-name"
            v-model="form.full_name"
            type="text"
            required
            autocomplete="off"
            placeholder="Nome Sobrenome"
            class="w-full bg-gray-800 border border-gray-700 text-gray-100 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all placeholder:text-gray-600"
          />
        </div>

        <div>
          <label for="create-role" class="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
            Papel
          </label>
          <select
            id="create-role"
            v-model="form.role"
            class="w-full bg-gray-800 border border-gray-700 text-gray-100 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all"
          >
            <option value="user">user</option>
            <option value="admin">admin</option>
          </select>
        </div>

        <div
          v-if="formError"
          class="sm:col-span-2 bg-red-900/10 border border-red-900/30 rounded-lg p-3 flex items-center gap-2 text-sm text-red-400"
        >
          <svg class="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {{ formError }}
        </div>

        <div class="sm:col-span-2 flex justify-end gap-3 pt-1">
          <button
            type="button"
            @click="resetForm"
            class="px-4 py-2 text-sm font-medium text-gray-300 hover:text-white border border-gray-700 hover:bg-gray-800 rounded-lg transition-colors"
          >
            Cancelar
          </button>
          <button
            type="submit"
            :disabled="creating"
            class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg transition-colors"
          >
            <LoadingSpinner v-if="creating" class="w-4 h-4" />
            Cadastrar
          </button>
        </div>
      </form>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex justify-center py-24">
      <LoadingSpinner class="w-8 h-8 text-blue-500" />
    </div>

    <!-- Erro -->
    <div v-else-if="error" class="rounded-xl border border-red-800/60 bg-red-900/20 p-5 flex items-start gap-4 text-red-300">
      <svg class="w-5 h-5 mt-0.5 shrink-0 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <div>
        <p class="font-semibold text-red-200">Erro ao carregar usuários</p>
        <p class="text-sm text-red-400 font-mono mt-0.5">{{ error }}</p>
      </div>
    </div>

    <!-- Lista -->
    <div v-else class="rounded-xl border border-gray-700 bg-gray-900/80 overflow-hidden">
      <div class="px-4 sm:px-6 py-4 border-b border-gray-800 flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4">
        <div class="relative flex-1 min-w-0">
          <svg
            class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            v-model="searchQuery"
            type="search"
            autocomplete="off"
            placeholder="Buscar por nome ou e-mail…"
            class="w-full bg-gray-800 border border-gray-700 text-gray-100 rounded-lg pl-10 pr-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all placeholder:text-gray-600"
          />
        </div>
        <p class="text-xs text-gray-500 shrink-0 sm:text-right">
          {{ filteredUsers.length }} de {{ users.length }}
          {{ users.length === 1 ? 'usuário' : 'usuários' }}
        </p>
      </div>

      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-800/50">
          <thead class="bg-gray-950/80">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 tracking-wider">Nome</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 tracking-wider">Username</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 tracking-wider">E-mail</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 tracking-wider">Papel</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 tracking-wider">Status</th>
              <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 tracking-wider">
                <span class="sr-only">Ações</span>
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-800/50">
            <tr
              v-for="u in filteredUsers"
              :key="u.username"
              class="hover:bg-gray-800/30 transition-colors"
            >
              <td class="px-6 py-4 text-sm font-medium text-gray-200">
                <span class="inline-flex items-center gap-2">
                  {{ u.full_name }}
                  <span
                    v-if="isSelf(u)"
                    class="text-[10px] font-semibold uppercase tracking-wider text-gray-500 border border-gray-700 px-1.5 py-0.5 rounded"
                  >
                    você
                  </span>
                </span>
              </td>
              <td class="px-6 py-4 text-xs text-gray-500 font-mono">{{ u.username }}</td>
              <td class="px-6 py-4 text-sm text-gray-400 font-mono">{{ u.email }}</td>
              <td class="px-6 py-4">
                <span
                  class="text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded-md"
                  :class="u.role === 'admin' ? 'bg-blue-600/10 text-blue-400 border border-blue-500/30' : 'bg-gray-800 text-gray-400 border border-gray-700'"
                >
                  {{ u.role }}
                </span>
              </td>
              <td class="px-6 py-4">
                <span
                  class="text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded-md"
                  :class="u.active ? 'bg-green-600/10 text-green-400 border border-green-500/30' : 'bg-red-600/10 text-red-400 border border-red-500/30'"
                >
                  {{ u.active ? 'Ativo' : 'Inativo' }}
                </span>
              </td>
              <td class="px-6 py-4 text-right">
                <button
                  type="button"
                  @click="confirmTarget = u"
                  :disabled="isSelf(u) || deletingUsername === u.username"
                  :title="isSelf(u) ? 'Você não pode excluir a si mesmo' : 'Excluir usuário'"
                  class="px-2.5 py-1 text-[11px] font-medium rounded-md transition-colors inline-flex items-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed text-red-400/90 hover:text-red-300 hover:bg-red-950/40 border border-red-900/40 hover:border-red-800/60"
                >
                  <LoadingSpinner v-if="deletingUsername === u.username" class="w-3 h-3" />
                  Excluir
                </button>
              </td>
            </tr>
            <tr v-if="filteredUsers.length === 0">
              <td colspan="6" class="px-6 py-10 text-center text-sm text-gray-500">
                {{ users.length === 0 ? 'Nenhum usuário cadastrado.' : 'Nenhum usuário corresponde à busca.' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Confirmação de exclusão -->
    <ConfirmDialog
      v-if="confirmTarget"
      title="Excluir usuário"
      :message="deleteConfirmMessage"
      confirm-label="Excluir"
      type="danger"
      :loading="deletingUsername === confirmTarget.username"
      @cancel="confirmTarget = null"
      @confirm="handleDelete"
    />

  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { createLocalUser, deleteLocalUser, listLocalUsers } from '../api/auth'
import { useAuth } from '../composables/useAuth'
import { useToast } from '../composables/useToast'
import LoadingSpinner from '../components/LoadingSpinner.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'

const { addToast } = useToast()
const { user: currentUser } = useAuth()

const users = ref([])
const loading = ref(true)
const error = ref('')
const searchQuery = ref('')

const showForm = ref(false)
const creating = ref(false)
const formError = ref('')
const form = reactive({
  email: '',
  full_name: '',
  role: 'user',
})

const confirmTarget = ref(null)
const deletingUsername = ref(null)

const filteredUsers = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return users.value
  return users.value.filter((u) => {
    const name = (u.full_name || '').toLowerCase()
    const email = (u.email || '').toLowerCase()
    const username = (u.username || '').toLowerCase()
    return name.includes(q) || email.includes(q) || username.includes(q)
  })
})

const deleteConfirmMessage = computed(() => {
  const t = confirmTarget.value
  if (!t) return ''
  const label = t.full_name || t.username
  return `Remover ${label} (${t.email || t.username}) da plataforma? O usuário deixará de conseguir solicitar magic link. Esta ação não pode ser desfeita.`
})

function isSelf(u) {
  const mine = (currentUser.value?.username || '').toLowerCase()
  return Boolean(mine) && (u.username || '').toLowerCase() === mine
}

function resetForm() {
  form.email = ''
  form.full_name = ''
  form.role = 'user'
  formError.value = ''
  showForm.value = false
}

async function loadUsers() {
  loading.value = true
  error.value = ''
  try {
    const data = await listLocalUsers()
    users.value = data.users
  } catch (err) {
    error.value = err.message || 'Falha ao carregar usuários.'
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  formError.value = ''
  creating.value = true
  try {
    const created = await createLocalUser({
      email: form.email.trim(),
      full_name: form.full_name.trim(),
      role: form.role,
    })
    addToast(`Usuário ${created.full_name} cadastrado. Acesso via magic link.`, 'success')
    resetForm()
    await loadUsers()
  } catch (err) {
    formError.value = err.message || 'Falha ao cadastrar usuário.'
  } finally {
    creating.value = false
  }
}

async function handleDelete() {
  const target = confirmTarget.value
  if (!target || isSelf(target)) return

  deletingUsername.value = target.username
  try {
    await deleteLocalUser(target.username)
    confirmTarget.value = null
    addToast(`Usuário ${target.full_name || target.username} removido.`, 'success')
    await loadUsers()
  } catch (err) {
    addToast(err.message || 'Falha ao excluir usuário.', 'error')
  } finally {
    deletingUsername.value = null
  }
}

onMounted(loadUsers)
</script>
