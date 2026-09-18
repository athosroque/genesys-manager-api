# Especificação de Frontend: Dashboard de Diagnóstico de Interações Genesys Cloud

Este documento define a especificação completa de telas, componentes visuais, métricas e mapeamento de dados (a partir dos arquivos `_details.json` e `Auditoria Avançada`) para a criação do frontend de debug e auditoria de atendimentos.

---

## 📐 Visão Geral da Interface

O frontend receberá um campo de busca para o `conversationId` (UUID) e renderizará um dashboard de diagnóstico dividido em **5 blocos visuais principais**:

```
+----------------------------------------------------------------------------------------------------+
| [ 🔍 Input: Digite o conversationId ] [ Botão: Consultar / Auditar ]                              |
+----------------------------------------------------------------------------------------------------+
| 1. CABEÇALHO EXECUTIVO (Status, Canal, Cliente, Duração, Motivo de Desconexão e Gravação)           |
+----------------------------------------------------------------------------------------------------+
| 2. TRILHA DE AUDITORIA & ORIGEM (Badge: Direto do Bot vs Transferência entre Atendentes)          |
+----------------------------------------------------------------------------------------------------+
| 3. LINHA DO TEMPO VISUAL / TIMELINE (Stepper horizontal ou Gantt interativo de todos os estados)  |
+----------------------------------------------------------------------------------------------------+
| 4. DIAGNÓSTICO WEBRTC & BORDA AWS (Qualidade de Voz, Servidor Edge, Latência e Pacotes Perdidos)   |
+----------------------------------------------------------------------------------------------------+
| 5. GAVETA DE DADOS BRUTOS (Visualizador de JSON com busca e cópia rápida)                          |
+----------------------------------------------------------------------------------------------------+
```

---

## 🗂️ Detalhamento dos Componentes de Tela

### 1. Cabeçalho Executivo (Header Cards)
Card superior com resumo instantâneo da chamada/mensagem:

| Elemento Visual | O que exibir na tela | De qual JSON extrair | Caminho do Campo no JSON |
| :--- | :--- | :--- | :--- |
| **Badge de Canal** | `VOZ`, `WHATSAPP`, `CALLBACK`, `CHAT`, `EMAIL` | `details.json` | `participants[].sessions[].mediaType` (ex: `voice`, `message`) |
| **Sentido** | Ícone `Inbound (Receptivo)` ou `Outbound (Ativo)` | `details.json` | `participants[].sessions[].direction` |
| **Identificação Cliente** | Nome do cliente + Telefone formatado | `details.json` | `participants[0].participantName` e `sessions[0].ani` |
| **Destino / DNIS** | Número discado ou serviço acionado | `details.json` | `sessions[0].dnis` |
| **Duração Total** | Ex: `47m 30s` (calculado entre início e fim) | `details.json` | `conversationStart` e `conversationEnd` |
| **Data e Hora Início** | Data/Hora formatada em horário local (ex: `08/09/2026 13:12:00`) | `details.json` | `conversationStart` |
| **Status Desconexão** | Badge colorido com o tipo (ex: `Cliente Desligou`, `Transferido`, `Erro Sistema`) | `details.json` | Último `segments[].disconnectType` e `disconnectReason` |

---

### 2. Trilha de Auditoria & Origem do Atendimento (Origin & Transfer Card)
> **Problema que resolve:** Elimina chamados onde operadores dizem *"recebi atendimento indevido do BOT"*, comprovando instantaneamente se a interação veio do robô ou se foi transferência humana.

Componente em destaque (Banner de Alerta Inteligente):

* **Se antes do operador houve outro operador (`purpose == "agent"` ou `"user"`):**
  * 🏷️ **Badge Laranja/Azul:** `TRANSFERÊNCIA HUMANA (OPERADOR -> OPERADOR)`
  * Exibir: *"Transferido por [Nome do Atendente Anterior] da fila [Fila Original] após [X minutos] de conversa."*
* **Se antes do operador houve apenas robôs (`purpose == "botflow"` ou `"ivr"`):**
  * 🏷️ **Badge Verde/Roxo:** `DIRETO DA URA / BOT`
  * Exibir: *"Encaminhado pelo fluxo de BOT [Nome do Fluxo] com motivo [Exit Reason]."*

