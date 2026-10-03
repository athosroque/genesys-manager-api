# Handoff — finalizar migração do genesys-manager-api na VM

> Documento para o Claude Code rodando **dentro da VM**. Leia inteiro antes de
> executar qualquer coisa. Idioma: português (Brasil).

## Contexto

O genesys-manager-api (FastAPI + Vue/nginx + Postgres) está saindo do servidor
antigo (`192.168.0.101`) para esta VM isolada no Proxmox. A parte de código já
foi feita na branch `security/hardening-proxmox`:

- auth obrigatória em todas as rotas, rate limit no login, Swagger off em produção;
- containers não-root, rootfs read-only, Postgres sem porta publicada (rede interna);
- segredos em `backend/.env.enc` via **SOPS + age**, descriptografados só em
  tmpfs (`/run/genesys/.env`) por `scripts/deploy.sh`;
- runbook completo em `docs/MIGRACAO-PROXMOX.md` (referência principal).

## Estado atual (já feito pelo usuário)

| Item | Status |
|---|---|
| VM `102 - genesys-manager`, Ubuntu 24.04, disco LUKS | ✅ |
| IP fixo `192.168.0.110/24`, gateway `192.168.0.1` | ✅ |
| Usuário `deploy`, SSH por chave | ✅ |
| `harden-vm.sh` executado (UFW, fail2ban, sshd, Docker, sops, age) | ✅ (validar — passo 1) |
| PC admin (Windows) | `192.168.0.13` |
| Chave age gerada, privada no Bitwarden | ✅ |
| Segredos novos gerados e guardados no Bitwarden | ✅ |
| Túnel Cloudflare novo criado (token no Bitwarden) | ✅ |
| Cloudflare Access | ⏸️ **decisão adiada pelo usuário — não configurar** |
| Firewall do Proxmox | configurado pelo usuário no host (fora do alcance da VM) |

## Regras de segurança (obrigatórias)

1. **Nunca** imprimir, ecoar, logar ou commitar valores de segredo. Ao validar,
   mostre só nomes de variáveis (`sed 's/=.*/=***/'`).
2. O usuário fornece os segredos. Peça para ele **colar direto no editor**
   (`nano`/`sops`) quando possível, em vez de colar no chat.
3. A chave age privada (`AGE-SECRET-KEY-...`) só existe em
   `~/.config/sops/age/keys.txt` (0600). Nunca no repositório.
4. `backend/.env` em claro deve existir apenas o tempo de criptografar, depois
   `shred -u`.
5. Não rodar `docker compose down -v` (apaga o volume do Postgres).
6. Commits só quando o usuário pedir, em Conventional Commits, em português.

## Passo 1 — Validar o hardening

```bash
sudo ufw status verbose                 # esperado: deny incoming; 22/tcp ALLOW 192.168.0.13
sudo sshd -T | grep -Ei '^(passwordauthentication|permitrootlogin|allowusers|allowtcpforwarding|maxauthtries) '
#   passwordauthentication no / permitrootlogin no / allowusers deploy / allowtcpforwarding local
systemctl is-active fail2ban unattended-upgrades docker
id deploy | grep -q docker && echo "deploy no grupo docker"
sops --version; age --version; docker compose version
lsblk -o NAME,TYPE,FSTYPE | grep -i crypt   # confirma LUKS
ss -tlnp                                    # só 22 (e 127.0.0.53 do resolved)
```

Qualquer divergência: corrigir e reportar ao usuário antes de seguir.

## Passo 2 — Trazer o código

O repositório é `https://github.com/athosroque/genesys-manager-api.git`. Pergunte
ao usuário qual opção ele escolheu:

- **(a)** ele fez push da branch → `sudo install -d -o deploy -g deploy /opt/genesys-manager-api && git clone -b security/hardening-proxmox <repo> /opt/genesys-manager-api`
- **(b)** ele copiou via rsync/scp para `/opt/genesys-manager-api`

Confira: `git -C /opt/genesys-manager-api log --oneline -7` deve mostrar os
commits `fix(security)`, `chore(infra)`, `feat(infra)` e `.sops.yaml` com uma
chave `age1...` (pública). Se `.sops.yaml` ainda tiver `AGE_PUBLIC_KEY`, pedir a
chave pública ao usuário e substituir.

## Passo 3 — Chave age

Usuário cola o conteúdo da nota do Bitwarden:

