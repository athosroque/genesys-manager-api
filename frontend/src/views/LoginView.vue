<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-950 p-6 selection:bg-blue-500/30">
    
    <!-- Card de Login -->
    <div class="w-full max-w-md bg-gray-900 border border-gray-800 rounded-2xl p-8 shadow-2xl shadow-black/50">
      
      <!-- Cabeçalho -->
      <div class="text-center mb-10">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-blue-600/10 border border-blue-500/20 mb-4">
          <span class="text-4xl">🔷</span>
        </div>
        <h1 class="text-2xl font-bold text-white tracking-tight">Genesys Manager</h1>
        <p class="text-sm text-gray-500 mt-1 font-mono">sae1.pure.cloud</p>
      </div>

      <!-- Formulário -->
      <form @submit.prevent="handleLogin" class="space-y-6">
        <div>
          <label for="username" class="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Usuário</label>
          <input
            id="username"
            v-model="username"
            type="text"
            required
            placeholder="seu.nome"
            class="w-full bg-gray-800 border border-gray-700 text-gray-100 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all placeholder:text-gray-600"
          />
        </div>

        <div>
          <label for="password" class="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Senha</label>
          <input
            id="password"
            v-model="password"
            type="password"
            required
            placeholder="••••••••"
            class="w-full bg-gray-800 border border-gray-700 text-gray-100 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all placeholder:text-gray-600"
          />
        </div>

        <!-- Erro -->
        <div v-if="error" class="bg-red-900/10 border border-red-900/30 rounded-lg p-3 flex items-center gap-2 text-sm text-red-400 animate-in fade-in slide-in-from-top-1">
          <svg class="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {{ error }}
        </div>

        <button
          type="submit"
          :disabled="loading"
          class="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-gray-800 disabled:text-gray-600 text-white font-bold py-3.5 rounded-xl transition-all shadow-lg shadow-blue-900/20 flex items-center justify-center gap-2 group"
        >
          <svg v-if="loading" class="animate-spin h-5 w-5 text-current" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span v-else>{{ loading ? 'Validando...' : 'Entrar na Plataforma' }}</span>
          <svg v-if="!loading" class="w-4 h-4 group-hover:translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6" />
          </svg>
        </button>
      </form>

      <div class="mt-8 pt-6 border-t border-gray-800 flex justify-center text-[10px] text-gray-600 uppercase tracking-widest font-bold">
        Secure Access — Internal Use Only
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { login } from '../api/auth'

const router = useRouter()
const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function handleLogin() {
  loading.value = true
  error.value = ''
  
  try {
    const data = await login(username.value, password.value)
    // Sucesso redireciona para a home
    router.push('/')
  } catch (err) {
    if (err.status === 401) {
      error.value = 'Usuário ou senha incorretos'
    } else {
      error.value = 'Erro de conexão com o servidor'
    }
    console.error('Erro de login:', err)
  } finally {
    loading.value = false
  }
}
</script>