---

### 3. Linha do Tempo Visual / Timeline (Stepper / Gantt Interativo)
O componente central mais importante da tela. Deve mostrar o fluxo cronológico de ponta a ponta:

#### Como categorizar cada bloco da Timeline:

| Tipo do Bloco | Cor / Ícone Sugerido | Dados a Exibir no Bloco | Caminho no JSON (`details.json`) |
| :--- | :--- | :--- | :--- |
| **🤖 BOT / URA** | Lilás / `Bot` | Nome do Fluxo, Versão do Fluxo, Duração no Bot e Motivo de Saída (`TRANSFER`, `FLOW_EXIT`) | `sessions[].flow.flowName`<br>`sessions[].flow.exitReason`<br>`segments[type='ivr']` |
| **⏳ Fila de Espera (ACD)** | Amarelo / `Clock` | Nome da Fila (`queueName`), Tempo de Espera do Cliente em fila (`tAcd`) | `participants[purpose='acd'].name`<br>`sessions[].metrics[name='tAcd']` |
| **🔔 Chamando (Alerting)** | Laranja / `Bell` | Tempo que tocou no navegador/ramal do atendente antes de atender | `segments[type='alerting']` ou `metrics[name='tAlert']` |
| **🗣️ Atendimento Ativo** | Verde / `UserCheck` | Nome do Atendente, ID do Usuário, Tempo Falado / Conversado | `participantName`, `userId`<br>`segments[type='interact']` |
| **⏸️ Espera / Hold** | Vermelho Claro / `Pause` | Horário de início do Hold, término e duração exata de cada espera | `segments[type='hold'].segmentStart`<br>`segments[type='hold'].segmentEnd` |
| **🔄 Transferência** | Azul / `Shuffle` | Tipo de transferência (`Blind` / `Consult`), quem transferiu e para onde | `metrics[name='nBlindTransferred']`<br>`segments[type='wrapup'].disconnectType` |
| **📝 Pós-Atendimento / Wrapup**| Cinza / `FileText` | Código de tabulação e tempo de pós-atendimento (`tAcw`) | `segments[type='wrapup']`<br>`metrics[name='tAcw']` |

---

### 4. Diagnóstico de Infraestrutura WebRTC & Borda AWS (Quality Card)
Exibido para chamadas de **Voz**, crucial para investigar quedas, mudo unilateral e voz robótica:

#### Indicadores Visuais (Gauges / Progress Bars):

```
+---------------------------------------------------------------------------------------------------+
| 🌐 TELEFONIA & QUALIDADE WEBRTC                                                                   |
+-------------------------------------+-------------------------------------------------------------+
| Servidor Edge AWS:                  | Codec Utilizado: [ audio/opus ]                             |
| e925114b-606a-4dd2-ad84-5c20579384b0| Latência Máxima: [ 30 ms ] (Excelente < 100ms)             |
| [ Copiar Edge ID ]                  | Qualidade MOS:    [ 4.90 / 5.0 ] (Excelente > 4.3)         |
+-------------------------------------+ R-Factor:         [ 93.1 / 100 ]                            |
| SIP Call-ID da Operadora:           | Pacotes Recebidos: 41.077                                   |
| 1430725045892026131159@200.159...   | Pacotes Descartados: [ 0 ] ✅ (Perda Zero)                   |
| [ Copiar SIP Call-ID ]              |                                                             |
+-------------------------------------+-------------------------------------------------------------+
```

#### Regras de Cor para o Frontend:
* **Score MOS (`minMos`):**
  * `MOS >= 4.3`: 🟢 Verde (Excelente)
  * `4.0 <= MOS < 4.3`: 🟡 Amarelo (Aceitável)
  * `MOS < 4.0`: 🔴 Vermelho (Voz degradada / robótica)
* **Pacotes Descartados (`discardedPackets`):**
  * `0`: 🟢 Verde
  * `> 0`: 🔴 Vermelho piscante com badge: `⚠️ X PACOTES DESCARTADOS NA REDE`
