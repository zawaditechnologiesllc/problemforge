"""Freedom-to-Operate reports ($99 one-time).

Flow: checkout (Stripe, mode=payment) -> webhook marks the report queued and
schedules generation -> re-verify the patent's expired status (stored data +
live USPTO lookup) -> optional LLM plain-language analysis -> render PDF ->
upload to a private Supabase Storage bucket -> user downloads via signed URL.

Every report states prominently that it is an AI-generated informational
summary, NOT legal advice — that wording is non-negotiable (see brief §8).
"""

import re
from datetime import date, datetime, timezone

from fpdf import FPDF

from ..config import settings
from ..db import get_db
from . import llm
from .patent_sources import USPTOSource
from .patent_sources.base import normalize_patent_number

DISCLAIMER = (
    "This report is an AI-generated informational summary produced by "
    "ProblemForge. It is NOT legal advice, NOT a legal opinion, and NOT a "
    "guarantee of freedom to operate. Patent status data can be contested, "
    "corrected, or reinstated. Consult a qualified patent attorney before "
    "making commercial decisions."
)

PATENT_NUMBER_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{4,15}$")


def valid_patent_number(raw: str) -> str | None:
    normalized = normalize_patent_number(raw)
    return normalized if PATENT_NUMBER_RE.match(normalized) else None


