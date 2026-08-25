from __future__ import annotations

import os
import httpx

RESEND_API_URL = "https://api.resend.com/emails"


async def send_email(*, to: str, subject: str, html: str) -> dict:
    api_key = os.getenv("RESEND_API_KEY", "")
    if not api_key:
        raise RuntimeError("RESEND_API_KEY is not configured")

    from_email = os.getenv("BITEY_TRAINER_FROM_EMAIL", "onboarding@resend.dev")
    payload = {
        "from": from_email,
        "to": [to],
        "subject": subject,
        "html": html,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(RESEND_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()


async def send_trainer_test_email() -> dict:
    to = os.getenv("BITEY_TRAINER_REPORT_EMAIL", "")
    if not to:
        raise RuntimeError("BITEY_TRAINER_REPORT_EMAIL is not configured")
    html = """
    <h1>Bitey Trainer — prueba de email_notification</h1>
    <p><strong>Estado:</strong> conexión con Resend funcionando.</p>
    <p>Este es un correo de prueba del sistema de informes de Bitey Trainer.</p>
    <ul>
      <li>Canal: Email</li>
      <li>Destino: configurado en Render</li>
      <li>Motor: Bitey Trainer / Supracerebro</li>
    </ul>
    <p>La siguiente etapa será enviar informes reales de oportunidades laborales.</p>
    """
    return await send_email(to=to, subject="Bitey Trainer — email_notification de prueba", html=html)
