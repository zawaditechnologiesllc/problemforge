"""Tests for the Freedom-to-Operate report core (verification + PDF)."""

from datetime import date

from app.services.fto import (
    DISCLAIMER,
    assess_expiry,
    render_pdf,
    valid_patent_number,
)


def test_valid_patent_number_normalizes():
    assert valid_patent_number("US 7,156,808 B2") == "US7156808B2"
    assert valid_patent_number("us6934691b1") == "US6934691B1"
    assert valid_patent_number("EP1500000A1") == "EP1500000A1"


def test_valid_patent_number_rejects_garbage():
    assert valid_patent_number("") is None
    assert valid_patent_number("1234567") is None
    assert valid_patent_number("US12; DROP TABLE") is None


def test_assess_expiry_statutory_term():
    result = assess_expiry("2004-06-15", None, today=date(2026, 7, 17))
    assert result["public_domain"] is True
    assert any("Statutory term" in line for line in result["basis"])


def test_assess_expiry_source_status():
    result = assess_expiry(None, "Expired - lapsed for non-payment", today=date(2026, 7, 17))
    assert result["public_domain"] is True
    assert any("legal status" in line.lower() for line in result["basis"])


def test_assess_expiry_rejects_recent_and_unknown():
    recent = assess_expiry("2015-01-01", "Active", today=date(2026, 7, 17))
    assert recent["public_domain"] is False
    unknown = assess_expiry(None, None)
    assert unknown["public_domain"] is False
    assert unknown["basis"] == []


def test_assess_expiry_boundary():
    # Exactly 20 years: term ended today -> public domain
    on_boundary = assess_expiry("2006-07-17", None, today=date(2026, 7, 17))
    assert on_boundary["public_domain"] is True
    # One day short -> not public domain
    short = assess_expiry("2006-07-18", None, today=date(2026, 7, 17))
    assert short["public_domain"] is False


def test_render_pdf_produces_pdf_with_disclaimer():
    verification = assess_expiry("2004-06-15", "Expired - statutory term", today=date(2026, 7, 17))
    verification.update(
        {
            "patent_number": "US7156808B2",
            "title": "Remote monitoring of therapy compliance",
            "evidence": ["ProblemForge database record (source: seed)."],
        }
    )
    pdf = render_pdf(verification, "Plain-language analysis text.")
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000
    # The non-negotiable disclaimer must always be present in the source data
    assert "NOT legal advice" in DISCLAIMER
