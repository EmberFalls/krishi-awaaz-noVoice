import asyncio
from pathlib import Path

from agents.models import OfferStatus
from data.scenarios import load_scenarios
from orchestration.workflow import execute_scenario

CATALOG = Path(__file__).parents[1] / "data" / "scenarios.json"


def test_all_scenarios_complete_with_bounded_offers() -> None:
    scenarios = load_scenarios(CATALOG)

    for scenario in scenarios:
        result = asyncio.run(execute_scenario(scenario))
        middlemen = {middleman.id: middleman for middleman in scenario.middlemen}

        assert len(result.market_assessments) == len(scenario.markets)
        assert len(result.offers) == len(scenario.middlemen)
        assert result.events[-1].node == "reporting_agent"
        assert (
            "provisional" in result.report_text.lower() or result.recommended_middleman_id is None
        )

        for offer in result.offers:
            profile = middlemen[offer.middleman_id]
            assert offer.initial_price_per_quintal <= offer.final_price_per_quintal
            assert offer.final_price_per_quintal <= profile.maximum_offer_per_quintal
            assert offer.conversation
            assert all("{" not in line.text for line in offer.conversation)
            assert all("{" not in line.english_translation for line in offer.conversation)
            if offer.status is OfferStatus.QUALIFIED:
                assert offer.final_price_per_quintal >= scenario.listing.minimum_price_per_quintal


def test_offer_ranks_are_contiguous_for_qualified_offers() -> None:
    scenario = load_scenarios(CATALOG)[0]
    result = asyncio.run(execute_scenario(scenario))
    qualified = [offer for offer in result.offers if offer.status is OfferStatus.QUALIFIED]

    assert [offer.rank for offer in qualified] == list(range(1, len(qualified) + 1))
    assert [offer.risk_adjusted_total for offer in qualified] == sorted(
        [offer.risk_adjusted_total for offer in qualified], reverse=True
    )
    assert "maximum_hidden_price_per_quintal" not in result.model_dump(mode="json")
    assert "maximum_hidden_price_per_quintal" not in result.model_dump_json()