* **Latência (`maxLatencyMs`):**
  * `< 100ms`: 🟢 Verde
  * `100ms a 200ms`: 🟡 Amarelo
  * `> 200ms`: 🔴 Vermelho (Atraso perceptível)

---

### 5. Tabela Completa de Mapeamento: JSON -> Frontend

| Dado no Frontend | Arquivo Origem | Caminho JSON | Observação / Formatação |
| :--- | :--- | :--- | :--- |
| **Conversation ID** | Ambos | `conversationId` ou `id` | Exibir com botão de copiar |
| **Hora Início / Fim** | `details.json` | `conversationStart`, `conversationEnd` | Converter ISO UTC para fuso do operador |
| **Duração Total** | `details.json` | `(conversationEnd - conversationStart)` | Formatar em `Xm Ys` ou `Xh Ym` |
| **Nome do Cliente** | `details.json` | `participants[purpose='customer'].participantName` | Ex: "Jessica", "Katia" |
| **Número do Cliente (ANI)** | `details.json` | `participants[purpose='customer'].sessions[].ani` | Ex: `tel:+5521966014176` |
| **Número Discado (DNIS)** | `details.json` | `participants[0].sessions[0].dnis` | Ex: `tel:0800123456` |
| **Edge Server ID** | `details.json` | `participants[].sessions[].edgeId` | UUID da máquina AWS Edge |
| **SIP Call-ID** | `details.json` | `participants[].sessions[].protocolCallId` | ID de sessão SIP da operadora |
| **Nome dos Fluxos BOT** | `details.json` | `participants[purpose='ivr'\|'botflow'].sessions[].flow.flowName` | Ex: `WhatsApp_Habitacao` |
| **Motivo de Saída do Bot**| `details.json` | `participants[].sessions[].flow.exitReason` | Ex: `TRANSFER`, `FLOW_EXIT` |
| **Destino da Transferência**| `details.json`| `participants[].sessions[].flow.transferTargetName` | Fila para onde o bot enviou |
| **Nome da Fila ACD** | `details.json` | `participants[purpose='acd'].participantName` | Ex: `WPP_HAB_HABITAÇÃO_JDF` |
| **Tempo em Fila** | `details.json` | `participants[purpose='acd'].sessions[].metrics[name='tAcd'].value` | Em milissegundos (dividir por 1000) |
| **Nome do Atendente** | `details.json` | `participants[purpose='user'\|'agent'].participantName` | Nome completo do operador |
| **ID do Atendente** | `details.json` | `participants[purpose='user'\|'agent'].userId` | UUID do usuário Genesys |
| **Tempo Falado** | `details.json` | `metrics[name='tTalk'].value` | Tempo conversando com o cliente |
| **Quantidade de Holds** | `details.json` | Quantidade de `segments[segmentType='hold']` | Número de vezes colocado em espera |
| **Tempo Total de Hold** | `details.json` | `metrics[name='tHeldComplete'].value` ou soma dos segments | Tempo somado que ficou em espera |
| **Tipo de Desconexão** | `details.json` | `segments[].disconnectType` | `client`, `peer`, `transfer`, etc. |
| **Motivo de Desconexão**| `details.json` | `segments[].disconnectReason` | Detalhe textual da desconexão |
| **Métricas WebRTC MOS** | `details.json` | `sessions[].mediaEndpointStats[].minMos` | Float (ex: `4.89`) |
| **Métricas R-Factor** | `details.json` | `sessions[].mediaEndpointStats[].minRFactor` | Float (ex: `92.5`) |
| **Latência Máxima** | `details.json` | `sessions[].mediaEndpointStats[].maxLatencyMs` | Inteiro em milissegundos |
| **Pacotes Descartados** | `details.json` | `sessions[].mediaEndpointStats[].discardedPackets` | Inteiro (alerta se > 0) |

---

## 💡 Mock de Layout Recomendado para o Frontend (React / Vue / Angular / Tailwind)

