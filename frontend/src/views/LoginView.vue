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

      <!-- Tela de recuperação de códigos (após setup bem-sucedido) -->
      <div v-if="recoveryCodesScreen" class="text-center space-y-6">
        <div class="inline-flex items-center justify-center w-14 h-14 rounded-full bg-green-50 border border-green-200 mb-2">
          <svg class="w-7 h-7 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <div>
          <h2 class="text-lg font-semibold text-ink">Seus códigos de recuperação</h2>
          <p class="text-sm text-gray-500 mt-2 leading-relaxed">
            Guarde estes 10 códigos em local seguro. Se perder acesso ao seu autenticador, poderá usar um código para entrar.
          </p>
        </div>

        <!-- Grid de códigos -->
        <div class="bg-gray-50 border border-gray-200 rounded-xl p-6 space-y-3 text-left">
          <div v-for="(code, idx) in recoveryCodes" :key="idx" class="flex items-center justify-between font-mono text-sm">
            <span class="text-gray-400">{{ idx + 1 }}.</span>
            <span class="text-ink flex-1 ml-3 tracking-widest">{{ code }}</span>
            <button
              type="button"
              @click="copyRecoveryCode(idx)"
              title="Copiar"
              class="text-gray-400 hover:text-brand transition-colors ml-3"
            >
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
            </button>
          </div>
        </div>

        <!-- Botões de ação -->
        <div class="flex flex-col sm:flex-row gap-3 pt-2">
          <button
            type="button"
            @click="downloadRecoveryCodes"
            class="btn-secondary flex items-center justify-center gap-2"
          >
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Baixar
          </button>
          <label class="flex-1 flex items-center gap-2 cursor-pointer px-3 py-2 text-sm font-medium text-gray-600 hover:text-ink transition-colors">
            <input
              type="checkbox"
              v-model="recoveryCodesSaved"
              class="rounded border border-gray-300"
            />
            Salvei meus códigos
          </label>
        </div>

        <!-- Botão continuar (disabled até não marcar) -->
        <button
          type="button"
          @click="handleRecoveryCodesSaved"
          :disabled="!recoveryCodesSaved"
          class="btn-primary w-full py-3.5 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Continuar
        </button>

        <div v-if="error" class="bg-red-50 border border-red-200 rounded-xl p-3 flex items-center gap-2 text-sm text-red-700 mt-4">
          <svg class="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {{ error }}
        </div>
      </div>

      <!-- Tela de setup de TOTP (QR + confirmação) -->
      <div v-else-if="twoFaStatus === 'totp_setup_required' && !recoveryCodesScreen" class="text-center space-y-6">
        <div>
          <h2 class="text-lg font-semibold text-ink">Configure autenticação em duas etapas</h2>
          <p class="text-sm text-gray-500 mt-2">
            Escaneie o código QR com seu autenticador (Google, Microsoft, Authy, etc).
          </p>
        </div>

        <!-- QR Code -->
        <div v-if="qrCodeDataUrl" class="flex justify-center p-4 bg-white rounded-lg border border-gray-200">
          <img :src="qrCodeDataUrl" alt="QR Code para TOTP" class="w-48 h-48" />
        </div>

        <!-- Segredo manual -->
        <div class="bg-gray-50 border border-gray-200 rounded-xl p-4">
          <p class="text-xs text-gray-500 uppercase tracking-wider mb-2">Ou digite manualmente:</p>
          <p class="font-mono text-sm text-ink tracking-widest break-all">{{ totpSecret }}</p>
        </div>

        <!-- Confirmação de código -->
        <div>
          <label for="confirm-code" class="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
            Digite o código de 6 dígitos do seu autenticador
          </label>
          <input
            id="confirm-code"
            v-model="confirmSetupCode"
            type="text"
            inputmode="numeric"
            autocomplete="one-time-code"
            placeholder="000000"
            maxlength="6"
            class="input text-center text-2xl tracking-widest"
            autofocus
          />
        </div>

        <button
          type="button"
          @click="handleConfirmTotpSetup"
          :disabled="totpLoading || confirmSetupCode.length !== 6"
          class="btn-primary w-full py-3.5 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <svg v-if="totpLoading" class="animate-spin h-5 w-5 text-current" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span v-else>Confirmar</span>
        </button>

        <div v-if="error" class="bg-red-50 border border-red-200 rounded-xl p-3 flex items-center gap-2 text-sm text-red-700">
          <svg class="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {{ error }}
        </div>
      </div>

      <!-- Tela de verificação de TOTP (usuário já tem 2FA ativo) -->
      <div v-else-if="twoFaStatus === 'totp_required'" class="text-center space-y-6">
        <div>
          <h2 class="text-lg font-semibold text-ink">Digite seu código de autenticação</h2>
          <p class="text-sm text-gray-500 mt-2">
            Verifique no seu autenticador (Google, Microsoft, Authy, etc).
          </p>
        </div>

        <!-- Seletor de tipo de código -->
        <div v-if="!useRecoveryCode" class="space-y-4">
          <div>
            <label for="totp-code" class="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              Código de 6 dígitos
            </label>
            <input
              id="totp-code"
              v-model="totpCode"
              type="text"
              inputmode="numeric"
              autocomplete="one-time-code"
              placeholder="000000"
              maxlength="6"
              class="input text-center text-2xl tracking-widest"
              autofocus
            />
          </div>

          <button
            type="button"
            @click="handleVerifyTotp"
            :disabled="totpLoading || totpCode.length !== 6"
            class="btn-primary w-full py-3.5 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg v-if="totpLoading" class="animate-spin h-5 w-5 text-current" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span v-else>Verificar</span>
          </button>

          <button
            type="button"
            @click="useRecoveryCode = true"
            class="text-sm text-brand hover:text-brand-hover transition-colors font-medium w-full"
          >
            Usar código de recuperação
          </button>
        </div>

        <!-- Campo de código de recuperação -->
        <div v-else class="space-y-4">
          <div>
            <label for="recovery-code" class="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              Código de recuperação
            </label>
            <input
              id="recovery-code"
              v-model="recoveryCode"
              type="text"
              placeholder="XXXX-XXXX-XXXX"
              class="input"
              autofocus
            />
          </div>

          <button
            type="button"
            @click="handleVerifyTotp"
            :disabled="totpLoading || !recoveryCode.trim()"
            class="btn-primary w-full py-3.5 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg v-if="totpLoading" class="animate-spin h-5 w-5 text-current" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span v-else>Verificar</span>
          </button>

          <button
            type="button"
            @click="useRecoveryCode = false"
            class="text-sm text-brand hover:text-brand-hover transition-colors font-medium w-full"
          >
            Voltar ao código de autenticação
          </button>
        </div>

        <div v-if="error" class="bg-red-50 border border-red-200 rounded-xl p-3 flex items-center gap-2 text-sm text-red-700">
          <svg class="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {{ error }}
        </div>
      </div>

      <!-- Auto-login do magic link (POST consome o token; GET só redireciona) -->
      <div v-else-if="autoLoggingIn" class="text-center space-y-4">
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
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { requestLoginLink, confirmMagicLink, setupTotp, confirmTotpSetup, verifyTotp } from '../api/auth'
import { useAuth } from '../composables/useAuth'
import BrandMark from '../components/BrandMark.vue'
import QRCode from 'qrcode'