```bash
install -d -m 700 ~/.config/sops/age
nano ~/.config/sops/age/keys.txt        # usuário cola; salvar
chmod 600 ~/.config/sops/age/keys.txt
age-keygen -y ~/.config/sops/age/keys.txt   # imprime a PÚBLICA — deve bater com .sops.yaml
```

## Passo 4 — Montar e criptografar o `.env`

```bash
cd /opt/genesys-manager-api
cp backend/.env.example backend/.env && chmod 600 backend/.env
nano backend/.env
```

Valores esperados (o usuário fornece os secretos):

| Variável | Valor |
|---|---|
| `ENVIRONMENT` | `production` |
| `COOKIE_DOMAIN` | vazio |
| `CORS_ORIGINS` | `https://genesys.projetoathos.com.br` |
| `GENESYS_CLIENT_ID` / `GENESYS_CLIENT_SECRET` | **usuário** (secret regenerado) |
| `GENESYS_REGION` | `sae1.pure.cloud` |
| `JWT_SECRET_KEY` | **usuário** (64 hex) |
| `JWT_ALGORITHM` / `JWT_EXPIRE_MINUTES` | `HS256` / `2880` |
| `RESEND_API_KEY` | **usuário** (nova) |
| `RESEND_FROM_EMAIL` | **usuário** |
| `APP_BASE_URL` | `https://genesys.projetoathos.com.br` |
| `ALLOWED_EMAIL_DOMAIN` | `claro.com.br` (confirmar com usuário) |
| `MAGIC_LINK_EXPIRE_MINUTES` | `10` |
| `CLOUDFLARE_API_TOKEN` / `_ACCOUNT_ID` / `_ZONE_ID` | **usuário** |
| `POSTGRES_PASSWORD` | **usuário** (hex) |
| `DATABASE_URL` | `postgresql+psycopg://postgres:<POSTGRES_PASSWORD>@db:5432/genesys_manager` |
| `CLOUDFLARE_TUNNEL_TOKEN` | **usuário** |

Validar sem expor valores e criptografar:

```bash
sed 's/=.*/=***/' backend/.env | grep -v '^#' | grep .
# checagens automáticas (não imprimem valores):
. <(grep -E '^(POSTGRES_PASSWORD|DATABASE_URL|JWT_SECRET_KEY)=' backend/.env)
[ ${#JWT_SECRET_KEY} -ge 32 ] && echo "JWT ok"
[[ "$DATABASE_URL" == *":${POSTGRES_PASSWORD}@db:5432/"* ]] && echo "DATABASE_URL bate com POSTGRES_PASSWORD"
[[ "$DATABASE_URL" == postgresql+psycopg://* ]] && echo "driver ok"
unset POSTGRES_PASSWORD DATABASE_URL JWT_SECRET_KEY

sops --encrypt --input-type dotenv --output-type dotenv backend/.env > backend/.env.enc
sops --decrypt --input-type dotenv --output-type dotenv backend/.env.enc | sed 's/=.*/=***/' | head -3  # prova que descriptografa
shred -u backend/.env
```

## Passo 4.1 — Variáveis do compose no shell

O `docker-compose.yml` exige `POSTGRES_PASSWORD` na interpolação, então **todo**
`docker compose` fora do `deploy.sh` (`ps`, `exec`, `logs`) precisa apontar para
o env descriptografado. Adicionar uma vez ao `~/.bashrc` do `deploy`:

```bash
cat >> ~/.bashrc <<'RC'
export COMPOSE_ENV_FILES=/run/genesys/.env
export GENESYS_ENV_FILE=/run/genesys/.env
export SOPS_AGE_KEY_FILE=$HOME/.config/sops/age/keys.txt
RC
source ~/.bashrc
docker compose version   # COMPOSE_ENV_FILES exige Compose >= 2.24
```

`/run/genesys/.env` só existe depois do primeiro `deploy.sh` (Passos 6/7).
`backup.sh` e a unit systemd já exportam essas variáveis.

## Passo 5 — Postgres 16

Volume novo, então pode subir direto na 16. Em `docker-compose.yml`, trocar
`postgres:15-alpine` → `postgres:16-alpine` e remover o comentário de upgrade.

## Passo 6 — Migrar dados

O usuário traz do servidor antigo (`192.168.0.101`) para `/tmp` da VM:
`genesys.sql` (pg_dump) e `users.json`. Comando no servidor antigo:
`docker exec genesys-manager-api-db-1 pg_dump -U postgres genesys_manager > /tmp/genesys.sql`.

