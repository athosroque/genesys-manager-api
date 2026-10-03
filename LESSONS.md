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
