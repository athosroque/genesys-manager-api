"""
Explorador da Platform Audit API — Genesys Cloud
================================================

Script de estudo/validação. Roda fora do FastAPI, direto no venv do backend,
usando as mesmas variáveis do backend/.env.

Uso:
    # 1. Ver a árvore completa de serviços -> entidades -> ações da SUA org
    python explorar_auditoria.py --mapa

    # 2. Coletar amostras reais de um serviço (últimos 7 dias) e perfilar o schema
    python explorar_auditoria.py --amostra PeoplePermissions
    python explorar_auditoria.py --amostra ContactCenter --dias 30 --entidade Queue
    python explorar_auditoria.py --amostra UsersRules --dias 30 --max 200

Saídas:
    amostras/<servico>_raw.json      -> eventos crus, para abrir e estudar
    amostras/<servico>_perfil.txt    -> relatório: schema real, contagens, padrões

O relatório responde às perguntas de estudo:
    - Quais entityType x action realmente ocorrem na org (não só o que o mapa diz)?
    - Quais campos vêm preenchidos e com que frequência (user.name? entity.id? client?)
    - Que formatos aparecem em propertyChanges.property (padrões, com UUIDs mascarados)?
    - Que chaves aparecem em `context` por serviço?
    - Quem faz as mudanças: humanos (user) ou integrações (client)?
"""

import argparse
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass  # ok se as vars já estiverem exportadas

REGION = os.getenv("GENESYS_REGION", "sae1.pure.cloud")
CLIENT_ID = os.getenv("GENESYS_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("GENESYS_CLIENT_SECRET", "")
API = f"https://api.{REGION}"
LOGIN = f"https://login.{REGION}"

UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)


def get_token() -> str:
    r = httpx.post(
        f"{LOGIN}/oauth/token",
        data={"grant_type": "client_credentials"},
        auth=(CLIENT_ID, CLIENT_SECRET),
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def gc(method: str, path: str, token: str, **kw) -> dict:
    r = httpx.request(
        method, f"{API}{path}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30, **kw,
    )
    if r.status_code == 403:
        sys.exit("403 — a integração não tem a permissão audits:audit:view.")
    r.raise_for_status()
    return r.json() if r.text else {}


# ---------------------------------------------------------------------------
# --mapa
# ---------------------------------------------------------------------------
def cmd_mapa(token: str) -> None:
    data = gc("GET", "/api/v2/audits/query/servicemapping", token)
    services = data.get("services", [])
    print(f"\n{len(services)} serviços auditáveis na org ({REGION}):\n")
    for svc in services:
        # A API pode usar 'name'/'entities' ou 'serviceName'/'entityTypes'
        # dependendo da versão — tratamos os dois.
        sname = svc.get("name") or svc.get("serviceName")
        ents = svc.get("entities") or svc.get("entityTypes") or []
        print(f"■ {sname}  ({len(ents)} entidades)")
        for ent in ents:
            ename = ent.get("name") or ent.get("entityType")
            actions = ent.get("actions", [])
            print(f"    ├─ {ename}: {', '.join(actions)}")
        print()
    Path("amostras").mkdir(exist_ok=True)
    out = Path("amostras/servicemapping_raw.json")
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"JSON cru salvo em {out}")


# ---------------------------------------------------------------------------
# --amostra
# ---------------------------------------------------------------------------
def coletar(token: str, service: str, dias: int, entidade: str | None,
            max_eventos: int) -> list[dict]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=dias)
    payload: dict = {
        "interval": f"{start.strftime('%Y-%m-%dT%H:%M:%SZ')}/"
                    f"{end.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "serviceName": service,
        "sort": [{"name": "Timestamp", "sortOrder": "desc"}],
    }
    if entidade:
        payload["filters"] = [{"property": "EntityType", "value": entidade}]

    created = gc("POST", "/api/v2/audits/query", token, json=payload)
    tid, state = created["id"], created.get("state", "Queued")
    print(f"transactionId={tid}  state inicial={state}")

    while state not in ("Succeeded", "Failed", "Cancelled"):
        time.sleep(2)
        state = gc("GET", f"/api/v2/audits/query/{tid}", token).get("state")
        print(f"  polling... state={state}")
    if state != "Succeeded":
        sys.exit(f"Consulta terminou como {state}.")

    eventos, cursor = [], None
    while len(eventos) < max_eventos:
        params = {"pageSize": min(100, max_eventos - len(eventos))}
        if cursor:
            params["cursor"] = cursor
        page = gc("GET", f"/api/v2/audits/query/{tid}/results", token, params=params)
        batch = page.get("entities", [])
        eventos.extend(batch)
        cursor = page.get("cursor")
        print(f"  página com {len(batch)} eventos (total {len(eventos)})")
        if not cursor or not batch:
            break
    return eventos


def _mask(v: str) -> str:
    return UUID_RE.sub("<uuid>", str(v))


