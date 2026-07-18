"""Tests for the 5-Point Validation Framework parsing and orchestration."""

import asyncio
import json

from app.config import settings
from app.services import framework

VALID_OUTPUT = json.dumps(
    {
        "market_size": {
            "score": 72,
            "assessment": "Plenty of discussion volume.",
            "best_demographic": "Solo physical therapists in the US",
        },
        "competition": {
            "score": 55,
            "assessment": "Crowded but generic.",
            "gaps": ["PT-specific templates", "Audit-ready exports"],
        },
        "feasibility": {
            "score": 85,
            "assessment": "Whisper + LLM stack is well-trodden.",
            "mvp_scope": "Record, transcribe, structure one SOAP note.",
        },
        "monetization": {
            "score": 78,
            "assessment": "Clinics already pay for documentation tools.",
            "recommended_model": "Per-seat subscription at $49/therapist/month",
        },
        "uniqueness": {
            "score": 60,
            "assessment": "UX focus is the wedge.",
            "angle": "Under-90-seconds-per-note workflow",
        },
        "overall_score": 70,
        "verdict": "Build it. Start with the PT niche.",
    }
)


def test_parse_valid_json():
    parsed = framework.parse_framework_json(VALID_OUTPUT)
    assert parsed is not None
    assert parsed["market_size"]["score"] == 72
    assert parsed["competition"]["gaps"] == [
        "PT-specific templates",
        "Audit-ready exports",
    ]
    assert parsed["overall_score"] == 70


def test_parse_tolerates_code_fences_and_chatter():
    wrapped = f"Here is the analysis:\n```json\n{VALID_OUTPUT}\n```\nHope this helps!"
    parsed = framework.parse_framework_json(wrapped)
    assert parsed is not None
    assert parsed["verdict"].startswith("Build it")


def test_parse_clamps_and_derives_scores():
    data = json.loads(VALID_OUTPUT)
    data["market_size"]["score"] = 250
    data["uniqueness"]["score"] = "not-a-number"
    del data["overall_score"]
    parsed = framework.parse_framework_json(json.dumps(data))
    assert parsed is not None
    assert parsed["market_size"]["score"] == 100
    assert parsed["uniqueness"]["score"] == 50
    assert 0 <= parsed["overall_score"] <= 100


def test_parse_rejects_missing_pillars():
    assert framework.parse_framework_json('{"market_size": {"score": 1}}') is None
    assert framework.parse_framework_json("total garbage") is None


def test_analyze_without_llm_key_returns_none(monkeypatch):
    monkeypatch.setattr(settings, "llm_api_key", "")
    result = asyncio.run(framework.analyze_idea("an idea goes here", [], []))
    assert result is None


def test_analyze_calls_llm_and_caches(monkeypatch):
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    calls = {"n": 0}

    async def fake_chat(model, system, user, max_tokens=0, temperature=0.0):
        calls["n"] += 1
        assert "5-Point Validation Framework" in user
        assert "no-show killer" in user  # idea is embedded in the prompt
        assert "Automated Appointment Reminder" in user  # matches as evidence
        assert "(reddit)" in user  # community questions as evidence
        return VALID_OUTPUT

    monkeypatch.setattr(framework.llm, "chat", fake_chat)
    matches = [
        {
            "title": "Automated Appointment Reminder & Confirmation Calls",
            "similarity": 0.83,
            "human_problem": "No-shows bleed revenue.",
        }
    ]
    questions = [{"source": "reddit", "title": "No-shows are killing me", "engagement": 40}]

    idea = "a no-show killer app for salons run 42"
    first = asyncio.run(framework.analyze_idea(idea, matches, questions))
    assert first is not None and first["overall_score"] == 70
    second = asyncio.run(framework.analyze_idea(idea, matches, questions))
    assert second == first
    assert calls["n"] == 1  # second run served from cache
