# Guia de Configuração e Envio: Sincronização SQLite ➔ PostgreSQL

Este documento contém todas as instruções, comandos e scripts necessários para configurar a máquina de **Origem** (onde está o banco SQLite). O objetivo é transmitir os dados de forma contínua e segura para o PostgreSQL de destino via Cloudflare Zero Trust.

---

## 🏗️ 1. Como Funciona a Conexão (Visão Rápida)

1. A máquina de origem executa o `cloudflared access tcp`, que cria uma porta local `127.0.0.1:5432`.
2. Para o seu script local, é exatamente como se o PostgreSQL estivesse rodando na própria máquina (`localhost`).
3. Sob o capô, o `cloudflared` criptografa a conexão e a envia via túnel seguro da Cloudflare autenticado por **Service Token**.
4. Nenhuma porta precisa ser aberta no firewall ou roteador.

---

## 📋 2. Pré-requisitos na Máquina de Origem

1. **Python 3.8+** instalado com `pip`.
2. **Cloudflared CLI** instalado.
   - *Instalação rápida no Linux (Debian/Ubuntu):*
     ```bash
     curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /etc/apt/trusted.gpg.d/cloudflare.gpg >/dev/null
     echo "deb [signed-by=/etc/apt/trusted.gpg.d/cloudflare.gpg] https://pkg.cloudflare.com/cloudflared $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/cloudflared.list
     sudo apt update && sudo apt install -y cloudflared
     ```
3. Instalar o driver PostgreSQL para Python:
   ```bash
   pip install psycopg2-binary
   ```

---

## 🔑 3. Credenciais e Parâmetros de Conexão

| Parâmetro | Valor |
| :--- | :--- |
| **Hostname Remoto:** | `postgres.projetoathos.com.br` |
| **Porta Local Mapeada:** | `127.0.0.1:5432` |
| **Service Token ID (Client ID):** | `1cadb1769f6618e707b33e11a61c4820.access` |
| **Service Token Secret (Client Secret):** | `cfast_1FzE9GfBUE1kParSQuAP0Fbz3jFjWsHdaJ4779Vfe2d01405` |
| **Banco de Dados (PostgreSQL):** | `genesys_manager` |
| **Usuário PostgreSQL:** | `postgres` |
| **Senha PostgreSQL:** | `postgres` |

---

## 🚀 4. Passo 1: Abrir o Túnel Seguro na Origem

Execute o comando abaixo para iniciar o túnel na porta local `5432`:

```bash
cloudflared access tcp \
  --hostname postgres.projetoathos.com.br \
  --url 127.0.0.1:5432 \
  --service-token-id "1cadb1769f6618e707b33e11a61c4820.access" \
  --service-token-secret "cfast_1FzE9GfBUE1kParSQuAP0Fbz3jFjWsHdaJ4779Vfe2d01405"
```

### 💡 (Recomendado) Rodar como Serviço de Sistema (Systemd)

Para que o túnel inicie automaticamente com a máquina e reinicie se cair, crie o arquivo `/etc/systemd/system/cloudflared-postgres.service`:

```ini
[Unit]
Description=Cloudflare Access TCP - Tunel Postgres
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/cloudflared access tcp --hostname postgres.projetoathos.com.br --url 127.0.0.1:5432 --service-token-id "1cadb1769f6618e707b33e11a61c4820.access" --service-token-secret "cfast_1FzE9GfBUE1kParSQuAP0Fbz3jFjWsHdaJ4779Vfe2d01405"
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Ative com:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now cloudflared-postgres
```

---

## 🐍 5. Passo 2: Script de Transposição Contínua (Python Worker)

Salve o código abaixo como `sync_sqlite_to_postgres.py` no diretório onde está o seu arquivo `.db` (ou aponte a variável `SQLITE_DB_PATH` para o caminho correto).

