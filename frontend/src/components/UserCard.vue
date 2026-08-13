<template>
  <div class="card overflow-hidden p-6 md:p-8" v-if="user">
    <div class="flex flex-col items-center text-center space-y-3">
      <div class="w-24 h-24 rounded-full bg-brand-soft flex items-center justify-center shrink-0">
        <svg class="w-12 h-12 text-brand" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
        </svg>
      </div>

      <div class="space-y-2">
        <h2 class="text-2xl font-bold text-ink tracking-tight">{{ user.name }}</h2>
        <span
          class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold tracking-wide"
          :class="user.state === 'active'
            ? 'bg-green-50 text-green-700'
            : 'bg-red-50 text-red-700'"
        >
          <span
            class="w-1.5 h-1.5 rounded-full"
            :class="user.state === 'active' ? 'bg-green-500' : 'bg-red-500'"
          />
          {{ user.state === 'active' ? 'Ativo' : 'Inativo' }}
        </span>
      </div>

      <p class="text-gray-500 text-sm font-medium break-all">{{ user.email || user.username }}</p>
      <p class="text-xs text-gray-500 font-mono bg-ice px-3 py-1.5 rounded-full inline-block break-all select-all max-w-full">
        {{ user.id }}
      </p>
    </div>

    <div class="mt-8 pt-6 border-t border-gray-100 space-y-5">
      <h3 class="text-xs font-bold text-gray-400 uppercase tracking-wider flex items-center gap-2">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V8a2 2 0 00-2-2h-5m-4 0V5a2 2 0 114 0v1m-4 0a2 2 0 104 0m-5 8a2 2 0 100-4 2 2 0 000 4zm0 0c1.306 0 2.417.835 2.83 2M9 14a3.001 3.001 0 00-2.83 2M15 11h3m-3 4h2" />
        </svg>
        Identidade
      </h3>

      <div class="space-y-4 text-left">
        <div>
          <span class="block text-xs text-gray-400 mb-1">Cargo (Title)</span>
          <span class="text-sm font-semibold text-ink">{{ user.title || 'Não definido' }}</span>
        </div>
        <div>
          <span class="block text-xs text-gray-400 mb-1">Departamento</span>
          <span class="text-sm font-semibold text-ink">{{ user.department || 'Não definido' }}</span>
        </div>
        <div v-if="user.division">
          <span class="block text-xs text-gray-400 mb-1">Divisão Atual</span>
          <span class="text-sm font-medium px-2 py-1 bg-gray-50 rounded-lg text-ink border border-gray-100">
            {{ user.division.name || 'Desconhecida' }}
          </span>
        </div>
      </div>

      <div>
        <h3 class="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Roles</h3>
        <div class="flex flex-wrap gap-2">
          <template v-if="user.authorization?.roles?.length">
            <span
              v-for="role in user.authorization.roles"
              :key="role.id"
              class="px-2.5 py-1 rounded-full text-xs font-medium bg-brand-soft text-brand border border-brand/15"
              :title="role.id"
            >
              {{ role.name || role.id.substring(0, 8) }}
            </span>
          </template>
          <span v-else class="text-sm text-gray-400 italic">(Nenhuma role)</span>
        </div>
      </div>

      <div>
        <h3 class="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Grupos</h3>
        <div class="flex flex-wrap gap-2">
          <template v-if="user.groups?.length">
            <span
              v-for="group in user.groups"
              :key="typeof group === 'string' ? group : group.id"
              class="px-2.5 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-800 border border-amber-200"
              :title="typeof group === 'string' ? group : group.id"
            >
              {{ (typeof group === 'string' ? group.substring(0, 8) : (group.name || group.id.substring(0, 8))) }}
            </span>
          </template>
          <span v-else class="text-sm text-gray-400 italic">(Nenhum grupo)</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  user: {
    type: Object,
    default: null
  }
})
</script>