const ALLOWED_DOMAIN = '@claro.com.br'
const INVALID_LINK_MSG =
  'Link inválido, expirado ou já utilizado. Solicite um novo acesso.'

const route = useRoute()
const router = useRouter()
const { checkAuth, setUser } = useAuth()

const email = ref('')
const loading = ref(false)
const error = ref('')
const sent = ref(false)
const autoLoggingIn = ref(false)
let tokenProcessed = false

// Estados de 2FA
const twoFaStatus = ref('') // 'totp_required' ou 'totp_setup_required'
const totpCode = ref('')
const useRecoveryCode = ref(false)
const recoveryCode = ref('')
const qrCodeDataUrl = ref('')
const totpSecret = ref('')
const confirmSetupCode = ref('')
const recoveryCodesScreen = ref(false)
const recoveryCodes = ref([])
const recoveryCodesSaved = ref(false)
const totpLoading = ref(false)

function isAllowedEmail(value) {
  return value.trim().toLowerCase().endsWith(ALLOWED_DOMAIN)
}

function resetForm() {
  sent.value = false
  error.value = ''
  loading.value = false
}

async function completeMagicLinkLogin(token) {
  if (!token || tokenProcessed || autoLoggingIn.value) {
    return
  }
  tokenProcessed = true
  autoLoggingIn.value = true
  error.value = ''

  try {
    const res = await confirmMagicLink(token)

    // Se houver status, significa que 2FA é necessário
    if (res?.status) {
      twoFaStatus.value = res.status

      if (res.status === 'totp_setup_required') {
        // Inicia setup de TOTP
        await handleStartTotpSetup()
      }
      // Para 'totp_required', a tela de entrada de código é exibida automaticamente
      autoLoggingIn.value = false
      return
    }

    // Caso antigo (ou sem 2FA): acesso completo
    if (res?.user && typeof setUser === 'function') {
      setUser(res.user)
    } else {
      await checkAuth()
    }
    await router.replace({ name: 'Home' })
  } catch (err) {
    autoLoggingIn.value = false
    tokenProcessed = false
    error.value =
      typeof err.message === 'string' && err.message
        ? err.message
        : INVALID_LINK_MSG
    // Token usado/expirado: limpa query e mostra formulário com erro
    await router.replace({ name: 'Login', query: { error: 'invalid_link' } })
  }
}

