"""Tests for the transactional email renderer and safety behavior."""

import asyncio

from app.config import settings
from app.services import email


def test_render_produces_html_and_text_parts():
    html, text = email.render_email(
        "Your FTO report is ready",
        ["The report for patent US7156808B2 has been generated.", "Download it from your dashboard."],
        cta=("Download your report", "https://example.com/account"),
    )
    # Branded HTML with the CTA
    assert "ProblemForge".replace("Forge", "") in html  # wordmark split across spans
    assert "Your FTO report is ready" in html
    assert "https://example.com/account" in html
    assert "US7156808B2" in html
    # Plain-text alternative carries the same content (deliverability)
    assert "Your FTO report is ready" in text
    assert "Download your report: https://example.com/account" in text
    assert "Zawadi Technologies" in text


def test_render_escapes_html_in_content():
    html, _ = email.render_email(
        "Heading <script>alert(1)</script>",
        ['Body with <img src=x onerror=alert(1)> & "quotes"'],
    )
    # Injected tags must not survive as live markup — only as escaped text.
    assert "<script>" not in html
    assert "<img" not in html
    assert "&lt;script&gt;" in html
    assert "&lt;img src=x onerror=alert(1)&gt;" in html


def test_send_email_is_noop_without_configuration(monkeypatch):
    monkeypatch.setattr(settings, "resend_api_key", "")
    monkeypatch.setattr(settings, "email_from", "")
    assert asyncio.run(
        email.send_email("user@example.com", "Subject", "Heading", ["Body"])
    ) is False
    assert email.is_configured() is False


def test_send_email_requires_recipient(monkeypatch):
    monkeypatch.setattr(settings, "resend_api_key", "re_test")
    monkeypatch.setattr(settings, "email_from", "ProblemForge <n@example.com>")
    assert asyncio.run(email.send_email("", "Subject", "Heading", ["Body"])) is False
