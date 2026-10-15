#!/usr/bin/env python3
"""
Script de emergência: reseta 2FA de um usuário.

Uso:
    python scripts/reset_2fa.py <username>

Remove campos TOTP do users.json:
    - totp_secret_enc (segredo criptografado ativo)
    - totp_pending_enc (segredo pendente durante setup)
    - totp_last_step (último step usado para anti-replay)
    - totp_recovery_hashes (códigos de recuperação)
    - totp_enabled (flag de ativação)

Útil quando usuário perde acesso ao autenticador ou para reset emergencial.
"""
import sys
import os

# Adicionar backend/ ao path para imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import json
from auth_local import load_users, save_users


def main():
    """Reseta 2FA para o usuário especificado."""
    if len(sys.argv) != 2:
        print("Uso: python reset_2fa.py <username>", file=sys.stderr)
        sys.exit(1)

    username = sys.argv[1]

    # Carregar usuários
    users = load_users()

    # Localizar usuário
    user = next((u for u in users if u["username"] == username), None)
    if not user:
        print(f"Erro: Usuário '{username}' não encontrado.", file=sys.stderr)
        sys.exit(1)

    # Resetar campos TOTP
    user.pop("totp_secret_enc", None)
    user.pop("totp_pending_enc", None)
    user.pop("totp_last_step", None)
    user.pop("totp_recovery_hashes", None)
    user.pop("totp_enabled", None)

    # Salvar de volta
    save_users(users)

    print(f"2FA resetada para usuário '{username}'.")
    sys.exit(0)


if __name__ == "__main__":
    main()
