"""
Envio de e-mails via API HTTP do Resend (magic link de acesso).
"""
from __future__ import annotations

import logging

import httpx

from auth_local import is_allowed_email_domain
from config import settings

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


def build_magic_link_url(raw_token: str) -> str:
    """
    URL pública do verify.

    Em produção o nginx do frontend recebe `/api/*` e encaminha ao backend
    sem o prefixo `/api`. O link no e-mail precisa incluir `/api` para o
    navegador bater no proxy correto:
      {APP_BASE_URL}/api/auth/verify?token=...
    """
    base = settings.APP_BASE_URL.rstrip("/")
    return f"{base}/api/auth/verify?token={raw_token}"


def _resend_failure_message(response: httpx.Response) -> str:
    """Traduz erro HTTP do Resend em mensagem acionável (PT-BR)."""
    raw_body = (response.text or "").strip()
    api_message = ""
    try:
        data = response.json()
        if isinstance(data, dict):
            api_message = str(data.get("message") or "").strip()
    except Exception:
        api_message = ""

    combined = f"{api_message} {raw_body}".lower()
    if (
        "verify a domain" in combined
        or "only send testing emails" in combined
        or "onboarding@resend.dev" in combined
    ):
        return (
            "O Resend recusou o envio: com o remetente sandbox "
            "(onboarding@resend.dev) só é possível enviar para o e-mail da "
            "conta Resend. Verifique um domínio em https://resend.com/domains "
            "e configure RESEND_FROM_EMAIL com um endereço desse domínio."
        )

    detail = api_message or raw_body or f"HTTP {response.status_code}"
    return f"Falha ao enviar e-mail (Resend HTTP {response.status_code}): {detail}"


def send_magic_link(to_email: str, raw_token: str) -> None:
    """
    Envia o e-mail com o link de acesso (válido por MAGIC_LINK_EXPIRE_MINUTES).
    Recusa destinatários fora de ALLOWED_EMAIL_DOMAIN antes de chamar o Resend.
    Levanta RuntimeError se o domínio for inválido, a API key estiver ausente
    ou o envio falhar.
    """
    if not is_allowed_email_domain(to_email):
        raise RuntimeError(
            f"Envio recusado: destinatário deve ser @{settings.ALLOWED_EMAIL_DOMAIN}."
        )

    if not settings.RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY não configurada.")

    link = build_magic_link_url(raw_token)
    minutes = settings.MAGIC_LINK_EXPIRE_MINUTES

    html = f"""
    <div style="font-family: sans-serif; max-width: 520px; margin: 0 auto;">
      <h2 style="color: #111;">Genesys Manager — link de acesso</h2>
      <p>Clique no botão abaixo para entrar. O link é de uso único e expira em
      <strong>{minutes} minutos</strong>.</p>
      <p style="margin: 28px 0;">
        <a href="{link}"
           style="background:#e11d48;color:#fff;padding:12px 20px;
                  text-decoration:none;border-radius:6px;display:inline-block;">
          Acessar a plataforma
        </a>
      </p>
      <p style="color:#666;font-size:13px;">
        Ao abrir o link no navegador, o acesso é concluído automaticamente.
        Scanners de e-mail não consomem o link.<br><br>
        Se o botão não funcionar, copie e cole este endereço no navegador:<br>
        <a href="{link}">{link}</a>
      </p>
      <p style="color:#999;font-size:12px;">
        Se você não solicitou este acesso, ignore este e-mail.
      </p>
    </div>
    """

    try:
        response = httpx.post(
            RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": settings.RESEND_FROM_EMAIL,
                "to": [to_email],
                "subject": "Seu link de acesso — Genesys Manager",
                "html": html,
            },
            timeout=30.0,
        )
    except httpx.RequestError as exc:
        logger.exception("Falha de rede ao chamar Resend para %s", to_email)
        raise RuntimeError(f"Falha ao enviar e-mail: erro de rede ({exc})") from exc

    if response.is_success:
        return

    logger.error(
        "Resend recusou magic link para %s: HTTP %s body=%s",
        to_email,
        response.status_code,
        response.text,
    )
    raise RuntimeError(_resend_failure_message(response))
