# Guia de Rastreabilidade: Transferência Nativa vs. Script (Genesys Cloud)

Este documento descreve os conceitos técnicos, regras de identificação, endpoints e campos necessários para distinguir se uma transferência (*Blind Transfer*) em uma interação no Genesys Cloud foi realizada através do **botão nativo do painel do Genesys** ou pelo **botão dentro do Script de Atendimento (Scripter / Aplicação de Tela)**.

---

## 1. O Problema e o Mito do "Audit Viewer"

### O Problema do CDR / Analytics
Quando ocorre uma transferência cega (*blind transfer*), o Analytics e o CDR registram:
* `disconnectType = "transfer"` no segmento do agente;
* Um novo segmento iniciando imediatamente com o destino transferido.

Isso indica **que houve** transferência e **para onde** ela foi, mas a API de Analytics isolada não discrimina se o clique ocorreu no cabeçalho nativo da interface do Genesys Cloud ou em um botão desenhado dentro do iframe da tela do operador (Scripter).

### O Mito do Audit Viewer
* O **Admin → Audit Viewer** (`/api/v2/audits/query`) registra eventos de auditoria **administrativa e de configuração** (ex.: criação de usuários, alteração de permissões, modificação de filas, publicação de fluxos no Architect, integrações).
* **Ações operacionais de telefonia em tempo real** (como clicar em *Transferir*, *Hold*, *Mute*, *Desconectar*) **NÃO são auditadas pelo Audit Viewer**. Não existe na Genesys um log de auditoria administrativa gerado por cliques de controle de chamada telefônica.

---

## 2. Conceitos Extraídos: A Mecânica de Cada Transferência

A diferenciação definitiva não é feita por um campo booleano único, mas sim pela **cadeia de evidências de dados deixada na interação**:

### A. Fluxo do Botão Nativo de Transferência (Genesys Interaction UI)
1. O agente clica no botão "Transferir" localizado no painel de controle superior da chamada no Genesys Cloud.
2. O navegador dispara a chamada REST nativa (`POST /api/v2/conversations/calls/{id}/participants/{id}/replace` ou `/transfer`).
3. A chamada é encaminhada **diretamente** para a fila ou número digitado/selecionado pelo agente.
4. **Impacto nos dados:**
   * A chamada não executa nenhuma regra de negócio intermediária do Script.
   * **NÃO grava atributos customizados de transferência** (ex.: `mcduTransferencia`, `temTransferencia`).
   * O próximo participante na timeline é diretamente a **fila ACD** ou o **telefone externo**.

### B. Fluxo do Botão do Script (Genesys Scripter / Aplicação de Tela)
1. O agente utiliza a tela do Script (ex.: `Atendimento_Voz_Demais_SEG_Callback`) e clica no botão dedicado de **"Transferir"**.
2. O botão está atrelado a uma ação customizada (ex.: `transfer2Flow` / `02ae0478-5bd6-4d4a-93d2-2a3c3a4e1b05`).
3. **A ação do script executa uma cadeia obrigatória de 2 etapas:**
   * **Etapa 1:** Executa uma Data Action / Bridge Action (`custom_-_a2c50d44...`) que grava nos dados do cliente (`customer`) os atributos:
     * `mcduTransferencia = "<código_mcdu>"` (ex.: `"8271"`)
     * `temTransferencia = "true"`
   * **Etapa 2:** Dispara a função `scripter.blindTransfer` apontando especificamente para uma **URA intermediária de transbordo** (ex.: `URA_ROTEAMENTO_TRANSFERENCIAS`).
4. A URA intermediária atende o cliente em frações de segundo, lê o atributo `mcduTransferencia` via Architect e realiza a transferência para a fila correta de destino.

---

## 3. Matriz Comparativa (Regra de Ouro)

| Critério de Análise | Transferência via Script (Scripter) | Transferência via Botão Nativo (UI) |
| :--- | :--- | :--- |
| **Atributo `mcduTransferencia`** | **Presente** (com código numérico, ex: `8271`) | **Ausente** (ou vazio) |
| **Atributo `temTransferencia`** | `true` | Ausente |
| **Atributo `scriptId`** | UUID do script aberto associado | N/A (não acionado pelo fluxo) |
| **Próximo Participante Imediato** | IVR intermediário (`URA_ROTEAMENTO_TRANSFERENCIAS`) | Fila ACD direta ou número externo |
| **Data Action intermediária** | Disparada segundos antes do transfer | Nenhuma Data Action disparada |
| **Wrap-up Notes do Agente** | Geralmente documenta o motivo da fila de destino | Varia com o comportamento do operador |

---

## 4. Endpoints e Campos a Consultar

Para auditar uma conversa de forma automatizada, consulte os dois endpoints abaixo:

