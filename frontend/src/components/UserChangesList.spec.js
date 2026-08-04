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
