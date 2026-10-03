#!/usr/bin/env bash
# Arquivos de estado (users.json, auth_tokens.json), criptografados com age
# (chave pública do .sops.yaml). Não há banco: o estado vive nesses arquivos.
set -euo pipefail

cd "$(dirname "$0")/.."

DEST="${BACKUP_DIR:-/var/backups/genesys}"
STAMP=$(date +%Y%m%d-%H%M%S)
RECIPIENT=$(awk '/age:/ {print $2}' .sops.yaml)

mkdir -p "$DEST"
tar -cz backend/users.json backend/auth_tokens.json \
  | age -r "$RECIPIENT" > "$DEST/state-$STAMP.tar.gz.age"

# Retenção: 14 dias
find "$DEST" -name '*.age' -mtime +14 -delete
