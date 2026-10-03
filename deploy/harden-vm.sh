#!/usr/bin/env bash
# Hardening da VM Ubuntu 24.04 do genesys-manager. Rodar como root, UMA vez,
# depois de copiar sua chave pública SSH para /home/deploy/.ssh/authorized_keys.
set -euo pipefail

ADMIN_CIDR="${ADMIN_CIDR:?defina ADMIN_CIDR, ex: 192.168.0.0/24}"

[ -s /home/deploy/.ssh/authorized_keys ] || {
  echo "Sem chave em /home/deploy/.ssh/authorized_keys — abortando para não se trancar fora." >&2
  exit 1
}

apt-get update
apt-get install -y ufw fail2ban unattended-upgrades age ca-certificates curl
dpkg-reconfigure -f noninteractive unattended-upgrades

# SOPS (binário oficial)
SOPS_VERSION=3.9.4
curl -fsSL -o /usr/local/bin/sops \
  "https://github.com/getsops/sops/releases/download/v${SOPS_VERSION}/sops-v${SOPS_VERSION}.linux.amd64"
chmod 0755 /usr/local/bin/sops

# Docker oficial + usuário deploy no grupo docker
curl -fsSL https://get.docker.com | sh
usermod -aG docker deploy

# SSH: só chave, sem root, só o usuário deploy, só forwarding local
cat > /etc/ssh/sshd_config.d/10-hardening.conf <<'CONF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
AllowUsers deploy
AllowTcpForwarding local
X11Forwarding no
AllowAgentForwarding no
MaxAuthTries 3
LoginGraceTime 30
CONF
sshd -t && systemctl reload ssh

# Firewall: só SSH da rede de gestão. Docker publica 8082 apenas em 127.0.0.1.
ufw default deny incoming
ufw default allow outgoing
ufw allow from "$ADMIN_CIDR" to any port 22 proto tcp
ufw --force enable

systemctl enable --now fail2ban
echo "Hardening concluído. Teste um NOVO login SSH antes de fechar esta sessão."
