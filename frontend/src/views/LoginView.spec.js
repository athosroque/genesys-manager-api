import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import LoginView from './LoginView.vue'
import * as authApi from '../api/auth'
import * as authComposable from '../composables/useAuth'

const mockPush = vi.fn()
const mockReplace = vi.fn()
let currentQuery = {}

vi.mock('qrcode', () => ({
  default: {
    toDataURL: vi.fn().mockResolvedValue('data:image/png;base64,test'),
  },
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({
    query: currentQuery,
  }),
  useRouter: () => ({
    push: mockPush,
    replace: mockReplace,
  }),
}))

describe('LoginView — fluxo de magic link', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    currentQuery = {}
  })

  it('exibe mensagem de link inválido quando query error=invalid_link', async () => {
    currentQuery = { error: 'invalid_link' }

    const wrapper = mount(LoginView)
    await flushPromises()

    expect(wrapper.text()).toContain('Link inválido, expirado ou já utilizado')
  })

  it('processa token da query e completa login com sucesso', async () => {
    currentQuery = { token: 'valid-token-123' }

    const mockUser = { username: 'test.user', full_name: 'Test User', role: 'user' }
    const confirmSpy = vi.spyOn(authApi, 'confirmMagicLink').mockResolvedValueOnce({
      message: 'Acesso autorizado.',
      user: mockUser,
    })

    const wrapper = mount(LoginView)
    await flushPromises()

    expect(confirmSpy).toHaveBeenCalledTimes(1)
    expect(confirmSpy).toHaveBeenCalledWith('valid-token-123')
    expect(mockReplace).toHaveBeenCalledWith({ name: 'Home' })
  })

  it('trata erro de token inválido e redireciona com error=invalid_link', async () => {
    currentQuery = { token: 'invalid-token-999' }

    vi.spyOn(authApi, 'confirmMagicLink').mockRejectedValueOnce(
      new Error('Link inválido, expirado ou já utilizado. Solicite um novo acesso.')
    )

    const wrapper = mount(LoginView)
    await flushPromises()

    expect(mockReplace).toHaveBeenCalledWith({
      name: 'Login',
      query: { error: 'invalid_link' },
    })
    expect(wrapper.text()).toContain('Link inválido, expirado ou já utilizado')
  })
})

describe('LoginView — fluxo de TOTP', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    currentQuery = {}
  })

  it('exibe tela de setup de TOTP quando status é totp_setup_required', async () => {
    currentQuery = { token: 'valid-token-123' }

    const setupSpy = vi.spyOn(authApi, 'setupTotp').mockResolvedValueOnce({
      secret: 'JBSWY3DPEBLW64TMMQ======',
      otpauth_uri: 'otpauth://totp/Genesys%20Manager:user%40claro.com.br?secret=JBSWY3DPEBLW64TMMQ%3D%3D%3D%3D%3D%3D&issuer=Genesys%20Manager',
    })

    vi.spyOn(authApi, 'confirmMagicLink').mockResolvedValueOnce({
      status: 'totp_setup_required',
    })

    const wrapper = mount(LoginView)
    await flushPromises()

    expect(wrapper.text()).toContain('Configure autenticação em duas etapas')
    expect(wrapper.text()).toContain('Escaneie o código QR')
    expect(setupSpy).toHaveBeenCalledTimes(1)
  })

  it('completa setup de TOTP e exibe tela de recovery codes', async () => {
    currentQuery = { token: 'valid-token-123' }

    vi.spyOn(authApi, 'setupTotp').mockResolvedValueOnce({
      secret: 'JBSWY3DPEBLW64TMMQ======',
      otpauth_uri: 'otpauth://totp/...',
    })

    vi.spyOn(authApi, 'confirmMagicLink').mockResolvedValueOnce({
      status: 'totp_setup_required',
    })

    const confirmSpy = vi.spyOn(authApi, 'confirmTotpSetup').mockResolvedValueOnce({
      user: { username: 'test.user', full_name: 'Test User' },
      recovery_codes: ['CODE-1', 'CODE-2', 'CODE-3', 'CODE-4', 'CODE-5', 'CODE-6', 'CODE-7', 'CODE-8', 'CODE-9', 'CODE-10'],
    })

    const wrapper = mount(LoginView)
    await flushPromises()

    // Preenche código de confirmação
    const input = wrapper.find('input[autocomplete="one-time-code"]')
    expect(input.exists()).toBe(true)

    await input.setValue('123456')
    await flushPromises()

    // Clica botão de confirmação
    const confirmButton = wrapper.findAll('button').find((b) => b.text().includes('Confirmar'))
    if (confirmButton) {
      await confirmButton.trigger('click')
      await flushPromises()
    }

    // Espera que confirmTotpSetup seja chamado
    expect(confirmSpy).toHaveBeenCalledWith('123456')
  })

  it('exibe tela de verificação de TOTP quando status é totp_required', async () => {
    currentQuery = { token: 'valid-token-456' }

    vi.spyOn(authApi, 'confirmMagicLink').mockResolvedValueOnce({
      status: 'totp_required',
    })

    const wrapper = mount(LoginView)
    await flushPromises()

    expect(wrapper.text()).toContain('Digite seu código de autenticação')
    expect(wrapper.text()).toContain('Verifique no seu autenticador')
  })

  it('verifica TOTP e redireciona após sucesso', async () => {
    currentQuery = { token: 'valid-token-456' }

    const mockUser = { username: 'test.user', full_name: 'Test User' }

    vi.spyOn(authApi, 'confirmMagicLink').mockResolvedValueOnce({
      status: 'totp_required',
    })

    const verifySpy = vi.spyOn(authApi, 'verifyTotp').mockResolvedValueOnce({
      user: mockUser,
    })

    const wrapper = mount(LoginView)
    await flushPromises()

    const input = wrapper.find('input[inputmode="numeric"]')
    await input.setValue('654321')
    await flushPromises()

    const verifyButton = wrapper.findAll('button').find((b) => b.text().includes('Verificar'))
    if (verifyButton) {
      await verifyButton.trigger('click')
      await flushPromises()
    }

    expect(verifySpy).toHaveBeenCalledWith({ code: '654321' })
  })

  it('aceita código de recuperação na tela de TOTP', async () => {
    currentQuery = { token: 'valid-token-789' }

    vi.spyOn(authApi, 'confirmMagicLink').mockResolvedValueOnce({
      status: 'totp_required',
    })

    const verifySpy = vi.spyOn(authApi, 'verifyTotp').mockResolvedValueOnce({
      user: { username: 'test.user' },
    })

    const wrapper = mount(LoginView)
    await flushPromises()

    // Clica no link "Usar código de recuperação"
    const recoveryToggle = wrapper.findAll('button').find((b) => b.text().includes('Usar código de recuperação'))
    if (recoveryToggle) {
      await recoveryToggle.trigger('click')
      await flushPromises()
    }

    // Preenche código de recuperação
    const input = wrapper.find('input[type="text"]')
    if (input.exists()) {
      await input.setValue('RECOVERY-CODE-123')
      await flushPromises()
    }

    const verifyButton = wrapper.findAll('button').find((b) => b.text().includes('Verificar'))
    if (verifyButton) {
      await verifyButton.trigger('click')
      await flushPromises()
    }

    expect(verifySpy).toHaveBeenCalledWith({ recovery_code: 'RECOVERY-CODE-123' })
  })
})
