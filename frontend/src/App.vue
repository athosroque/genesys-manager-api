<template>
  <div class="min-h-screen font-sans text-ink bg-canvas">

    <!-- Spinner inicial enquanto valida sessão -->
    <div
      v-if="loading"
      class="fixed inset-0 z-50 flex flex-col items-center justify-center bg-white/90 gap-4"
    >
      <LoadingSpinner class="w-12 h-12 text-brand" />
      <p class="text-sm text-gray-500 animate-pulse">Autenticando...</p>
    </div>

    <!-- Tela de Login (rota /login) -->
    <main v-else-if="route.name === 'Login'">
      <RouterView />
    </main>

    <!-- Shell autenticado (demais rotas) -->
    <template v-else-if="isAuthenticated">
      <!-- Overlay mobile -->
      <div
        v-if="sidebarOpen"
        class="fixed inset-0 z-40 bg-ink/25 lg:hidden"
        @click="sidebarOpen = false"
      />

      <!-- Sidebar -->
      <aside
        class="fixed inset-y-0 left-0 z-50 w-64 bg-sidebar flex flex-col transition-transform duration-200
               lg:translate-x-0"
        :class="sidebarOpen ? 'translate-x-0' : '-translate-x-full'"
      >
        <RouterLink
          to="/"
          class="flex items-center gap-3 px-5 py-6 shrink-0"
          @click="sidebarOpen = false"
        >
          <BrandMark class="w-8 h-8" />
          <div class="min-w-0">
            <p class="font-bold text-ink tracking-tight leading-tight truncate">Genesys Manager</p>
            <p class="text-[11px] text-gray-400 mt-0.5">Management Platform</p>
          </div>
        </RouterLink>

        <nav class="flex-1 px-3 space-y-1 overflow-y-auto">
          <RouterLink
            to="/"
            class="sidebar-link"
            :class="{ 'sidebar-link-active': isActive('/') }"
            @click="sidebarOpen = false"
          >
            <svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M4 5h7v7H4V5zm9 0h7v4h-7V5zM4 14h7v5H4v-5zm9 6V11h7v9h-7z" />
            </svg>
            Dashboard
          </RouterLink>

          <RouterLink
            to="/consulta"
            class="sidebar-link"
            :class="{ 'sidebar-link-active': isActive('/consulta') }"
            @click="sidebarOpen = false"
          >
            <svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            Consulta
          </RouterLink>

          <RouterLink
            to="/auditoria"
            class="sidebar-link"
            :class="{ 'sidebar-link-active': isActive('/auditoria') }"
            @click="sidebarOpen = false"
          >
            <svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Auditoria
          </RouterLink>

          <RouterLink
            v-if="isAdmin"
            to="/admin/usuarios"
            class="sidebar-link"
            :class="{ 'sidebar-link-active': isActive('/admin/usuarios') }"
            @click="sidebarOpen = false"
          >
            <svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            Usuários
          </RouterLink>
        </nav>

        <div class="px-3 pb-6 pt-3 space-y-1 shrink-0">
          <RouterLink
            v-if="isAdmin"
            to="/admin/usuarios"
            class="btn-primary w-full mb-3"
            @click="sidebarOpen = false"
          >
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
            Novo Cadastro
          </RouterLink>

          <button
            type="button"
            class="sidebar-foot-link"
            title="Em breve"
          >
            <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            Configurações
          </button>

          <button
            type="button"
            class="sidebar-foot-link"
            title="Em breve"
          >
            <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Suporte
          </button>
        </div>
      </aside>

      <!-- Coluna principal -->
      <div class="lg:pl-64 min-h-screen flex flex-col">
        <header class="sticky top-0 z-30 h-16 bg-white border-b border-black/[0.06] flex items-center gap-3 px-4 sm:px-6">
          <button
            type="button"
            class="lg:hidden p-2 -ml-1 rounded-xl text-gray-500 hover:bg-gray-50 hover:text-ink"
            aria-label="Abrir menu"
            @click="sidebarOpen = true"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>

          <nav class="flex-1 flex items-center gap-5 min-w-0 overflow-x-auto">
            <RouterLink
              to="/consulta"
              class="top-tab whitespace-nowrap"
              :class="{ 'top-tab-active': isActive('/consulta') }"
            >
              Consulta
            </RouterLink>
            <RouterLink
              to="/auditoria"
              class="top-tab whitespace-nowrap"
              :class="{ 'top-tab-active': isActive('/auditoria') }"
            >
              Auditoria
            </RouterLink>
            <RouterLink
              v-if="isAdmin"
              to="/admin/usuarios"
              class="top-tab whitespace-nowrap"
              :class="{ 'top-tab-active': isActive('/admin/usuarios') }"
            >
              Usuários
            </RouterLink>
          </nav>

          <div class="flex items-center gap-2 sm:gap-3 shrink-0">
            <div
              class="w-9 h-9 rounded-full bg-brand-soft border border-brand/15 flex items-center justify-center text-ink font-bold text-xs uppercase"
              :title="user?.full_name || user?.username"
            >
              {{ initials }}
            </div>
            <button
              type="button"
              @click="logout"
              title="Sair"
              class="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-full transition-all"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
            </button>
          </div>
        </header>

        <main class="flex-1 px-4 sm:px-6 lg:px-8 py-6 md:py-8">
          <div class="max-w-6xl mx-auto">
            <RouterView v-slot="{ Component }">
              <KeepAlive :include="['DashboardView', 'ConsultaView', 'AuditView']">
                <component :is="Component" />
              </KeepAlive>
            </RouterView>
          </div>
        </main>
      </div>
    </template>

    <ToastContainer />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { useAuth } from './composables/useAuth'
import BrandMark from './components/BrandMark.vue'
import LoadingSpinner from './components/LoadingSpinner.vue'
import ToastContainer from './components/ToastContainer.vue'

const { user, isAuthenticated, loading, checkAuth, logout } = useAuth()
const route = useRoute()
const sidebarOpen = ref(false)

const isAdmin = computed(() => user.value?.role === 'admin')

const initials = computed(() => {
  const name = (user.value?.full_name || user.value?.username || '').trim()
  if (!name) return '??'
  const parts = name.split(/\s+/).filter(Boolean)
  if (parts.length >= 2) {
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
  }
  return name.slice(0, 2).toUpperCase()
})

function isActive(path) {
  if (path === '/') return route.path === '/'
  return route.path === path || route.path.startsWith(`${path}/`)
}

watch(() => route.path, () => {
  sidebarOpen.value = false
})

onMounted(async () => {
  if (user.value === null && route.name !== 'Login') {
    await checkAuth()
  }
})
</script>

<style>
body, html {
  margin: 0;
  padding: 0;
  min-height: 100%;
}
</style>
