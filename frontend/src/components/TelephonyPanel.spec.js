import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import TelephonyPanel from './TelephonyPanel.vue'
import * as genesysApi from '../api/genesys'

vi.mock('../api/genesys', () => ({
  getUserTelephony: vi.fn(),
}))

describe('TelephonyPanel.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renderiza cenário 1 saudável corretamente', async () => {
    const mockHealthy = {
      user_id: 'u-123',
      user_name: 'Usuario Teste',
      scenario: 1,
      scenario_title: 'Cenário 1: Backend Íntegro (Problema Local na Máquina)',
      is_healthy: true,
      diagnosis: 'Configuração correta no Genesys Cloud.',
      recommendations: ['Fechar abas duplicadas', 'Limpar cache'],
      issues: [],
      station: {
        id: 'st-1',
        name: 'p523303_1',
        status: 'ASSOCIATED',
        type: 'generic_sip',
        line_appearance_id: 'line-1',
        is_associated: true,
      },
      phone: {
        id: 'ph-1',
        name: 'p523303_SIP',
        state: 'active',
        site: { id: 's-1', name: 'Site Matriz' },
        phone_base_settings: { id: 'pbs-1', name: 'WebRTC Template' },
      },
      summary: {
        station_assigned: true,
        station_associated: true,
        phone_active: true,
      },
    }

    genesysApi.getUserTelephony.mockResolvedValueOnce(mockHealthy)

    const wrapper = mount(TelephonyPanel, {
      props: { userId: 'u-123' },
    })

    expect(wrapper.text()).toContain('Consultando diagnóstico de telefonia')

    await flushPromises()

    expect(wrapper.text()).toContain('Cenário 1: Íntegro')
    expect(wrapper.text()).toContain('p523303_1')
    expect(wrapper.text()).toContain('ASSOCIATED')
    expect(wrapper.text()).toContain('Site Matriz')
  })

  it('renderiza cenário 2 com inconsistências', async () => {
    const mockInconsistent = {
      user_id: 'u-456',
      user_name: 'Usuario Falha',
      scenario: 2,
      scenario_title: 'Cenário 2: Inconsistência na Configuração do Genesys Cloud',
      is_healthy: false,
      diagnosis: 'Inconsistência encontrada no Genesys Cloud.',
      recommendations: ['Ajustar ramal no Admin'],
      issues: ['Usuário não possui estação efetiva atribuída no Genesys Cloud.'],
      station: null,
      phone: null,
      summary: {
        station_assigned: false,
        station_associated: false,
        phone_active: false,
      },
    }

    genesysApi.getUserTelephony.mockResolvedValueOnce(mockInconsistent)

    const wrapper = mount(TelephonyPanel, {
      props: { userId: 'u-456' },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Cenário 2: Inconsistente')
    expect(wrapper.text()).toContain('Não Atribuída')
    expect(wrapper.text()).toContain('Usuário sem ramal atribuído')
    expect(wrapper.text()).toContain('DESCONECTADO')
    expect(wrapper.text()).toContain('Nenhum Telefone Base')
  })

  it('exibe mensagem de erro quando a chamada da API falhar', async () => {
    genesysApi.getUserTelephony.mockRejectedValueOnce(new Error('Falha de rede 500'))

    const wrapper = mount(TelephonyPanel, {
      props: { userId: 'u-err' },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Falha ao consultar telefonia')
    expect(wrapper.text()).toContain('Falha de rede 500')
    expect(wrapper.text()).toContain('Tentar novamente')
  })
})