async function handleStartTotpSetup() {
  error.value = ''
  try {
    const res = await setupTotp()
    totpSecret.value = res.secret
    qrCodeDataUrl.value = await QRCode.toDataURL(res.otpauth_uri)
  } catch (err) {
    error.value = err.message || 'Erro ao iniciar setup de TOTP'
    twoFaStatus.value = ''
  }
}

async function handleConfirmTotpSetup() {
  error.value = ''
  totpLoading.value = true

  try {
    const res = await confirmTotpSetup(confirmSetupCode.value)
    recoveryCodes.value = res.recovery_codes || []
    recoveryCodesScreen.value = true
  } catch (err) {
    error.value = err.message || 'Código inválido. Tente novamente.'
  } finally {
    totpLoading.value = false
  }
}

async function handleRecoveryCodesSaved() {
  if (!recoveryCodesSaved.value) return

  error.value = ''

  try {
    if (typeof setUser === 'function') {
      // Assumindo que setUser foi preenchido anteriormente (do confirmMagicLink)
      // Aqui apenas redirecionamos após confirmação
      await router.replace({ name: 'Home' })
    } else {
      await checkAuth()
      await router.replace({ name: 'Home' })
    }
  } catch (err) {
    error.value = err.message || 'Erro ao completar login'
  }
}

async function handleVerifyTotp() {
  error.value = ''
  totpLoading.value = true

  try {
    const payload = useRecoveryCode.value
      ? { recovery_code: recoveryCode.value }
      : { code: totpCode.value }

    const res = await verifyTotp(payload)

    if (res?.user && typeof setUser === 'function') {
      setUser(res.user)
    } else {
      await checkAuth()
    }

    twoFaStatus.value = ''
    await router.replace({ name: 'Home' })
  } catch (err) {
    error.value = err.message || 'Código inválido ou expirado.'
  } finally {
    totpLoading.value = false
  }
}

function copyRecoveryCode(index) {
  const code = recoveryCodes.value[index]
  if (code) {
    navigator.clipboard.writeText(code)
  }
}

function downloadRecoveryCodes() {
  const text = recoveryCodes.value.join('\n')
  const element = document.createElement('a')
  element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(text))
  element.setAttribute('download', 'codigos-recuperacao.txt')
  element.style.display = 'none'
  document.body.appendChild(element)
  element.click()
  document.body.removeChild(element)
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

watch(
  () => route.query.token,
  (newToken) => {
    if (typeof newToken === 'string' && newToken.trim()) {
      tokenProcessed = false
      completeMagicLinkLogin(newToken.trim())
    }
  }
)

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
