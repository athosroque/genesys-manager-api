#!/usr/bin/env python3
"""
ETL Worker: Sincronização Incremental Contínua SQLite -> PostgreSQL
Executa a cada N segundos (padrão: 10s), sincronizando novos registros
e atualizações da tabela 'tickets'.
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
logger = logging.getLogger("sqlite_postgres_sync")

# Variáveis de Configuração
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
    logger.info("Sinal de interrupção recebido. Encerrando worker suavemente...")
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
        logger.warning(f"Arquivo SQLite não encontrado em '{SQLITE_DB_PATH}'. Aguardando...")
        return

    # Conectar ao Postgres para obter watermark (último id / contagem)
    try:
        with get_pg_connection() as pg_conn:
            with pg_conn.cursor() as pg_cur:
                pg_cur.execute("SELECT COALESCE(MAX(id), 0) FROM tickets;")
                last_pg_id = pg_cur.fetchone()[0]
                
                pg_cur.execute("SELECT COALESCE(MAX(updated_at), '1970-01-01'::timestamptz) FROM tickets;")
                last_pg_updated = pg_cur.fetchone()[0]

            # Conectar ao SQLite para buscar novos registros ou modificados
            with sqlite3.connect(SQLITE_DB_PATH) as sqlite_conn:
                sqlite_conn.row_factory = sqlite3.Row
                sqlite_cur = sqlite_conn.cursor()

                # Busca tanto registros com id maior quanto atualizações recentes
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

                logger.info(f"Sincronizados {len(records_to_upsert)} tickets (novos/atualizados) com sucesso!")

    except psycopg2.OperationalError as e:
        logger.error(f"Erro de conexão com PostgreSQL via túnel ({PG_HOST}:{PG_PORT}): {e}")
    except Exception as e:
        logger.error(f"Erro inesperado durante o ciclo de sincronização: {e}", exc_info=True)

def main():
    logger.info("Iniciando Worker de Sincronização SQLite -> PostgreSQL...")
    logger.info(f"Origem SQLite: {SQLITE_DB_PATH}")
    logger.info(f"Destino PostgreSQL: {PG_HOST}:{PG_PORT}/{PG_DB} (Intervalo: {SYNC_INTERVAL}s)")

    while running:
        sync_cycle()
        for _ in range(SYNC_INTERVAL):
            if not running:
                break
            time.sleep(1)

    logger.info("Worker finalizado.")

if __name__ == "__main__":
    main()
