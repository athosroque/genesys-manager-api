<template>
  <div class="flex h-screen bg-gray-950 font-sans text-gray-100 overflow-hidden">
    
    <!-- Spinner Inicial enquanto valida sessão -->
    <div v-if="loading" class="fixed inset-0 z-50 flex flex-col items-center justify-center bg-gray-950 gap-4">
       <LoadingSpinner class="w-12 h-12 text-blue-500" />
       <p class="text-sm text-gray-400 font-mono animate-pulse">Autenticando...</p>
    </div>

    <!-- Sidebar Fixa (Apenas Logado) -->
    <aside v-if="isAuthenticated" class="w-64 bg-gray-900 border-r border-gray-800 flex flex-col z-10 shrink-0">
      <div class="p-6 border-b border-gray-800">
        <h1 class="text-xl font-bold tracking-tight text-white flex items-center gap-2">
          <span class="text-blue-500 text-2xl">⚡</span>
          Genesys Manager
        </h1>
        <p class="text-xs text-gray-400 mt-1 font-mono">sae1.pure.cloud</p>
      </div>

      <nav class="flex-1 p-4 space-y-2 overflow-y-auto">
        <RouterLink 
          to="/" 
          class="flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors"
          :class="[
            $route.path === '/' 
              ? 'bg-blue-600/10 text-blue-400' 
              : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
          ]"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
          Consulta e Ações
        </RouterLink>
      </nav>

      <!-- Perfil e Logout -->
      <div class="mt-auto border-t border-gray-800 bg-gray-950/30">
        <div class="p-4 flex items-center gap-3">
          <div class="w-8 h-8 rounded-full bg-blue-600/10 border border-blue-500/30 flex items-center justify-center text-blue-400 font-bold text-xs uppercase">
            {{ user?.username?.substring(0, 2) || '??' }}
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-[11px] font-bold text-gray-200 truncate">{{ user?.full_name || 'Desconhecido' }}</p>
            <p class="text-[10px] text-gray-500 uppercase tracking-tighter">{{ user?.role || 'User' }}</p>
          </div>
          <button 
            @click="logout" 
            title="Sair"
            class="p-2 text-gray-500 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-all"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" /></svg>
          </button>
        </div>
        <div class="px-4 pb-4 text-[9px] text-gray-700 text-center uppercase tracking-widest font-mono">
          v1.0.0 — Genesys Manager
        </div>
      </div>
    </aside>

    <!-- Área Principal -->
    <main class="flex-1 relative overflow-hidden flex flex-col">
      <div class="h-full overflow-y-auto p-4 md:p-8">
        <RouterView />
      </div>
    </main>

    <ToastContainer />
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter, RouterLink, RouterView } from 'vue-router'
import { useAuth } from './composables/useAuth'
import LoadingSpinner from './components/LoadingSpinner.vue'
import ToastContainer from './components/ToastContainer.vue'

const { user, isAuthenticated, loading, checkAuth, logout } = useAuth()

onMounted(async () => {
  await checkAuth()
})
</script>

<style>
/* Remove margin base do vue original setupado pelo Vite */
body, html {
  margin: 0;
  padding: 0;
  height: 100%;
}
</style>
