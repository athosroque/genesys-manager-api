# Verificação de Configuração de Usuário - Migração WebRTC (Genesys Cloud)

## 🎯 O Problema a ser Resolvido

Durante a migração para o WebRTC Softphone, usuários estão relatando falhas ao tentar realizar ou receber chamadas. Os sintomas incluem:
- Chamadas com duração de milissegundos (ex: 0,06s) sendo desconectadas com "Erro".
- Status de "Contatando" que cai instantaneamente.
- Ligações mudas ou falha de áudio.

Como a política de uso exige navegador homologado, aba única, limpeza de sessão e configuração correta de headset, precisamos primeiro garantir que a configuração de telefonia do usuário no Genesys Cloud está 100% correta. Se o backend estiver correto, o problema é isolado na estação de trabalho local do usuário (cache corrompido, concorrência de abas, bloqueio de microfone/firewall).

> [!TIP]
> **✨ Validação Automatizada no Genesys Manager:**
> Todo o processo manual descrito neste documento agora está **automatizado e integrado nativamente na plataforma**!
> - **Interface Web**: Na aba **Consulta e Ações**, ao pesquisar qualquer usuário por matrícula, e-mail ou UUID, o painel **Telefonia e Ramal** avalia os 3 pilares automaticamente em paralelo e gera o laudo técnico com o botão **"Copiar Laudo"**.
> - **Endpoint API**: `GET /api/users/{user_id}/telephony` (gerenciado por `services/user_telephony.py`).
> - **Script CLI**: Para validação rápida via terminal, execute `python backend/validate_webrtc.py <user_id>`.

## 🔎 O Que Estamos Buscando

Nosso objetivo com estas consultas à API é confirmar três pilares fundamentais da configuração do usuário:
1. O usuário possui uma estação atribuída (`effectiveStation`)?
2. O status atual de conexão da estação com o servidor está **ASSOCIATED** e operacional?
3. O telefone base associado à linha está ativo (`active`) e com Site configurado?

## 🚀 Endpoints de Validação

Para executar estas chamadas, você precisará do `userId` do colaborador.
(Você pode obter o userId pesquisando o nome dele em `GET /api/v2/users?name=NOME_DO_USUARIO`).

### 1. Validar Atribuição Geral e Estação Efetiva
Este endpoint traz a visão macro do usuário e nos diz exatamente qual aparelho/estação o Genesys reconhece no momento.

- **Método**: GET
- **Endpoint**: `/api/v2/users/{userId}?expand=station,telephony,presence`

**O que analisar no JSON (Resultado Esperado):**
- `effectiveStation`: Não pode ser `null`. Se estiver nulo, o usuário está sem telefone/estação atribuída.
  - Deve conter o `id` da estação associada (ex: `effectiveStation.id`).
- `presence`: Deve refletir o status de presença (ex: `On Queue`, `Available`, `Break`).

### 2. Consultar Status Detalhado da Estação do Usuário
Verifica o vínculo e status de conexão da estação com o servidor Genesys.

- **Método**: GET
- **Endpoint**: `/api/v2/users/{userId}/station`
  *(Ou diretamente via `/api/v2/stations/{stationId}` usando o ID retornado na `effectiveStation`)*

**O que analisar no JSON (Resultado Esperado):**
- `status`: DEVE estar como `"ASSOCIATED"`.
  - **Atenção**: Se o status estiver `"DISASSOCIATED"`, significa que não há registro/conexão ativa no momento. Isso reforça a tese de que uma aba concorrente "roubou" a sessão, que a máquina perdeu conectividade, ou que os cookies/cache estão impedindo o token de renovar.
- `lineAppearanceId` ou `name`: Identificador da linha/estação correspondente.

### 3. Validar Configuração do Telefone Base (Phone)
Para checar as configurações estáticas do telefone criado e vinculado à estação (Site e PhoneBaseSettings).

- **Método**: GET
- **Endpoints Oficiais**:
  - **Via Linha / Estação (Recomendado)**: `/api/v2/telephony/providers/edges/phones?lines.id={station_id}`
  - **Via Usuário WebRTC direto**: `/api/v2/telephony/providers/edges/phones?webRtcUser.id={userId}`

