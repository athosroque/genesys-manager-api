# Guia de Operação: Sincronização SQLite para PostgreSQL via Cloudflare Tunnels

Este guia documenta as configurações já aplicadas no Cloudflare Zero Trust e fornece o passo a passo exato para rodar o túnel cliente e o script de sincronização contínua na máquina de origem (onde reside o SQLite).

---

## 🟢 1. O que já foi configurado e aplicado (Destino & Cloudflare)

Toda a infraestrutura do lado do servidor e da Cloudflare foi configurada com sucesso:

1. **Rota no Túnel `homelab-backend` (`a0b38394-36fa-4ac1-b06f-634c80bd8451`)**:
   - Hostname: `postgres.projetoathos.com.br`
   - Serviço: `tcp://192.168.0.101:5432`
   - O daemon `cloudflared` no servidor já atualizou e aplicou a nova configuração (v27).
2. **DNS Cloudflare**:
   - CNAME `postgres.projetoathos.com.br` apontando para o túnel com Proxy ativado.
3. **Cloudflare Access & Segurança**:
   - Aplicação Self-Hosted criada: `PostgreSQL Homelab` (`postgres.projetoathos.com.br`).
   - Política de Acesso configurada: `Service Token Auth` (Non-Identity).
   - Service Token gerado: `etl-sqlite-sync`.
4. **Banco de Dados Destino**:
   - PostgreSQL 15 ativo no container `genesys-manager-api-db-1`.
   - Tabela `tickets` pronta e estruturada.

---

## 🔑 2. Credenciais do Service Token Gerado

* **Service Token Name:** `etl-sqlite-sync`
* **Client ID:** `1cadb1769f6618e707b33e11a61c4820.access`
* **Client Secret:** `cfast_1FzE9GfBUE1kParSQuAP0Fbz3jFjWsHdaJ4779Vfe2d01405`

*(Nota: O arquivo local `backend/.cloudflare_service_token.json` foi salvo com o backup dessas credenciais e protegido no `.gitignore`).*

---

## 🚀 3. O que executar na Máquina de Origem (Onde está o SQLite)

### Passo 1: Abrir o canal TCP seguro com `cloudflared`

Na máquina onde está o banco SQLite, execute o comando abaixo (ou configure como serviço systemd / supervisor):

```bash
cloudflared access tcp \
  --hostname postgres.projetoathos.com.br \
  --url 127.0.0.1:5432 \
  --service-token-id "1cadb1769f6618e707b33e11a61c4820.access" \
  --service-token-secret "cfast_1FzE9GfBUE1kParSQuAP0Fbz3jFjWsHdaJ4779Vfe2d01405"
```

> **Dica (Systemd na Origem):** Para deixar o `cloudflared` rodando em background continuamente como serviço do sistema operacional:
>
> Arquivo `/etc/systemd/system/cloudflared-postgres.service`:
> ```ini
> [Unit]
> Description=Cloudflare Access TCP Tunnel para Postgres
> After=network.target
>
> [Service]
> Type=simple
> User=root
> ExecStart=/usr/local/bin/cloudflared access tcp --hostname postgres.projetoathos.com.br --url 127.0.0.1:5432 --service-token-id "1cadb1769f6618e707b33e11a61c4820.access" --service-token-secret "cfast_1FzE9GfBUE1kParSQuAP0Fbz3jFjWsHdaJ4779Vfe2d01405"
> Restart=always
> RestartSec=5
>
> [Install]
> WantedBy=multi-user.target
> ```
> Ative com:
> ```bash
> sudo systemctl daemon-reload
> sudo systemctl enable --now cloudflared-postgres
> ```

---

### Passo 2: Executar o Worker de Sincronização Contínua (ETL Python)

Copie o script `backend/etl_sync_sqlite_to_postgres.py` para a máquina de origem.

1. **Instale a dependência:**
   ```bash
   pip install psycopg2-binary
   ```

2. **Inicie o worker:**
   ```bash
   # Caso o arquivo SQLite esteja no mesmo diretório:
   python3 etl_sync_sqlite_to_postgres.py
   
   # Ou passando variáveis de ambiente customizadas:
   SQLITE_DB_PATH="/caminho/para/seu/tickets_enriched.db" \
   PG_HOST="127.0.0.1" \
   PG_PORT="5432" \
   PG_USER="postgres" \
   PG_PASSWORD="postgres" \
   PG_DB="genesys_manager" \
   SYNC_INTERVAL_SECONDS="10" \
   python3 etl_sync_sqlite_to_postgres.py
   ```

> **Dica (Systemd do Worker ETL):**
> Arquivo `/etc/systemd/system/etl-sqlite-sync.service`:
> ```ini
> [Unit]
> Description=ETL Worker SQLite to PostgreSQL
> After=cloudflared-postgres.service
>
> [Service]
> Type=simple
> User=athos
> WorkingDirectory=/caminho/do/script
> Environment=SQLITE_DB_PATH=/caminho/para/tickets_enriched.db
> Environment=PG_HOST=127.0.0.1
> Environment=PG_PORT=5432
> Environment=PG_USER=postgres
> Environment=PG_PASSWORD=postgres
> Environment=PG_DB=genesys_manager
> Environment=SYNC_INTERVAL_SECONDS=10
> ExecStart=/usr/bin/python3 etl_sync_sqlite_to_postgres.py
> Restart=always
> RestartSec=5
>
> [Install]
> WantedBy=multi-user.target
> ```
> Ative com:
> ```bash
> sudo systemctl daemon-reload
> sudo systemctl enable --now etl-sqlite-sync
> ```

---

## 🔍 4. Como monitorar e validar

No servidor de destino (Homelab), você pode acompanhar os dados chegando no PostgreSQL a qualquer momento:

```bash
docker exec -it genesys-manager-api-db-1 psql -U postgres -d genesys_manager -c "SELECT COUNT(*) FROM tickets;"
```

Ou checar os últimos registros inseridos:
```bash
docker exec -it genesys-manager-api-db-1 psql -U postgres -d genesys_manager -c "SELECT id, external_id, title, status, updated_at FROM tickets ORDER BY updated_at DESC LIMIT 5;"
```
