"""Tests for the Modern AI Playbook parsing."""

import json

from app.services.playbook import STAGES, parse_playbook_json

VALID = json.dumps(
    {
        "problem_today": {
            "still_exists": True,
            "assessment": "No-shows still cost clinics real revenue.",
            "evidence": "r/smallbusiness thread with 482 upvotes this month.",
        },
        "ai_solution": "Use LLM-voiced calls with natural conversation instead of robotic prompts.",
        "stack": {
            "design": "Figma or Google Stitch for six core screens.",
            "coding": "Next.js 14 + TypeScript built in Cursor.",
            "configuration": "Vercel frontend, Render FastAPI, Supabase Postgres + Auth.",
            "integration": "Twilio Voice + OpenAI TTS + Stripe subscriptions.",
            "testing": "Playwright on the booking flow, pytest on webhooks, 10-clinic beta.",
        },
        "marketing": {
            "channels": [
                {
                    "channel": "Reddit communities",
                    "audience": "Salon and clinic owners in r/smallbusiness",
                    "how": "Answer no-show threads with a case study, not a pitch.",
                },
                {
                    "channel": "SEO",
                    "audience": "Owners searching 'reduce appointment no-shows'",
                    "how": "Comparison and calculator pages targeting long-tail queries.",
                },
            ]
        },
    }
)


def test_parse_valid_playbook():
    parsed = parse_playbook_json(VALID)
    assert parsed is not None
    assert parsed["problem_today"]["still_exists"] is True
    assert set(parsed["stack"]) == set(STAGES)
    assert len(parsed["marketing"]["channels"]) == 2
    assert parsed["marketing"]["channels"][0]["channel"] == "Reddit communities"


def test_parse_tolerates_code_fences():
    wrapped = f"```json\n{VALID}\n```"
    assert parse_playbook_json(wrapped) is not None


def test_parse_rejects_missing_stage():
    data = json.loads(VALID)
    del data["stack"]["testing"]
    assert parse_playbook_json(json.dumps(data)) is None


def test_parse_rejects_empty_channels_and_garbage():
    data = json.loads(VALID)
    data["marketing"]["channels"] = []
    assert parse_playbook_json(json.dumps(data)) is None
    assert parse_playbook_json("not json at all") is None


def test_parse_caps_channels_at_five():
    data = json.loads(VALID)
    data["marketing"]["channels"] = data["marketing"]["channels"] * 4  # 8
    parsed = parse_playbook_json(json.dumps(data))
    assert parsed is not None
    assert len(parsed["marketing"]["channels"]) == 5