**O que analisar no JSON (Resultado Esperado):**
- A lista de `entities` deve retornar o telefone vinculado.
- `state`: `"active"`.
- `site`: O site atrelado deve estar preenchido, pois é o site que dita as rotas de saída (Dial Plan) e que permite que o usuário faça ligações externas.
- `phoneBaseSettings`: Template de telefonia associado.

---

### 🔑 Permissões Necessárias no OAuth Client Credentials
Para que as chamadas acima funcionem via API / Backend, a role atribuída ao Client Credentials no Genesys Cloud precisa conter:
1. `telephony:otherStationAssociation:view` (para consultar `/api/v2/users/{userId}/station`)
2. `telephony:plugin:all` (para consultar `/api/v2/telephony/providers/edges/phones`)

## 📋 Conclusão e Próximos Passos (Checklist de Atendimento)

Após executar os endpoints acima:

### 🟢 CENÁRIO 1: Tudo Correto no Backend
- `effectiveStation` atribuída (não nula).
- `status` da estação está `ASSOCIATED`.
- Telefone base `state: "active"` e no Site correto.

**Ação:** O Genesys Cloud está configurado perfeitamente no backend. O problema está na máquina local do usuário. Enviar resposta padronizada ao solicitante exigindo a execução do checklist local:
1. Fechar todas as abas concorrentes do Genesys.
2. Limpar cache e cookies de todo o período e relogar.
3. Garantir que o navegador tem permissão nas configurações do SO para acessar o Microfone.
4. Rodar o teste em Configurações > Diagnósticos WebRTC.

### 🔴 CENÁRIO 2: Inconsistência Encontrada
- `effectiveStation` é nulo (sem estação atribuída).
- `status` está `DISASSOCIATED` constantemente.
- Telefone inativo ou sem site atribuído.

**Ação:** A TI/Suporte do Genesys precisa corrigir a configuração do usuário na aba de Administração (Admin > Telefonia > Telefones) antes de exigir testes na máquina do usuário. Corrigir o ramal, associar a estação e pedir para o usuário relogar.

---

## 🔬 Exemplos Reais Validados na API

### 🟢 Exemplo Cenário 1 (Configuração Correta)
- **ID Testado**: `956ee25f-e931-476b-9ce2-0680c6dedc57`
- **GET `/api/v2/users/{userId}?expand=station`**:
  ```json
  {
    "station": {
      "effectiveStation": {
        "id": "30c3a596-eca5-420a-ba37-31eb47239ecd",
        "providerInfo": { "name": "p523303_1" }
      }
    }
  }
  ```
- **GET `/api/v2/stations/30c3a596-eca5-420a-ba37-31eb47239ecd`**:
  ```json
  {
    "id": "30c3a596-eca5-420a-ba37-31eb47239ecd",
    "name": "p523303_SIP",
    "status": "ASSOCIATED",
    "type": "generic_sip"
  }
  ```
- **GET `/api/v2/telephony/providers/edges/phones?lines.id=30c3a596-eca5-420a-ba37-31eb47239ecd`**:
  ```json
  {
    "entities": [
      {
        "id": "52df45c3-455c-4e3c-8f29-fefdb4bd0633",
        "name": "p523303_SIP",
        "state": "active",
        "site": { "id": "4bb310f5-7fb9-40b3-8c5b-34774a351abf" },
        "phoneBaseSettings": { "id": "0ee2c512-a570-4142-8a2f-eea459622780" }
      }
    ]
  }
  ```
*Diagnóstico: Backend 100% íntegro.*

### 🔴 Exemplo Cenário 2 (Inconsistência / Sem Estação)
- **ID Testado**: `a157b2f2-9a3f-4426-b7cf-b1a040594b28`
- **GET `/api/v2/users/{userId}?expand=station`**:
  ```json
  {
    "station": {}
  }
  ```
  *(Nota: `effectiveStation` nem sequer existe no retorno).*
- **GET `/api/v2/users/{userId}/station`**:
  ```json
  {
    "userId": "a157b2f2-9a3f-4426-b7cf-b1a040594b28"
  }
  ```
  *(Nota: Apenas o `userId` é devolvido, sem nenhum objeto de estação associada).*
- **GET `/api/v2/telephony/providers/edges/phones?webRtcUser.id={userId}`**:
  ```json
  {
    "entities": []
  }
  ```
*Diagnóstico: Usuário não possui estação nem telefone configurados no Genesys Cloud.*