```html
<!-- Exemplo de estrutura de classes Tailwind sugerida -->
<div class="p-6 max-w-7xl mx-auto space-y-6">

  <!-- 1. Campo de Busca -->
  <div class="bg-white p-4 rounded-xl shadow-sm border border-slate-200 flex gap-4">
    <input type="text" placeholder="Cole o conversationId aqui..." class="flex-1 px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500" />
    <button class="bg-blue-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-blue-700">Auditar Interação</button>
  </div>

  <!-- 2. Header Cards Executivos -->
  <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
    <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
      <span class="text-xs text-slate-500 font-semibold uppercase">Canal & Sentido</span>
      <div class="mt-1 flex items-center gap-2">
        <span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-green-100 text-green-800">WHATSAPP</span>
        <span class="text-sm font-medium text-slate-700">Inbound (Receptivo)</span>
      </div>
    </div>
    <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
      <span class="text-xs text-slate-500 font-semibold uppercase">Cliente</span>
      <p class="mt-1 text-sm font-bold text-slate-800">Jessica</p>
      <p class="text-xs text-slate-500">+55 62 9496-2738</p>
    </div>
    <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
      <span class="text-xs text-slate-500 font-semibold uppercase">Duração Total</span>
      <p class="mt-1 text-lg font-extrabold text-slate-900">43m 20s</p>
      <p class="text-xs text-slate-400">08/09/2026 13:45 -> 14:29</p>
    </div>
    <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
      <span class="text-xs text-slate-500 font-semibold uppercase">Desconexão</span>
      <p class="mt-1"><span class="px-2 py-0.5 rounded text-xs font-bold bg-blue-100 text-blue-800">Cliente Desligou (PEER)</span></p>
      <p class="text-xs text-slate-400 mt-1">Normal / Inactivity</p>
    </div>
  </div>

  <!-- 3. Banner de Auditoria de Origem (Human vs Bot Transfer) -->
  <div class="bg-amber-50 border-l-4 border-amber-500 p-4 rounded-r-xl">
    <div class="flex items-center gap-3">
      <span class="text-xl">⚠️</span>
      <div>
        <h4 class="text-sm font-bold text-amber-900">Origem do Atendimento: Transferência Humana (Não veio do Bot)</h4>
        <p class="text-xs text-amber-800 mt-0.5">
          O cliente foi atendido inicialmente pela operadora <b>Larissa Valentina Loures dos Santos</b> na fila <i>WC_SAC_RECLAMACAO_JDF</i> e transferido via Blind Transfer para a fila <i>WPP_HAB_HABITAÇÃO_JDF</i> às 14:17:52.
        </p>
      </div>
    </div>
  </div>

  <!-- 4. Timeline Sequencial de Segmentos -->
  <div class="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
    <h3 class="text-base font-bold text-slate-800 mb-6">Linha do Tempo da Interação</h3>
    <!-- Stepper cronológico com cada participante e estado -->
  </div>

  <!-- 5. Bloco de Diagnóstico de Borda e Qualidade WebRTC -->
  <div class="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
    <h3 class="text-base font-bold text-slate-800 mb-4">Telefonia & Diagnóstico WebRTC (Mídia)</h3>
    <!-- Indicadores de MOS, R-Factor, Latência e Edge ID -->
  </div>

</div>
```

---

## 🎯 Resumo das Regras de Negócio para os Desenvolvedores Frontend

1. **Tratamento de tipos de mídia:**
   * Se for interação de **Mensagem/WhatsApp**, alguns campos de telefonia não existirão. O frontend deve tratar graciosamente chamadas de voz vs texto.
2. **Cálculo de Holds:**
   * O frontend deve filtrar todos os `segments` onde `segmentType == "hold"` dentro da perna do cliente ou do operador para somar o tempo total e a quantidade de pausas.
3. **Detecção de Transferência Cega vs Consulta:**
   * Se na sessão do operador constar `nBlindTransferred: 1`, exibir badge de **Transferência Cega**.
   * Se constar `nConsultTransferred: 1`, exibir badge de **Transferência com Consulta**.
4. **Alerta de Pacotes Descartados:**
   * Se `mediaEndpointStats[].discardedPackets > 0`, exibir badge vermelho de alerta com a contagem exata de pacotes perdidos.