```bash
cd /opt/genesys-manager-api
install -m 600 /tmp/users.json backend/users.json
echo '{"tokens": []}' > backend/auth_tokens.json && chmod 600 backend/auth_tokens.json
COMPOSE_PROFILE=none ./scripts/deploy.sh db
sleep 5
docker compose exec -T db psql -U postgres -d genesys_manager -v ON_ERROR_STOP=1 < /tmp/genesys.sql
docker compose exec -T db psql -U postgres -d genesys_manager -c '\dt'
shred -u /tmp/genesys.sql /tmp/users.json
```

Se não houver dump (banco vazio aceitável), pular o restore e confirmar com o usuário.

## Passo 7 — Subir a stack completa + systemd

```bash
sudo cp deploy/genesys-manager.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now genesys-manager
systemctl status genesys-manager --no-pager
docker compose ps
docker compose logs --tail=50 backend cloudflared
```

Observação: o serviço usa `RuntimeDirectory=genesys`, que cria `/run/genesys`
com dono `deploy`. Se `deploy.sh` reclamar de permissão, conferir isso.

## Passo 8 — Validação final (todos devem passar)

```bash
# containers e isolamento
docker compose exec backend id                         # uid=1000(app)
docker inspect -f '{{.Name}} ro={{.HostConfig.ReadonlyRootfs}}' $(docker compose ps -q)
docker compose exec backend python -c "import socket; socket.create_connection(('db',5432),2); print('db ok')"
docker compose exec db sh -c 'wget -q -T3 -O- https://1.1.1.1 && echo VAZOU || echo "db sem internet ok"'
ss -tlnp | grep -E ':5432|:8082'                       # 8082 só em 127.0.0.1; 5432 ausente

# app
curl -s -o /dev/null -w '%{http_code}\n' localhost:8082/                   # 200
curl -s localhost:8082/api/health                                           # {"status":"ok"}
curl -s -o /dev/null -w '%{http_code}\n' localhost:8082/api/tickets/        # 401
curl -s -o /dev/null -w '%{http_code}\n' localhost:8082/api/docs            # 404
curl -sI localhost:8082/ | grep -Ei 'content-security|x-frame|strict-transport'

# segredos
ls -l /run/genesys/.env                                # existe, 600, deploy
test ! -e backend/.env && echo "sem .env em claro no disco"
git status --short                                     # .env.enc pode aparecer; nada de .env

# testes dentro da imagem (rede interna alcança o db)
docker compose run --rm --no-deps -v "$PWD/backend:/app" -e ENVIRONMENT=test backend python -m pytest -q -p no:cacheprovider
#   esperado: tudo passa exceto 3 falhas pré-existentes em test_user_audit.py
```

Pelo PC do usuário: `ssh -L 8082:127.0.0.1:8082 deploy@192.168.0.110` e abrir
`http://localhost:8082` — login via magic link deve funcionar.

Reboot: `sudo reboot` → destravar LUKS no console do Proxmox → após o boot,
`docker compose ps` deve mostrar tudo `running` sem intervenção.

## Passo 9 — Backup

```bash
sudo install -d -o deploy -g deploy /var/backups/genesys
./scripts/backup.sh && ls -l /var/backups/genesys
( crontab -l 2>/dev/null; echo '0 3 * * * /opt/genesys-manager-api/scripts/backup.sh' ) | crontab -
```

Lembrar o usuário: `vzdump` semanal da VM no Proxmox (Datacenter → Backup).

## Fora do escopo desta VM (apenas lembrar o usuário)

- **Cutover Cloudflare:** apontar o Public Hostname do túnel novo para
  `http://frontend:8080` e remover o hostname do túnel antigo (`homelab-backend`)
  — só depois do Passo 8 passar.
- **Cloudflare Access:** decisão adiada pelo usuário.
- **Servidor antigo:** `docker compose down`, `docker image rm genesys-manager-api-backend`
  (imagem antiga contém o `.env`), `shred -u backend/.env`.
- Commitar `backend/.env.enc` e a troca para Postgres 16 quando o usuário pedir.

## Relatório final esperado

Ao terminar, entregar ao usuário uma tabela com cada verificação do Passo 8
(✅/❌ + observação), o que ficou pendente e qualquer desvio deste documento.
Registrar gotchas novos em `LESSONS.md` no formato do arquivo.
