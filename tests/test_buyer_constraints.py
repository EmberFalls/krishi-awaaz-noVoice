import asyncio
from decimal import Decimal
from pathlib import Path

from agents.negotiation import assess_markets, eligible_middleman, negotiate_with_middleman
from data.scenarios import load_scenarios
from orchestration.workflow import intake_node

CATALOG = Path(__file__).parents[1] / "data" / "scenarios.json"


def test_unavailable_capacity_and_quality_rules_exclude_buyers() -> None:
    scenario = load_scenarios(CATALOG)[0]
    request = intake_node({"scenario": scenario})["farmer_request"]
    buyer = scenario.middlemen[0]

    assert eligible_middleman(request, buyer)
    assert not eligible_middleman(request, buyer.model_copy(update={"is_available": False}))
    assert not eligible_middleman(
        request,
        buyer.model_copy(update={"available_quantity_quintal": Decimal(20)}),
    )
    assert not eligible_middleman(
        request,
        buyer.model_copy(update={"accepted_quality_keywords": ["premium export"]}),
    )


def test_competing_demand_changes_a_provisional_quote() -> None:
    scenario = load_scenarios(CATALOG)[0]
    request = intake_node({"scenario": scenario})["farmer_request"]
    buyer = scenario.middlemen[0]
    markets = assess_markets(request, scenario.markets)
    baseline = asyncio.run(negotiate_with_middleman(request, buyer, markets))
    competitive = asyncio.run(
        negotiate_with_middleman(
            request,
            buyer.model_copy(update={"competing_demand_modifier_per_quintal": Decimal(50)}),
            markets,
        )
    )
    assert competitive.final_price_per_quintal >= baseline.final_price_per_quintal
