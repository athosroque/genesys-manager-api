#!/usr/bin/env bash
# Descriptografa backend/.env.enc em tmpfs e sobe a stack.
# O .env em claro só existe em /run (RAM) — some no reboot e nunca toca o disco.
set -euo pipefail

cd "$(dirname "$0")/.."

ENV_DIR=/run/genesys
ENV_FILE="$ENV_DIR/.env"

command -v sops >/dev/null || { echo "sops não instalado" >&2; exit 1; }
[ -f backend/.env.enc ] || { echo "backend/.env.enc não encontrado" >&2; exit 1; }

[ -w "$ENV_DIR" ] || sudo install -d -m 0700 -o "$(id -u)" -g "$(id -g)" "$ENV_DIR"
umask 077
sops --decrypt --input-type dotenv --output-type dotenv backend/.env.enc > "$ENV_FILE"

# --env-file alimenta a interpolação (CLOUDFLARE_TUNNEL_TOKEN do cloudflared);
# GENESYS_ENV_FILE alimenta o env_file do backend.
export GENESYS_ENV_FILE="$ENV_FILE"
docker compose --env-file "$ENV_FILE" --profile "${COMPOSE_PROFILE:-tunnel}" up -d --build "$@"
