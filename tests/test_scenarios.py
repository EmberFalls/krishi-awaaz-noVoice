from pathlib import Path

from data.scenarios import load_scenarios

CATALOG = Path(__file__).parents[1] / "data" / "scenarios.json"


def test_catalog_has_multiple_farmers_languages_and_middlemen() -> None:
    scenarios = load_scenarios(CATALOG)

    assert len(scenarios) == 4
    assert len({scenario.farmer.id for scenario in scenarios}) == 4
    assert {scenario.farmer.preferred_language for scenario in scenarios} == {
        "mr-IN",
        "pa-IN",
        "ta-IN",
        "te-IN",
    }
    assert all(len(scenario.middlemen) == 3 for scenario in scenarios)
    assert all(len(scenario.intake_dialogue) >= 6 for scenario in scenarios)


def test_every_dialogue_line_is_reviewable_in_english() -> None:
    scenarios = load_scenarios(CATALOG)

    for scenario in scenarios:
        for line in scenario.intake_dialogue:
            assert line.text.strip()
            assert line.english_translation.strip()
