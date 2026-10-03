# Migração para VM isolada no Proxmox

Runbook para mover o genesys-manager-api para uma VM dedicada, com segredos em
SOPS + age, acesso administrativo só por SSH tunnel e domínio público atrás do
Cloudflare Access.

**Decisão: uma VM só.** A stack é pequena (frontend + backend + Postgres) e o
isolamento interno já vem das redes Docker (`genesys-internal` sem saída para a
internet; Postgres sem porta publicada). Uma segunda VM só para o banco
acrescentaria tráfego entre VMs exposto na rede e mais um sistema para manter
atualizado, sem ganho real de segurança.

## 1. Criar a VM (Proxmox)

- Ubuntu Server 24.04 minimal, 2 vCPU, 4 GB RAM, 32 GB de disco.
- Disco criptografado: LUKS no instalador **ou** dataset ZFS com `encryption=on` no storage.
- Rede: bridge/VLAN dedicada (ex.: `vmbr1`, VLAN 30), sem acesso às outras VMs do homelab.
- Firewall do Proxmox (Datacenter → VM → Firewall, `enable: 1`, policy IN = DROP):
  - IN: `tcp/22` só a partir da rede de gestão.
  - OUT: `tcp/443` e `udp/53`, `udp/123` (Genesys, Resend, Cloudflare, Docker Hub, apt).
- Durante a instalação: criar o usuário `deploy`.

## 2. Hardening

```bash
# da sua máquina (chave ed25519 guardada no Bitwarden SSH agent)
ssh-copy-id deploy@<ip-vm>

# na VM
sudo ADMIN_CIDR=192.168.0.0/24 bash deploy/harden-vm.sh   # depois do clone do passo 3
```

O script configura o SSH só por chave (sem root, só `deploy`, só forwarding
local), UFW, fail2ban, atualizações automáticas, Docker, age e sops.
**Abra uma nova sessão SSH antes de fechar a atual.**

## 3. Código e segredos

```bash
sudo install -d -o deploy -g deploy /opt/genesys-manager-api
git clone <repo> /opt/genesys-manager-api && cd /opt/genesys-manager-api

# restaura a chave age a partir da nota segura do Bitwarden
install -d -m 700 ~/.config/sops/age
bw get notes "genesys-manager age key" > ~/.config/sops/age/keys.txt   # ou colar manualmente
chmod 600 ~/.config/sops/age/keys.txt
```

### Rotação obrigatória antes de criptografar

O `.env` atual ficou em texto puro numa máquina sem isolamento e também foi
**copiado para dentro das imagens Docker antigas** (o `.dockerignore` não o
excluía). Considere todos os segredos expostos e gere novos:

| Segredo | Onde rotacionar |
|---|---|
| `GENESYS_CLIENT_SECRET` | Genesys Admin → Integrations → OAuth → client → Regenerate |
| `JWT_SECRET_KEY` | `openssl rand -hex 32` (derruba todas as sessões) |
| `RESEND_API_KEY` | resend.com/api-keys → revogar a antiga, criar nova |
| `CLOUDFLARE_API_TOKEN` | dash → My Profile → API Tokens → Roll (escopo mínimo) |
| `POSTGRES_PASSWORD` | `openssl rand -hex 24`, e atualizar também o `DATABASE_URL` |
| `CLOUDFLARE_TUNNEL_TOKEN` | Zero Trust → Tunnels → criar túnel novo para a VM |

```bash
# monte o .env com os valores novos (modelo em backend/.env.example) e criptografe
sops --encrypt --input-type dotenv --output-type dotenv backend/.env > backend/.env.enc
shred -u backend/.env
git add backend/.env.enc .sops.yaml && git commit -m "chore(infra): segredos criptografados com sops"
```

## 4. Migração dos dados

No host antigo:

```bash
docker compose exec -T db pg_dump -U postgres genesys_manager > /tmp/genesys.sql
scp /tmp/genesys.sql backend/users.json deploy@<ip-vm>:/tmp/
shred -u /tmp/genesys.sql
```

Na VM (já é a hora de passar para `postgres:16-alpine` no `docker-compose.yml`):

```bash
cd /opt/genesys-manager-api
install -m 600 /tmp/users.json backend/users.json
echo '{"tokens": []}' > backend/auth_tokens.json && chmod 600 backend/auth_tokens.json  # força novo login
COMPOSE_PROFILE=none ./scripts/deploy.sh db
docker compose exec -T db psql -U postgres genesys_manager < /tmp/genesys.sql
shred -u /tmp/genesys.sql /tmp/users.json
```

## 5. Subir e validar pelo SSH tunnel

```bash
sudo cp deploy/genesys-manager.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now genesys-manager

# da sua máquina
ssh -L 8082:127.0.0.1:8082 deploy@<ip-vm>    # abra http://localhost:8082
```

## 6. Cloudflare Access + cutover

1. Zero Trust → Access → Applications → Self-hosted: `genesys.projetoathos.com.br`,
   policy *Allow* para os e-mails/domínio autorizados (OTP por e-mail ou IdP),
   sessão de 24h.
2. Zero Trust → Tunnels → túnel novo da VM → Public Hostname
   `genesys.projetoathos.com.br` → `http://frontend:8080` (cloudflared está na
   mesma rede Docker).
3. Remova o hostname do túnel antigo (`homelab-backend`, que aponta para `192.168.0.101:8082`).
4. No host antigo: `docker compose down`, `docker image rm genesys-manager-api-backend`
   (a imagem antiga contém o `.env`), `shred -u backend/.env`.

## 7. Backup

```bash
# crontab -e (usuário deploy)
0 3 * * * /opt/genesys-manager-api/scripts/backup.sh
```

Além disso, agende um `vzdump` semanal da VM no Proxmox (Datacenter → Backup).

## Checklist de verificação

- [ ] `nmap -p- <ip-vm>` a partir da LAN mostra só a porta 22.
- [ ] `ssh root@<ip-vm>` e login por senha são recusados.
- [ ] `curl -I https://genesys.projetoathos.com.br` redireciona para o Cloudflare Access.
- [ ] Pelo tunnel: `curl -s localhost:8082/api/tickets/` → 401; `/api/docs` → 404.
- [ ] `docker compose exec backend id` → `uid=1000(app)`.
- [ ] `ls /run/genesys/.env` existe; `ls /opt/genesys-manager-api/backend/.env` não existe.
- [ ] `sudo reboot` → a stack volta sozinha (systemd + deploy.sh).
- [ ] `./scripts/backup.sh` gera arquivos `.age` e um restore de teste funciona.
