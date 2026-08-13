<template>
  <div class="min-h-screen flex items-center justify-center p-6 bg-canvas selection:bg-brand/20">

    <!-- Card de Login -->
    <div class="w-full max-w-md card rounded-3xl p-8 md:p-10">

      <!-- Cabeçalho -->
      <div class="text-center mb-10">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-brand-soft mb-4">
          <BrandMark class="w-9 h-9" />
        </div>
        <h1 class="text-2xl font-bold text-ink tracking-tight">Genesys Manager</h1>
        <p class="text-sm text-gray-400 mt-1">sae1.pure.cloud</p>
      </div>

      <!-- Auto-login do magic link (POST consome o token; GET só redireciona) -->
      <div v-if="autoLoggingIn" class="text-center space-y-4">
        <div class="inline-flex items-center justify-center w-14 h-14 rounded-full bg-brand-soft mb-2">
          <svg class="animate-spin h-7 w-7 text-brand" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        </div>
        <h2 class="text-lg font-semibold text-ink">Entrando…</h2>
        <p class="text-sm text-gray-500 leading-relaxed">
          Validando seu link de acesso. Aguarde um instante.
        </p>
      </div>

      <!-- Estado de sucesso: verifique seu e-mail -->
      <div v-else-if="sent" class="text-center space-y-4">
        <div class="inline-flex items-center justify-center w-14 h-14 rounded-full bg-green-50 border border-green-200 mb-2">
          <svg class="w-7 h-7 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
        </div>
        <h2 class="text-lg font-semibold text-ink">Verifique seu e-mail</h2>
        <p class="text-sm text-gray-500 leading-relaxed">
          Se o endereço for válido, enviamos um link de acesso para
          <span class="text-ink font-medium">{{ email }}</span>.
          O link é válido por <span class="text-ink font-medium">10 minutos</span>.
        </p>
        <button
          type="button"
          @click="resetForm"
          class="mt-4 text-sm text-brand hover:text-brand-hover transition-colors font-medium"
        >
          Usar outro e-mail
        </button>
      </div>

      <!-- Formulário -->
      <form v-else @submit.prevent="handleSubmit" class="space-y-6">
        <div>
          <label for="email" class="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">E-mail</label>
          <input
            id="email"
            v-model="email"
            type="email"
            required
            autocomplete="email"
            placeholder="seu.nome@claro.com.br"
            class="input"
          />
          <p class="mt-2 text-xs text-gray-400">Use um e-mail corporativo <span class="text-gray-500">@claro.com.br</span></p>
        </div>

        <!-- Erro -->
        <div v-if="error" class="bg-red-50 border border-red-200 rounded-xl p-3 flex items-center gap-2 text-sm text-red-700">
          <svg class="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {{ error }}
        </div>

        <button
          type="submit"
          :disabled="loading"
          class="btn-primary w-full py-3.5 group"
        >
          <svg v-if="loading" class="animate-spin h-5 w-5 text-current" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <template v-else>
            <span>Enviar link de acesso</span>
            <svg class="w-4 h-4 group-hover:translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </template>
        </button>
      </form>

      <div class="mt-8 pt-6 border-t border-gray-100 flex justify-center text-[10px] text-gray-400 uppercase tracking-widest font-bold">
        Secure Access — Internal Use Only
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { requestLoginLink, confirmMagicLink } from '../api/auth'
import { useAuth } from '../composables/useAuth'
import BrandMark from '../components/BrandMark.vue'

const ALLOWED_DOMAIN = '@claro.com.br'
const INVALID_LINK_MSG =
  'Link inválido, expirado ou já utilizado. Solicite um novo acesso.'

const route = useRoute()
const router = useRouter()
const { checkAuth } = useAuth()

const email = ref('')
const loading = ref(false)
const error = ref('')
const sent = ref(false)
const autoLoggingIn = ref(false)

function isAllowedEmail(value) {
  return value.trim().toLowerCase().endsWith(ALLOWED_DOMAIN)
}

function resetForm() {
  sent.value = false
  error.value = ''
  loading.value = false
}

async function completeMagicLinkLogin(token) {
  autoLoggingIn.value = true
  error.value = ''

  try {
    await confirmMagicLink(token)
    await checkAuth()
    await router.replace({ name: 'Home' })
  } catch (err) {
    autoLoggingIn.value = false
    error.value =
      typeof err.message === 'string' && err.message
        ? err.message
        : INVALID_LINK_MSG
    // Token usado/expirado: limpa query e mostra formulário com erro
    await router.replace({ name: 'Login', query: { error: 'invalid_link' } })
  }
}

onMounted(() => {
  const qError = route.query.error
  const qToken = route.query.token

  if (typeof qError === 'string' && qError) {
    error.value = INVALID_LINK_MSG
  }

  if (typeof qToken === 'string' && qToken.trim()) {
    completeMagicLinkLogin(qToken.trim())
  }
})

async function handleSubmit() {
  loading.value = true
  error.value = ''

  const trimmed = email.value.trim()

  if (!isAllowedEmail(trimmed)) {
    error.value = 'O e-mail deve terminar com @claro.com.br'
    loading.value = false
    return
  }

  try {
    await requestLoginLink(trimmed)
    email.value = trimmed
    sent.value = true
  } catch (err) {
    if (err.status === 400 || err.status === 422) {
      const detail = err.message
      error.value = typeof detail === 'string' && detail !== 'Falha na autenticação'
        ? detail
        : 'E-mail inválido. Use um endereço @claro.com.br'
    } else if (err.status === 429) {
      error.value = 'Muitas tentativas. Aguarde um momento e tente novamente.'
    } else if (err.status >= 500) {
      const detail = err.message
      error.value = typeof detail === 'string' && detail !== 'Falha na autenticação'
        ? detail
        : 'Erro no servidor. Tente novamente em instantes.'
    } else {
      error.value = 'Erro de conexão com o servidor'
    }
    console.error('Erro ao solicitar link de acesso:', err)
  } finally {
    loading.value = false
  }
}
</script>
