<template>
  <div class="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden shadow-xl" v-if="user">
    
    <!-- Header Principal -->
    <div class="p-6 md:p-8 border-b border-gray-800 flex flex-col md:flex-row items-center md:items-start gap-6 bg-gradient-to-br from-gray-900 to-gray-950">
      
      <!-- Avatar (Initials/Emoji) -->
      <div class="w-24 h-24 rounded-full bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-900/20 text-4xl border-4 border-gray-800 shrink-0">
        👤
      </div>
      
      <!-- Title Area -->
      <div class="flex-1 text-center md:text-left space-y-1">
        <div class="flex flex-col md:flex-row items-center md:items-center gap-3">
          <h2 class="text-2xl font-bold text-white tracking-tight">{{ user.name }}</h2>
          <span 
            class="px-3 py-1 rounded-full text-xs font-semibold tracking-wide border shadow-sm flex items-center gap-1.5"
            :class="[
              user.state === 'active' 
                ? 'bg-green-900/30 text-green-400 border-green-700/50' 
                : 'bg-red-900/30 text-red-400 border-red-700/50'
            ]"
          >
            <span class="w-1.5 h-1.5 rounded-full block animate-pulse" :class="user.state === 'active' ? 'bg-green-400' : 'bg-red-400'"></span>
            {{ user.state === 'active' ? 'Ativo' : 'Inativo' }}
          </span>
        </div>
        
        <p class="text-gray-400 text-sm font-medium">{{ user.email || user.username }}</p>
        <p class="text-xs text-gray-500 font-mono mt-2 bg-gray-950 px-3 py-1.5 rounded-md inline-block border border-gray-800 break-all select-all">
          {{ user.id }}
        </p>
      </div>
    </div>

    <!-- Details Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-gray-800">
      
      <!-- Esquerda: Identidade Organizacional -->
      <div class="p-6 md:p-8 space-y-6">
        <h3 class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-4 flex items-center gap-2">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V8a2 2 0 00-2-2h-5m-4 0V5a2 2 0 114 0v1m-4 0a2 2 0 104 0m-5 8a2 2 0 100-4 2 2 0 000 4zm0 0c1.306 0 2.417.835 2.83 2M9 14a3.001 3.001 0 00-2.83 2M15 11h3m-3 4h2"></path></svg>
          Identidade
        </h3>
        
        <div class="space-y-4">
          <div>
            <span class="block text-xs text-gray-500 mb-1">Cargo (Title)</span>
            <span class="text-sm font-medium text-gray-200">{{ user.title || 'Não definido' }}</span>
          </div>
          <div>
            <span class="block text-xs text-gray-500 mb-1">Departamento</span>
            <span class="text-sm font-medium text-gray-200">{{ user.department || 'Não definido' }}</span>
          </div>
          <div v-if="user.division">
            <span class="block text-xs text-gray-500 mb-1">Divisão Atual</span>
            <span class="text-sm font-medium px-2 py-1 bg-gray-800 rounded text-gray-300 border border-gray-700">{{ user.division.name || 'Desconhecida' }}</span>
          </div>
        </div>
      </div>

      <!-- Direita: Roles & Grupos -->
      <div class="p-6 md:p-8 flex flex-col gap-8">
        
        <!-- Roles -->
        <div>
          <h3 class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-4 flex items-center gap-2">
            <svg class="w-4 h-4 text-blue-500/70" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path></svg>
            Roles (Perfis Atribuídos)
          </h3>
          <div class="flex flex-wrap gap-2">
            <template v-if="user.authorization?.roles?.length">
              <span 
                v-for="role in user.authorization.roles" 
                :key="role.id"
                class="px-2.5 py-1 rounded-md text-xs font-medium bg-blue-900/20 text-blue-300 border border-blue-800/50 hover:bg-blue-900/40 transition-colors"
                :title="role.id"
              >
                {{ role.name || role.id.substring(0,8) }}
              </span>
            </template>
            <span v-else class="text-sm text-gray-500 italic block mt-1">(Nenhuma role)</span>
          </div>
        </div>

        <!-- Grupos -->
        <div>
          <h3 class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-4 flex items-center gap-2">
            <svg class="w-4 h-4 text-purple-500/70" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path></svg>
            Grupos
          </h3>
          <div class="flex flex-wrap gap-2">
            <template v-if="user.groups?.length">
              <span 
                v-for="group in user.groups" 
                :key="typeof group === 'string' ? group : group.id"
                class="px-2.5 py-1 rounded-md text-xs font-medium bg-purple-900/20 text-purple-300 border border-purple-800/50 hover:bg-purple-900/40 transition-colors"
                :title="typeof group === 'string' ? group : group.id"
              >
                {{ (typeof group === 'string' ? group.substring(0,8) : (group.name || group.id.substring(0,8))) }}
              </span>
            </template>
            <span v-else class="text-sm text-gray-500 italic block mt-1">(Nenhum grupo)</span>
          </div>
        </div>
        
      </div>
    </div>

    <!-- Filas Block -->
    <div class="border-t border-gray-800">
      <div 
        class="flex flex-col sm:flex-row items-start sm:items-center justify-between p-6 md:px-8 py-5 cursor-pointer bg-gray-950/30 hover:bg-gray-800/50 transition-colors"
        @click="queuesExpanded = !queuesExpanded"
      >
          <div class="flex items-center gap-3 w-full">
            <div class="p-2 rounded-lg bg-gray-900 border border-gray-700 shadow-sm">
              <svg class="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16"></path></svg>
            </div>
            <div class="flex-1">
              <h3 class="text-sm font-semibold text-gray-200">
                Filas Configuradas na Plataforma (<span :class="queues.length > 0 ? 'text-blue-400' : 'text-gray-500'">{{ queues.length }}</span>)
              </h3>
              <p v-if="loading" class="text-xs text-blue-400 mt-0.5 animate-pulse">Carregando filas do back-end...</p>
              <p v-else class="text-xs text-gray-500 mt-0.5">Gestão individual de participações</p>
            </div>
          </div>
          
          <div class="mt-4 sm:mt-0 p-2 transform transition-transform duration-200 text-gray-400" :class="queuesExpanded ? 'rotate-180' : ''">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
          </div>
        </div>

        <!-- Tabela Interna expansível -->
        <div v-show="queuesExpanded">
          <div class="border-t border-gray-800" v-if="queues.length > 0">
            <div class="max-h-64 overflow-y-auto">
              <table class="min-w-full divide-y divide-gray-800/50">
                <thead class="bg-gray-950/80 sticky top-0 z-10 backdrop-blur-sm">
                  <tr>
                    <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 tracking-wider">Nome da Fila</th>
                    <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 tracking-wider">Status</th>
                    <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 tracking-wider">System ID (UUID)</th>
                    <th scope="col" class="px-6 py-3 text-right text-xs font-medium text-gray-500 tracking-wider">Ação</th>
                  </tr>
                </thead>
                <tbody class="bg-transparent divide-y divide-gray-800/30">
                  <tr v-for="q in queues" :key="q.id" class="hover:bg-gray-800/30 transition-colors group">
                    <td class="px-6 py-3 whitespace-nowrap text-sm font-medium text-indigo-100">
                      {{ q.name }}
                    </td>
                    <td class="px-6 py-3 whitespace-nowrap">
                      <span 
                        class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-xs font-medium border"
                        :class="q.joined 
                          ? 'bg-green-900/20 text-green-400 border-green-800/50' 
                          : 'bg-gray-800 text-gray-400 border-gray-700'"
                      >
                        <span class="w-1.5 h-1.5 rounded-full" :class="q.joined ? 'bg-green-400' : 'bg-gray-500'"></span>
                        {{ q.joined ? 'Ativo' : 'Inativo' }}
                      </span>
                    </td>
                    <td class="px-6 py-3 whitespace-nowrap text-xs text-gray-500 font-mono text-ellipsis overflow-hidden max-w-[150px]">
                      {{ q.id }}
                    </td>
                    <td class="px-6 py-3 whitespace-nowrap text-right">
                      <button
                        @click.stop="$emit('remove-from-queue', q)"
                        class="inline-flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-red-400 bg-red-900/20 border border-red-800/40 rounded-md hover:bg-red-900/40 transition-all"
                        title="Remover desta fila"
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
        <div v-else-if="!loading" class="p-8 text-center text-gray-500 text-sm border-t border-gray-800 flex flex-col items-center gap-3">
          <svg class="w-8 h-8 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
          Usuário não está configurado em nenhuma fila da Plataforma.
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  user: {
    type: Object,
    default: null
  },
  queues: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  }
})

defineEmits(['remove-from-queue'])

const queuesExpanded = ref(true)
</script>
