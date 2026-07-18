"""Transactional email via the Resend API.

Used for product events the backend controls: FTO report ready and support
notifications. Auth emails (signup confirmation, password reset, magic link)
are sent by Supabase Auth through Resend SMTP with the branded templates in
emails/ — see emails/README.md.

Deliverability practices baked in (the code-side half of staying out of
spam; the DNS half — SPF/DKIM/DMARC — is documented in emails/README.md):
- From address on a verified domain only (EMAIL_FROM env; nothing sends
  until it is configured).
- Every message carries both an HTML part and a plain-text part.
- Simple, table-based HTML with no tracking pixels, no link shorteners,
  and links only to the product domain.
- Best-effort: email failures never break the request path.
"""

import html as html_lib

import httpx

from ..config import settings

RESEND_URL = "https://api.resend.com/emails"


def render_email(
    heading: str,
    body_lines: list[str],
    cta: tuple[str, str] | None = None,
    footer_note: str = "ProblemForge — a Zawadi Technologies LLC product.",
) -> tuple[str, str]:
    """Return (html, text) parts for a branded transactional email."""
    paragraphs_html = "".join(
        f'<p style="margin:0 0 14px;font-size:15px;line-height:1.6;color:#333d4d;">'
        f"{html_lib.escape(line)}</p>"
        for line in body_lines
    )
    cta_html = ""
    if cta:
        label, url = cta
        cta_html = (
            f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:22px 0 6px;">'
            f'<tr><td style="border-radius:8px;background:#F2A93B;">'
            f'<a href="{html_lib.escape(url)}" '
            f'style="display:inline-block;padding:12px 22px;font-size:14px;font-weight:600;'
            f'color:#0F1115;text-decoration:none;">{html_lib.escape(label)}</a>'
            f"</td></tr></table>"
        )

    html = f"""<!doctype html>
<html><body style="margin:0;padding:0;background:#f4f5f7;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f5f7;padding:32px 12px;">
<tr><td align="center">
<table role="presentation" width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;">
<tr><td style="padding:0 4px 16px;font-family:Arial,Helvetica,sans-serif;">
  <span style="font-size:17px;font-weight:700;color:#0F1115;">Problem<span style="color:#D98A18;">Forge</span></span>
</td></tr>
<tr><td style="background:#ffffff;border-radius:12px;padding:32px 28px;font-family:Arial,Helvetica,sans-serif;">
  <h1 style="margin:0 0 18px;font-size:20px;line-height:1.35;color:#0F1115;">{html_lib.escape(heading)}</h1>
  {paragraphs_html}
  {cta_html}
</td></tr>
<tr><td style="padding:18px 8px;font-family:Arial,Helvetica,sans-serif;font-size:12px;line-height:1.6;color:#8a93a6;">
  {html_lib.escape(footer_note)}<br>
  You received this because of activity on your ProblemForge account.
</td></tr>
</table>
</td></tr></table>
</body></html>"""

    text_parts = [heading, ""] + body_lines
    if cta:
        text_parts += ["", f"{cta[0]}: {cta[1]}"]
    text_parts += ["", "--", footer_note]
    return html, "\n".join(text_parts)


def is_configured() -> bool:
    return bool(settings.resend_api_key and settings.email_from)


async def send_email(
    to: str,
    subject: str,
    heading: str,
    body_lines: list[str],
    cta: tuple[str, str] | None = None,
) -> bool:
    """Send one transactional email. Returns False (never raises) on failure."""
    if not is_configured() or not to:
        return False
    html, text = render_email(heading, body_lines, cta)
    payload: dict = {
        "from": settings.email_from,
        "to": [to],
        "subject": subject,
        "html": html,
        "text": text,
    }
    if settings.email_reply_to:
        payload["reply_to"] = settings.email_reply_to
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                RESEND_URL,
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json=payload,
            )
        return response.status_code < 300
    except Exception:
        return False
