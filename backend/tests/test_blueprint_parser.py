"""Tests for parsing the four-section LLM translation output."""

from app.services.llm import parse_blueprint_markdown

FULL_OUTPUT = """### THE HUMAN PROBLEM
People forget errands until they get home.

### THE EXPIRED CORE LOGIC
Reminders are bound to geographic regions; boundary entry fires the matching task.

### HOW A VIBE CODER BUILDS IT TODAY
1. Build an Expo app with a task list.
2. Register OS geofences and fire local notifications.
3. Sync through Supabase and add a premium tier.

### PROMPT FOR CURSOR / WINDSURF
Build "Nearby", a location-triggered reminder app, with Expo and Supabase.
"""


def test_parses_all_four_sections():
    parsed = parse_blueprint_markdown(FULL_OUTPUT)
    assert parsed is not None
    assert set(parsed) == {
        "human_problem",
        "expired_logic",
        "build_plan",
        "master_prompt",
    }
    assert parsed["human_problem"] == "People forget errands until they get home."
    assert parsed["build_plan"].startswith("1. Build an Expo app")
    assert "Nearby" in parsed["master_prompt"]


def test_tolerates_heading_level_and_case_variations():
    variant = FULL_OUTPUT.replace("### THE HUMAN PROBLEM", "## The Human Problem")
    parsed = parse_blueprint_markdown(variant)
    assert parsed is not None
    assert parsed["human_problem"] == "People forget errands until they get home."


def test_rejects_incomplete_output():
    assert parse_blueprint_markdown("### THE HUMAN PROBLEM\nOnly one section.") is None
    assert parse_blueprint_markdown("no headings at all") is None


def test_rejects_empty_sections():
    empty = FULL_OUTPUT.replace(
        "People forget errands until they get home.", ""
    )
    assert parse_blueprint_markdown(empty) is None
