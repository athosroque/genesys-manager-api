import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import UserChangesList from './UserChangesList.vue'

const sampleChange = {
  id: 'evt-1',
  category: 'division',
  action: 'update',
  resource: { id: 'd1', name: 'Divisão A' },
  before: 'X',
  after: 'Y',
  changed_by: { kind: 'USER', name: 'Athos' },
  event_date: '2026-08-03T12:00:00Z',
}

describe('UserChangesList — aviso de truncamento', () => {
  it('exibe a mensagem quando truncated é true', () => {
    const wrapper = mount(UserChangesList, {
      props: {
        changes: [sampleChange],
        truncated: true,
        fetchedDeepCategories: ['queue'],
      },
    })
    const warning = wrapper.get('[data-testid="truncated-warning"]')
    expect(warning.text()).toContain('~2.500 eventos da organização')
    expect(warning.text()).toContain('podem faltar')
  })

  it('exibe categorias truncadas quando truncatedByCategory informa', () => {
    const wrapper = mount(UserChangesList, {
      props: {
        changes: [sampleChange],
        truncated: true,
        truncatedByCategory: { queue: true, role: false },
        fetchedDeepCategories: ['queue', 'role'],
      },
    })
    const warning = wrapper.get('[data-testid="truncated-warning"]')
    expect(warning.text()).toContain('Fila')
    expect(warning.text()).toContain('Varredura parcial em')
  })

  it('não exibe a mensagem quando truncated é false', () => {
    const wrapper = mount(UserChangesList, {
      props: {
        changes: [sampleChange],
        truncated: false,
        fetchedDeepCategories: ['queue'],
      },
    })
    expect(wrapper.find('[data-testid="truncated-warning"]').exists()).toBe(false)
  })
})

describe('UserChangesList — múltiplos usuários e target_user', () => {
  const user1 = { id: 'u-1', name: 'Lucas Silva', email: 'lucas@example.com' }
  const user2 = { id: 'u-2', name: 'Maria Souza', email: 'maria@example.com' }

  const multiChanges = [
    {
      id: 'evt-10',
      category: 'queue',
      action: 'add',
      resource: { id: 'q-1', name: 'Fila Suporte' },
      target_user: user1,
      changed_by: { kind: 'USER', name: 'Admin' },
      event_date: '2026-08-03T14:00:00Z',
    },
    {
      id: 'evt-20',
      category: 'role',
      action: 'add',
      resource: { id: 'r-1', name: 'Admin Role' },
      target_user: user2,
      changed_by: { kind: 'USER', name: 'Admin' },
      event_date: '2026-08-03T15:00:00Z',
    },
  ]

  it('exibe chips de pessoas e badge com target_user quando há múltiplos usuários', async () => {
    const wrapper = mount(UserChangesList, {
      props: {
        changes: multiChanges,
        queriedUsers: [user1, user2],
        fetchedDeepCategories: ['queue', 'role'],
      },
    })

    expect(wrapper.text()).toContain('Pessoa:')
    expect(wrapper.text()).toContain('Lucas Silva')
    expect(wrapper.text()).toContain('Maria Souza')
    expect(wrapper.text()).toContain('Todas as pessoas')

    // Verifica se os cards mostram badge do target_user
    expect(wrapper.text()).toContain('👤 Lucas Silva')
    expect(wrapper.text()).toContain('👤 Maria Souza')
    expect(wrapper.text()).toContain('para Lucas Silva')

    // Filtra por Lucas Silva
    const lucasBtn = wrapper.findAll('button').find((b) => b.text().includes('Lucas Silva'))
    expect(lucasBtn).toBeDefined()
    await lucasBtn.trigger('click')

    expect(wrapper.text()).toContain('Fila Suporte')
    expect(wrapper.text()).not.toContain('Admin Role')
  })
})
