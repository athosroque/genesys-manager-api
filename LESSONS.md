# LESSONS — genesys-manager-api

### [tags: docker, seguranca, segredos]
**Sintoma:** `docker run --entrypoint sh genesys-manager-api-backend -c 'ls -a /app'` mostrava `.env`, JSONs de amostra com PII e `tickets_enriched.db` dentro da imagem.
**Causa:** o `Dockerfile` faz `COPY . .`, e o `.dockerignore` só excluía `.venv`/`__pycache__`. O `.gitignore` **não** vale para o build — o `.env` entrava na imagem mesmo estando gitignored.
**Solução:** `.dockerignore` com `.env`, `.env.*`, `*.json`, `*.db`, scripts `consultar_*`/`check_perms*` e testes. Verificar sempre a imagem final com `ls -a /app`. Imagens antigas devem ser apagadas e os segredos rotacionados.
**Custo do aprendizado:** ~10min (achado na auditoria de segurança).

### [tags: docker, postgres, sqlalchemy]
**Sintoma:** depois de um `docker compose build` limpo, o backend quebrava no import com `ModuleNotFoundError: No module named 'psycopg'`. A imagem antiga funcionava.
**Causa:** o `DATABASE_URL` usa `postgresql+psycopg://` (psycopg 3), mas o `requirements.txt` só tinha `psycopg2-binary`. A imagem antiga tinha o pacote de um build anterior, e o cache escondia o problema.
**Solução:** adicionar `psycopg[binary]` ao `requirements.txt`. Validar mudanças de dependência com `docker compose build --no-cache`.
**Custo do aprendizado:** ~10min.

### [tags: nginx, seguranca, headers]
**Sintoma:** headers de segurança (`X-Frame-Options`, CSP) definidos no bloco `server` não apareciam nas respostas de `/index.html` e `/api/`.
**Causa:** no nginx, um `add_header` dentro de um `location` **substitui** todos os herdados do `server`, não soma a eles.
**Solução:** headers em `frontend/security-headers.conf`, com `include` no `server` e em todo `location` que tenha `add_header` próprio.
**Custo do aprendizado:** ~5min (gotcha conhecido, fácil de esquecer).

### [tags: pytest, config]
**Sintoma:** com o fail-fast de produção no `config.py`, a coleta do pytest abortava com `RuntimeError: Configuração insegura`.
**Causa:** o `backend/.env` local tem `ENVIRONMENT=production`, e o `load_dotenv()` carrega o valor no import.
**Solução:** `backend/conftest.py` define `os.environ["ENVIRONMENT"] = "test"` antes de qualquer import (o `load_dotenv` não sobrescreve variáveis que já existem).
**Custo do aprendizado:** ~5min.

### [tags: docker, compose, config]
**Sintoma:** o `.env.enc` tinha `CORS_ORIGINS=https://manager-genesys.projetoathos.com.br`, mas o backend continuaria aceitando só `https://genesys.projetoathos.com.br`.
**Causa:** o `docker-compose.yml` fixava `CORS_ORIGINS` no bloco `environment:` do backend. No Compose, `environment:` tem prioridade sobre `env_file:`, então o valor do arquivo de segredos era ignorado sem nenhum aviso.
**Solução:** tirar `CORS_ORIGINS` do `environment:` e deixar o `.env.enc` como única fonte. Conferir o valor efetivo com `docker compose config --format json` (filtrando só as chaves de interesse, para não imprimir segredos).
**Custo do aprendizado:** ~5min (achado na migração para a VM).

### [tags: sops, segredos]
**Sintoma:** `sops --encrypt ... backend/.env > backend/.env.enc` falharia com "no matching creation rules found".
**Causa:** o sops escolhe a regra do `.sops.yaml` pelo caminho do arquivo de **entrada**, e a regra casa com `\.env\.enc$`, não com `backend/.env`.
**Solução:** `sops --encrypt --filename-override backend/.env.enc --input-type dotenv --output-type dotenv backend/.env > backend/.env.enc`.
**Custo do aprendizado:** ~2min.

### [tags: docker, compose, rede]
**Sintoma:** na VM nova, `127.0.0.1:8082` não abria. O `docker inspect` mostrava `PortBindings` certo, mas `NetworkSettings.Ports` vinha `null`, e o `ss` não listava a porta.
**Causa:** o frontend estava só na rede `genesys-internal` (`internal: true`). O Docker Engine recente (29.x na VM) não publica portas de containers ligados apenas a redes internas. No servidor antigo, com Docker mais velho, publicava.
**Solução:** rede extra `genesys-publish` só para o frontend, com `com.docker.network.bridge.enable_ip_masquerade: "false"`. A porta volta a ser publicada, e sem NAT de saída o frontend continua sem internet (conferir com `wget https://1.1.1.1` de dentro do container).
**Custo do aprendizado:** ~10min.

### [tags: docker, compose, bind-mount]
**Sintoma:** `install -m 600 /tmp/users.json backend/users.json` falhou com `Permission denied` em `backend/users.json/users.json`.
**Causa:** um `docker compose run backend ...` rodou antes de os arquivos existirem, e o Docker criou `backend/users.json` e `backend/auth_tokens.json` como **diretórios** de root para os bind mounts.
**Solução:** `sudo rmdir` nos diretórios vazios e criar os arquivos **antes** de qualquer `docker compose run/up`. Para testes, usar `docker run` puro sobre uma cópia do `backend/` sem os arquivos de estado. Os testes não isolam o `USERS_FILE` e podem gravar no `users.json` real.
**Custo do aprendizado:** ~5min.

### [tags: cloudflare, tunnel, firewall]
**Sintoma:** o `cloudflared` ficava em loop com `failed to dial to edge with quic: timeout` e, com `--protocol http2`, `dial tcp ...:7844: i/o timeout`.
**Causa:** o túnel conecta na borda da Cloudflare pela porta **7844** (UDP para QUIC, TCP para http2), nunca pela 443. O firewall do Proxmox só liberava saída em `tcp/443`.
**Solução:** liberar a saída `tcp/7844` no firewall do Proxmox e fixar `--protocol http2` no compose, para não depender de UDP. Testar do host com `timeout 5 bash -c '</dev/tcp/198.41.192.167/7844'`.
**Custo do aprendizado:** ~10min.