```python
#!/usr/bin/env python3
"""
Worker de Transposição Contínua SQLite -> PostgreSQL
Sincroniza registros a cada 10 segundos com controle incremental e upsert.
"""

import os
import sys
import time
import signal
import sqlite3
import logging
from datetime import datetime
import psycopg2
from psycopg2.extras import execute_values

# Configuração de Logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("sync_worker")

# Variáveis Configuráveis (via ambiente ou valores padrão)
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "tickets_enriched.db")
PG_HOST = os.getenv("PG_HOST", "127.0.0.1")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "postgres")
PG_DB = os.getenv("PG_DB", "genesys_manager")
SYNC_INTERVAL = int(os.getenv("SYNC_INTERVAL_SECONDS", "10"))

running = True

def handle_exit(signum, frame):
    global running
    logger.info("Encerrando worker de sincronização...")
    running = False

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

def get_pg_connection():
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        user=PG_USER,
        password=PG_PASSWORD,
        dbname=PG_DB,
        connect_timeout=5
    )

def parse_iso_datetime(dt_val):
    if not dt_val:
        return None
    if isinstance(dt_val, datetime):
        return dt_val
    try:
        return datetime.fromisoformat(str(dt_val).replace("Z", "+00:00"))
    except Exception:
        return None

def sync_cycle():
    if not os.path.exists(SQLITE_DB_PATH):
        logger.warning(f"Base SQLite '{SQLITE_DB_PATH}' não encontrada. Aguardando...")
        return

    try:
        # 1. Obtém a marca d'água no PostgreSQL de destino
        with get_pg_connection() as pg_conn:
            with pg_conn.cursor() as pg_cur:
                pg_cur.execute("SELECT COALESCE(MAX(id), 0) FROM tickets;")
                last_pg_id = pg_cur.fetchone()[0]

                pg_cur.execute("SELECT COALESCE(MAX(updated_at), '1970-01-01'::timestamptz) FROM tickets;")
                last_pg_updated = pg_cur.fetchone()[0]

            # 2. Busca novos registros ou atualizados no SQLite local
            with sqlite3.connect(SQLITE_DB_PATH) as sqlite_conn:
                sqlite_conn.row_factory = sqlite3.Row
                sqlite_cur = sqlite_conn.cursor()

                query = """
                    SELECT id, external_id, title, description, status, category,
                           classification, suggested_response, is_faq, created_at, updated_at
                    FROM tickets
                    WHERE id > ? OR updated_at > ?
                    ORDER BY id ASC;
                """
                sqlite_cur.execute(query, (last_pg_id, str(last_pg_updated)))
                rows = sqlite_cur.fetchall()

                if not rows:
                    return

                records_to_upsert = []
                for r in rows:
                    records_to_upsert.append((
                        r["external_id"],
                        r["title"],
                        r["description"],
                        r["status"],
                        r["category"],
                        r["classification"],
                        r["suggested_response"],
                        bool(r["is_faq"]) if r["is_faq"] is not None else False,
                        parse_iso_datetime(r["created_at"]),
                        parse_iso_datetime(r["updated_at"])
                    ))

                # 3. Insere ou Atualiza (UPSERT) no PostgreSQL
                upsert_query = """
                    INSERT INTO tickets (
                        external_id, title, description, status, category,
                        classification, suggested_response, is_faq, created_at, updated_at
                    ) VALUES %s
                    ON CONFLICT (external_id) DO UPDATE SET
                        title = EXCLUDED.title,
                        description = EXCLUDED.description,
                        status = EXCLUDED.status,
                        category = EXCLUDED.category,
                        classification = EXCLUDED.classification,
                        suggested_response = EXCLUDED.suggested_response,
                        is_faq = EXCLUDED.is_faq,
                        updated_at = EXCLUDED.updated_at;
                """
                with pg_conn.cursor() as pg_cur:
                    execute_values(pg_cur, upsert_query, records_to_upsert)
                pg_conn.commit()

                logger.info(f"Sucesso: {len(records_to_upsert)} tickets sincronizados com o PostgreSQL.")

    except psycopg2.OperationalError as e:
        logger.error(f"Não foi possível conectar ao Postgres via 127.0.0.1:{PG_PORT}. O cloudflared está rodando? Erro: {e}")
    except Exception as e:
        logger.error(f"Erro no ciclo de sincronização: {e}", exc_info=True)

def main():
    logger.info("=== Worker ETL Iniciado ===")
    logger.info(f"Origem SQLite: {SQLITE_DB_PATH}")
    logger.info(f"Destino: {PG_HOST}:{PG_PORT}/{PG_DB} (Ciclo: {SYNC_INTERVAL}s)")

    while running:
        sync_cycle()
        for _ in range(SYNC_INTERVAL):
            if not running:
                break
            time.sleep(1)

    logger.info("Worker finalizado com sucesso.")

if __name__ == "__main__":
    main()
```

---

## 🏃 6. Como Iniciar o Worker

No mesmo terminal (com o túnel ativo em outro terminal ou rodando via systemd):

```bash
# Execução direta:
python3 sync_sqlite_to_postgres.py

# Ou especificando o caminho do SQLite:
SQLITE_DB_PATH="/caminho/para/tickets_enriched.db" python3 sync_sqlite_to_postgres.py
```

### 💡 (Recomendado) Rodar o Worker como Serviço Systemd

Crie o arquivo `/etc/systemd/system/sqlite-sync.service`:

```ini
[Unit]
Description=Worker de Sincronizacao SQLite para PostgreSQL
After=cloudflared-postgres.service network.target

[Service]
Type=simple
User=root
WorkingDirectory=/caminho/onde/esta/o/script
Environment=SQLITE_DB_PATH=/caminho/para/tickets_enriched.db
Environment=PG_HOST=127.0.0.1
Environment=PG_PORT=5432
Environment=PG_USER=postgres
Environment=PG_PASSWORD=postgres
Environment=PG_DB=genesys_manager
Environment=SYNC_INTERVAL_SECONDS=10
ExecStart=/usr/bin/python3 sync_sqlite_to_postgres.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Ative com:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now sqlite-sync
```

---

## ✅ 7. Como Saber se Está Funcionando?

1. Verifique os logs do serviço:
   ```bash
   sudo journalctl -u sqlite-sync -f
   ```
2. Você deverá ver mensagens como:
   ```text
   2026-09-16 12:00:00 [INFO] Sucesso: 45 tickets sincronizados com o PostgreSQL.
   ```