def _flatten_keys(obj, prefix="") -> list[str]:
    keys = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else k
            keys.append(path)
            keys.extend(_flatten_keys(v, path))
    elif isinstance(obj, list) and obj:
        keys.extend(_flatten_keys(obj[0], prefix + "[]"))
    return keys


def perfilar(eventos: list[dict], service: str) -> str:
    n = len(eventos)
    lines = [f"PERFIL DE RETORNO — {service}", f"Eventos analisados: {n}", "=" * 60]
    if not n:
        lines.append("Nenhum evento no período. Amplie --dias ou remova --entidade.")
        return "\n".join(lines)

    # 1. EntityType x Action que realmente ocorrem
    combo = Counter((e.get("entityType"), e.get("action")) for e in eventos)
    lines.append("\n1) entityType x action observados:")
    for (et, ac), c in combo.most_common():
        lines.append(f"   {et:<25} {ac:<20} {c:>5}x")

    # 2. Preenchimento de campos (schema real)
    presence = Counter()
    for e in eventos:
        for k in set(_flatten_keys(e)):
            presence[k] += 1
    lines.append("\n2) Campos presentes (% dos eventos):")
    for k, c in sorted(presence.items()):
        lines.append(f"   {k:<45} {100 * c / n:>5.1f}%")

    # 3. Valores realmente preenchidos (não só presentes)
    def filled(getter):
        return sum(1 for e in eventos if getter(e))
    lines.append("\n3) Campos-chave com valor não-vazio:")
    checks = {
        "user.id (autor humano)": lambda e: (e.get("user") or {}).get("id"),
        "user.name": lambda e: (e.get("user") or {}).get("name"),
        "client.id (via integração/API)": lambda e: (e.get("client") or {}).get("id"),
        "entity.id": lambda e: (e.get("entity") or {}).get("id"),
        "entity.name": lambda e: (e.get("entity") or {}).get("name"),
        "remoteIp": lambda e: e.get("remoteIp"),
        "propertyChanges (>=1)": lambda e: e.get("propertyChanges"),
        "context (>=1 chave)": lambda e: e.get("context"),
    }
    for label, fn in checks.items():
        lines.append(f"   {label:<35} {100 * filled(fn) / n:>5.1f}%")

    # 4. Padrões de propertyChanges.property (UUIDs mascarados)
    props = Counter()
    val_patterns = Counter()
    for e in eventos:
        for pc in e.get("propertyChanges") or []:
            props[_mask(pc.get("property", ""))] += 1
            for v in (pc.get("newValues") or []):
                if v:
                    val_patterns[_mask(v)[:60]] += 1
    lines.append("\n4) Padrões de propertyChanges.property:")
    for p, c in props.most_common(20):
        lines.append(f"   {c:>4}x  {p}")
    lines.append("\n   Padrões de newValues (top 15):")
    for p, c in val_patterns.most_common(15):
        lines.append(f"   {c:>4}x  {p}")

    # 5. Chaves de context por serviço
    ctx_keys = Counter()
    for e in eventos:
        for k in (e.get("context") or {}):
            ctx_keys[k] += 1
    lines.append("\n5) Chaves em context:")
    lines.append("   " + (", ".join(f"{k} ({c}x)" for k, c in ctx_keys.most_common())
                          or "(sempre vazio neste serviço)"))

    # 6. Um evento completo de cada action, como exemplo de estudo
    lines.append("\n6) Um exemplo cru por action (ver *_raw.json para todos):")
    seen = set()
    for e in eventos:
        if e.get("action") not in seen:
            seen.add(e.get("action"))
            lines.append(json.dumps(e, indent=2, ensure_ascii=False)[:1500])
            lines.append("-" * 60)
    return "\n".join(lines)


def cmd_amostra(token: str, service: str, dias: int, entidade: str | None,
                max_eventos: int) -> None:
    eventos = coletar(token, service, dias, entidade, max_eventos)
    Path("amostras").mkdir(exist_ok=True)
    raw = Path(f"amostras/{service}_raw.json")
    raw.write_text(json.dumps(eventos, indent=2, ensure_ascii=False))
    relatorio = perfilar(eventos, service)
    txt = Path(f"amostras/{service}_perfil.txt")
    txt.write_text(relatorio)
    print("\n" + relatorio)
    print(f"\nArquivos: {raw}  |  {txt}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mapa", action="store_true", help="Imprime o servicemapping")
    ap.add_argument("--amostra", metavar="SERVICO", help="Coleta e perfila um serviço")
    ap.add_argument("--dias", type=int, default=7)
    ap.add_argument("--entidade", default=None, help="Filtra por EntityType")
    ap.add_argument("--max", type=int, default=300, dest="max_eventos")
    args = ap.parse_args()

    if not (CLIENT_ID and CLIENT_SECRET):
        sys.exit("Defina GENESYS_CLIENT_ID/SECRET (backend/.env).")

    tk = get_token()
    if args.mapa:
        cmd_mapa(tk)
    elif args.amostra:
        cmd_amostra(tk, args.amostra, args.dias, args.entidade, args.max_eventos)
    else:
        ap.print_help()
