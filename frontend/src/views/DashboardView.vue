<template>
  <div class="space-y-8">
    <!-- Hero -->
    <section class="card rounded-3xl p-8 md:p-12">
      <div class="max-w-xl">
        <div class="flex items-center gap-3 mb-4">
          <BrandMark class="w-10 h-10" />
          <h1 class="text-3xl md:text-4xl font-bold text-ink tracking-tight">Genesys Manager</h1>
        </div>
        <p class="text-lg font-semibold text-ink mb-2">{{ greeting }}, {{ firstName }}.</p>
        <p class="text-gray-500 leading-relaxed mb-8">
          Consulte usuários da Genesys Cloud, execute ações operacionais e acompanhe
          a trilha de auditoria — tudo em um só lugar.
        </p>
        <RouterLink to="/consulta" class="btn-primary">
          Consultar usuário
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6" />
          </svg>
        </RouterLink>
      </div>
    </section>

    <!-- Cards de módulo -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
      <RouterLink
        to="/consulta"
        class="card p-6 hover:shadow-md hover:-translate-y-0.5 transition-all group"
      >
        <div class="w-11 h-11 rounded-full bg-brand-soft flex items-center justify-center mb-4">
          <svg class="w-5 h-5 text-brand" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
        <h2 class="text-lg font-semibold text-ink mb-1 group-hover:text-brand transition-colors">Consulta</h2>
        <p class="text-sm text-gray-500 leading-relaxed">
          Busque por matrícula, e-mail ou UUID e execute ações na plataforma.
        </p>
      </RouterLink>

      <RouterLink
        to="/auditoria"
        class="card p-6 hover:shadow-md hover:-translate-y-0.5 transition-all group"
      >
        <div class="w-11 h-11 rounded-full bg-brand-soft flex items-center justify-center mb-4">
          <svg class="w-5 h-5 text-brand" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <h2 class="text-lg font-semibold text-ink mb-1 group-hover:text-brand transition-colors">Auditoria</h2>
        <p class="text-sm text-gray-500 leading-relaxed">
          Trilha de alterações de divisão, filas, roles e grupos.
        </p>
      </RouterLink>
    </div>

    <!-- Visão Geral -->
    <section>
      <h2 class="text-lg font-semibold text-ink mb-4">Visão Geral</h2>
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div class="card p-5 flex items-start justify-between gap-3">
          <div>
            <p class="text-[11px] font-bold uppercase tracking-wider text-gray-400">Usuários ativos</p>
            <p class="text-2xl font-bold text-ink mt-1 tabular-nums">—</p>
            <p class="text-xs text-gray-400 mt-1">em breve</p>
          </div>
          <div class="w-10 h-10 rounded-full bg-ice flex items-center justify-center shrink-0">
            <svg class="w-5 h-5 text-sky-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </div>
        </div>

        <div class="card p-5 flex items-start justify-between gap-3">
          <div>
            <p class="text-[11px] font-bold uppercase tracking-wider text-gray-400">Ações hoje</p>
            <p class="text-2xl font-bold text-ink mt-1 tabular-nums">—</p>
            <p class="text-xs text-gray-400 mt-1">em breve</p>
          </div>
          <div class="w-10 h-10 rounded-full bg-brand-soft flex items-center justify-center shrink-0">
            <svg class="w-5 h-5 text-brand" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
        </div>

        <div class="card p-5 flex items-start justify-between gap-3">
          <div>
            <p class="text-[11px] font-bold uppercase tracking-wider text-gray-400">Status plataforma</p>
            <p class="text-xl font-bold text-ink mt-1 flex items-center gap-2">
              <span class="w-2.5 h-2.5 rounded-full bg-brand" />
              Operacional
            </p>
            <p class="text-xs text-gray-400 mt-1">Sessão {{ sessionRole }}</p>
          </div>
          <div class="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center shrink-0">
            <svg class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
            </svg>
          </div>
        </div>
      </div>
    </section>

    <!-- Atividades recentes — empty state honesto (sem backend de feed) -->
    <section>
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold text-ink">Atividades Recentes</h2>
        <RouterLink to="/auditoria" class="text-sm font-medium text-brand hover:text-brand-hover">
          Ver todas
        </RouterLink>
      </div>
      <div class="card p-8 text-center">
        <p class="text-sm text-gray-500">
          Nenhuma atividade recente nesta sessão. Use a
          <RouterLink to="/auditoria" class="text-brand font-medium hover:text-brand-hover">auditoria</RouterLink>
          para consultar o histórico.
        </p>
      </div>
    </section>
  </div>
</template>

<script>
export default { name: 'DashboardView' }
</script>

<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useAuth } from '../composables/useAuth'
import BrandMark from '../components/BrandMark.vue'

const { user } = useAuth()

const firstName = computed(() => {
  const name = (user.value?.full_name || user.value?.username || 'operador').trim()
  return name.split(/\s+/)[0]
})

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 12) return 'Bom dia'
  if (h < 18) return 'Boa tarde'
  return 'Boa noite'
})

const sessionRole = computed(() => user.value?.role || 'ativa')
</script>
