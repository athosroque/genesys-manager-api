import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import LoginView from './LoginView.vue'
import * as authApi from '../api/auth'
import * as authComposable from '../composables/useAuth'

const mockPush = vi.fn()
const mockReplace = vi.fn()
let currentQuery = {}

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
