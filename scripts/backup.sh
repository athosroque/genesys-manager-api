#!/usr/bin/env bash
# pg_dump + arquivos de estado, criptografados com age (chave pública do .sops.yaml).
set -euo pipefail

cd "$(dirname "$0")/.."

DEST="${BACKUP_DIR:-/var/backups/genesys}"
STAMP=$(date +%Y%m%d-%H%M%S)
RECIPIENT=$(awk '/age:/ {print $2}' .sops.yaml)

# Interpolação do compose exige POSTGRES_PASSWORD (env gerado pelo deploy.sh)
export COMPOSE_ENV_FILES=/run/genesys/.env GENESYS_ENV_FILE=/run/genesys/.env

mkdir -p "$DEST"
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' \
  | age -r "$RECIPIENT" > "$DEST/db-$STAMP.sql.age"
tar -cz backend/users.json backend/auth_tokens.json \
  | age -r "$RECIPIENT" > "$DEST/state-$STAMP.tar.gz.age"

# Retenção: 14 dias
find "$DEST" -name '*.age' -mtime +14 -delete