### Endpoint 1: Dados em Tempo Real e Atributos da Conversa
```http
GET https://api.{region}/api/v2/conversations/{conversationId}
Authorization: Bearer {token}
```

#### Campos-Chave a Inspecionar:

1. **`participants[?(@.purpose=='customer')].attributes`**
   * Verifique a presença de:
     * `mcduTransferencia`: Valor do MCDU selecionado no script. Se preenchido, comprova execução via Script.
     * `temTransferencia`: `"true"`
     * `scriptId`: UUID do script que executou a ação.
     * `ScreenPopName`: Nome da página/script exibida ao agente.
     * `eventLog`: Mensagens de transbordo registradas na jornada (ex: `TRANSFERENCIA_ENTRE_FILAS`).

2. **`participants[?(@.purpose=='agent')].calls[].disconnectType`**
   * Deve ser `"transfer"`.

3. **`participants[?(@.purpose=='agent')].calls[].wrapup`**
   * Inspecione `wrapup.name` (ex.: `"TRANSFERÊNCIA ENTRE FILAS"`) e `wrapup.notes` (notas manuais inseridas pelo atendente).

4. **`participants[?(@.purpose=='agent')].calls[].clientIpAddress`**
   * IP de origem da estação do agente que finalizou a chamada.

---

### Endpoint 2: Detalhes Analíticos da Timeline (Sessões e Segmentos)
```http
GET https://api.{region}/api/v2/analytics/conversations/{conversationId}/details
Authorization: Bearer {token}
```

#### Campos-Chave a Inspecionar:

1. **Sequência Cronológica dos Participantes (`participants`):**
   * Localize o participante agente que desligou com `disconnectType = "transfer"`.
   * Observe o participante imediatamente posterior (pelo timestamp `segmentStart`):
     * **Se for uma URA de roteamento (`URA_ROTEAMENTO_TRANSFERENCIAS`):** Confirmação de que o Script assumiu o controle e direcionou para o fluxo de transferência automatizado.
     * **Se for diretamente uma Fila ACD (`purpose = "acd"`):** Indica que a chamada foi despejada diretamente na fila pelo botão nativo, sem passar pela URA de transbordo do script.

---

### Endpoint 3: Inspeção do Script Publicado (Opcional, para Auditoria de UI)
```http
GET https://api.{region}/api/v2/scripts/published/{scriptId}
GET https://api.{region}/api/v2/scripts/published/{scriptId}/pages/{pageId}
Authorization: Bearer {token}
```

#### Campos-Chave a Inspecionar:
* `customActions`: Procura por ações do tipo `transfer2Flow` ou que contenham `scripter.blindTransfer`.
* `page.components`: Localiza o botão (ex: texto `"Transferir"`, cor `#28a745`) e valida se o `clickAction` aponta para o ID da ação de transferência.

---

## 5. Algoritmo de Decisão (Pseudocódigo)

```python
def identificar_origem_transferencia(conv_data: dict) -> str:
    customer = next((p for p in conv_data["participants"] if p["purpose"] == "customer"), None)
    if not customer:
        return "INCONCLUSIVO_SEM_CUSTOMER"

    attrs = customer.get("attributes", {})
    mcdu = attrs.get("mcduTransferencia")
    tem_transf = attrs.get("temTransferencia") == "true"
    
    # Identifica o participante seguinte ao agente que transferiu
    next_participant = obter_participante_apos_transfer(conv_data)
    next_name = next_participant.get("name", "") if next_participant else ""

    # Regra de decisão
    if mcdu and tem_transf and "URA_ROTEAMENTO_TRANSFERENCIAS" in next_name:
        return f"SCRIPT_TRANSFER (Disparado pelo Scripter - MCDU: {mcdu})"
    elif not mcdu and "URA_ROTEAMENTO_TRANSFERENCIAS" not in next_name:
        return "NATIVE_TRANSFER (Disparado pelo botão nativo do Genesys)"
    else:
        return "TRANSFERENCIA_MISTA_OU_CUSTOMIZADA"
```

---

## 6. Scripts Disponíveis no Repositório

O projeto possui scripts prontos que automatizam essa checagem:

1. **Consulta Completa de Auditoria de Conversa:**
   * Arquivo: `backend/consultar_auditoria_conversa.py`
   * Execução:
     ```bash
     cd backend
     .venv/bin/python consultar_auditoria_conversa.py
     ```
   * Saída: Gera o relatório consolidado com cadeia de evidências e auditoria em `backend/retorno_auditoria_conversa.json`.

2. **Inspeção de Telas e Ações de Scripts:**
   * Arquivo: `backend/consultar_scripter.py`
   * Mapeia botões, regras de callback e fluxos de transferência configurados no Scripter.