def assess_expiry(
    filing_date: str | None, legal_status: str | None, today: date | None = None
) -> dict:
    """Deterministic expiry assessment — the verifiable core of the report."""
    today = today or date.today()
    basis: list[str] = []
    filed: date | None = None
    if filing_date:
        try:
            filed = date.fromisoformat(str(filing_date))
        except ValueError:
            filed = None
    if filed:
        try:
            term_end = filed.replace(year=filed.year + 20)
        except ValueError:  # Feb 29
            term_end = filed.replace(year=filed.year + 20, day=28)
        if term_end <= today:
            basis.append(
                f"Statutory term: filed {filed.isoformat()}, so the 20-year term "
                f"ended on or about {term_end.isoformat()}."
            )
    status = (legal_status or "").lower()
    if "expired" in status or "lapsed" in status or "ceased" in status:
        basis.append(f"Recorded legal status: \"{legal_status}\".")
    return {
        "public_domain": bool(basis),
        "basis": basis,
        "filing_date": filed.isoformat() if filed else None,
        "legal_status": legal_status,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


async def verify_patent(patent_number: str) -> dict:
    """Re-verify status from stored data plus a live USPTO lookup."""
    db = get_db()
    evidence: list[str] = []
    stored = (
        db.table("raw_patents")
        .select("title, filing_date, legal_status, source, public_domain_verified_at")
        .eq("patent_number", patent_number)
        .limit(1)
        .execute()
        .data
    )
    stored_row = stored[0] if stored else None
    if stored_row:
        evidence.append(
            f"ProblemForge database record (source: {stored_row['source']}, "
            f"verified {stored_row.get('public_domain_verified_at') or 'n/a'})."
        )

    live = None
    try:
        live = await USPTOSource().fetch_by_number(patent_number)
        if live:
            evidence.append("Live USPTO (PatentsView) lookup at report time.")
    except Exception:
        evidence.append("Live USPTO lookup unavailable at report time.")

    title = (live or {}).get("title") or (stored_row or {}).get("title")
    filing_date = (live or {}).get("filing_date") or (stored_row or {}).get("filing_date")
    legal_status = (stored_row or {}).get("legal_status")

    assessment = assess_expiry(filing_date, legal_status)
    assessment.update(
        {
            "patent_number": patent_number,
            "title": title,
            "evidence": evidence,
            "found": bool(stored_row or live),
        }
    )
    return assessment


async def _plain_language_analysis(verification: dict) -> str:
    """Optional LLM section; deterministic fallback when no LLM is configured."""
    fallback = (
        "Automated analysis was generated without an LLM provider configured. "
        "The verification facts above are computed deterministically from "
        "filing dates and recorded legal status."
    )
    if not settings.llm_api_key:
        return fallback
    try:
        return await llm.chat(
            settings.coder_model,
            "You are a careful analyst. Summarize patent expiry findings in plain "
            "language for a non-lawyer founder. Never present anything as legal "
            "advice or a guarantee. 150 words maximum.",
            f"Findings: {verification}",
            max_tokens=400,
        )
    except Exception:
        return fallback


def _latin1(text: str) -> str:
    return (text or "").encode("latin-1", "replace").decode("latin-1")


def render_pdf(verification: dict, analysis: str) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 12, "Freedom-to-Operate Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(
        0,
        7,
        _latin1(
            f"Patent {verification['patent_number']} - generated "
            f"{verification['checked_at'][:10]} by ProblemForge"
        ),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(4)
    pdf.set_text_color(0, 0, 0)

    verdict = (
        "VERIFIED PUBLIC DOMAIN" if verification["public_domain"] else "NOT VERIFIED"
    )
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_fill_color(*(223, 240, 216) if verification["public_domain"] else (252, 228, 214))
    pdf.cell(0, 10, f"  Status: {verdict}", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.ln(4)

    sections: list[tuple[str, str]] = [
        (
            "Patent",
            f"{verification['patent_number']}"
            + (f" - {verification['title']}" if verification.get("title") else ""),
        ),
        (
            "Verification basis",
            "\n".join(f"- {line}" for line in verification["basis"])
            or "No independent basis for expiry could be established. Do not "
            "assume this patent is safe to build on.",
        ),
        (
            "Evidence consulted",
            "\n".join(f"- {line}" for line in verification.get("evidence", []))
            or "- None available.",
        ),
        ("Plain-language analysis (AI-generated)", analysis),
        ("Important notice", DISCLAIMER),
    ]
    for heading, body in sections:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 9, _latin1(heading), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10.5)
        pdf.multi_cell(0, 5.5, _latin1(body))
        pdf.ln(3)

    return bytes(pdf.output())


def _storage(db):
    return db.storage.from_(settings.fto_bucket)


def _ensure_bucket(db) -> None:
    try:
        db.storage.create_bucket(settings.fto_bucket, options={"public": False})
    except Exception:
        pass  # already exists (or will fail loudly at upload)


async def generate_report(report_id: str) -> None:
    """Async job: verify -> analyze -> render -> upload -> mark ready."""
    db = get_db()
    rows = (
        db.table("fto_reports").select("*").eq("id", report_id).limit(1).execute().data
    )
    if not rows:
        return
    report = rows[0]
    if report["status"] not in ("queued", "pending_payment", "failed"):
        return  # already processing/ready — webhook retries are no-ops

    db.table("fto_reports").update({"status": "processing"}).eq("id", report_id).execute()
    try:
        verification = await verify_patent(report["patent_number"])
        analysis = await _plain_language_analysis(verification)
        pdf_bytes = render_pdf(verification, analysis)

        path = f"{report['user_id']}/{report_id}.pdf"
        _ensure_bucket(db)
        _storage(db).upload(
            path,
            pdf_bytes,
            {"content-type": "application/pdf", "upsert": "true"},
        )
        db.table("fto_reports").update(
            {
                "status": "ready",
                "verification": verification,
                "report_path": path,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "error": None,
            }
        ).eq("id", report_id).execute()
    except Exception as exc:
        db.table("fto_reports").update(
            {"status": "failed", "error": str(exc)[:1000]}
        ).eq("id", report_id).execute()


def signed_download_url(report: dict, expires_seconds: int = 3600) -> str:
    db = get_db()
    result = _storage(db).create_signed_url(report["report_path"], expires_seconds)
    url = result.get("signedURL") or result.get("signedUrl") or result.get("signed_url")
    if not url:
        raise RuntimeError("could not create signed URL")
    if url.startswith("/"):
        url = f"{settings.supabase_url}/storage/v1{url}"
    return url
