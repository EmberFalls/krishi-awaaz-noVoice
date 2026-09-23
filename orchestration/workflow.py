from __future__ import annotations

import asyncio
from typing import TypedDict, cast
from uuid import uuid4

from agents.models import (
    FarmerRequest,
    MarketAssessment,
    MiddlemanProfile,
    NegotiatedOffer,
    OfferStatus,
    SimulationResult,
    SimulationScenario,
    WorkflowEvent,
)
from agents.negotiation import (
    assess_markets,
    eligible_middleman,
    negotiate_with_middleman,
    rank_offers,
)


class SimulationState(TypedDict, total=False):
    scenario: SimulationScenario
    farmer_request: FarmerRequest
    market_assessments: list[MarketAssessment]
    eligible_middlemen: list[MiddlemanProfile]
    offers: list[NegotiatedOffer]
    recommended_middleman_id: str | None
    report_text: str
    events: list[WorkflowEvent]


def intake_node(state: SimulationState) -> dict[str, object]:
    scenario = state["scenario"]
    farmer = scenario.farmer
    listing = scenario.listing
    request = FarmerRequest(
        farmer_id=farmer.id,
        farmer_name=farmer.name,
        location=farmer.location,
        preferred_language=farmer.preferred_language,
        listing_id=listing.id,
        crop=listing.crop,
        crop_local_name=listing.crop_local_name,
        variety=listing.variety,
        quantity_quintal=listing.quantity_quintal,
        quality_grade=listing.quality_grade,
        minimum_price_per_quintal=listing.minimum_price_per_quintal,
        urgency_hours=listing.urgency_hours,
        pickup_preferred=listing.pickup_preferred,
        notes=listing.notes,
    )
    event = WorkflowEvent(
        node="intake_agent",
        message="Validated the scripted farmer conversation into a typed FarmerRequest.",
        data={
            "farmer_id": farmer.id,
            "language": farmer.preferred_language,
            "crop": listing.crop,
            "quantity_quintal": str(listing.quantity_quintal),
        },
    )
    return {"farmer_request": request, "events": [event]}


def market_decision_node(state: SimulationState) -> dict[str, object]:
    assessments = assess_markets(state["farmer_request"], state["scenario"].markets)
    event = WorkflowEvent(
        node="decision_agent",
        message="Ranked synthetic markets by estimated net return after transport and fees.",
        data={"market_order": [item.market.id for item in assessments]},
    )
    return {"market_assessments": assessments, "events": [event]}


def buyer_selection_node(state: SimulationState) -> dict[str, object]:
    request = state["farmer_request"]
    eligible = [
        middleman
        for middleman in state["scenario"].middlemen
        if eligible_middleman(request, middleman)
    ]
    event = WorkflowEvent(
        node="buyer_selection",
        message="Selected available middlemen whose crop, capacity, and quality constraints match.",
        data={
            "eligible_middlemen": [middleman.id for middleman in eligible],
            "excluded_middlemen": [
                middleman.id
                for middleman in state["scenario"].middlemen
                if middleman not in eligible
            ],
        },
    )
    return {"eligible_middlemen": eligible, "events": [event]}


async def parallel_negotiation_node(state: SimulationState) -> dict[str, object]:
    offers = await asyncio.gather(
        *[
            negotiate_with_middleman(
                state["farmer_request"], middleman, state["market_assessments"]
            )
            for middleman in state["eligible_middlemen"]
        ]
    )
    event = WorkflowEvent(
        node="negotiation_agents",
        message="Ran independent deterministic negotiations concurrently.",
        data={
            "offers": {offer.middleman_id: str(offer.final_price_per_quintal) for offer in offers}
        },
    )
    return {"offers": list(offers), "events": [event]}


def ranking_node(state: SimulationState) -> dict[str, object]:
    offers = rank_offers(state["offers"])
    recommended = next(
        (offer.middleman_id for offer in offers if offer.status is OfferStatus.QUALIFIED),
        None,
    )
    event = WorkflowEvent(
        node="offer_ranker",
        message="Ranked qualified offers by risk-adjusted net return.",
        data={"recommended_middleman_id": recommended},
    )
    return {
        "offers": offers,
        "recommended_middleman_id": recommended,
        "events": [event],
    }


def reporting_node(state: SimulationState) -> dict[str, object]:
    request = state["farmer_request"]
    recommended_id = state.get("recommended_middleman_id")
    if recommended_id is None:
        report = (
            f"No provisional offer met {request.farmer_name}'s minimum price of "
            f"₹{request.minimum_price_per_quintal} per quintal. No deal should be accepted."
        )
    else:
        offer = next(item for item in state["offers"] if item.middleman_id == recommended_id)
        pickup = "buyer pickup" if offer.pickup_available else "farmer-arranged transport"
        report = (
            f"Recommended provisional quote: {offer.business_name} at "
            f"₹{offer.final_price_per_quintal} per quintal, {pickup}, payment in "
            f"{offer.payment_delay_days} day(s). Estimated net total: "
            f"₹{offer.estimated_net_total}. Farmer confirmation and physical quality/weight "
            "inspection are still required."
        )
    event = WorkflowEvent(
        node="reporting_agent",
        message="Prepared a non-binding recommendation for farmer review.",
        data={"has_recommendation": recommended_id is not None},
    )
    return {"report_text": report, "events": [event]}


def apply_node_update(state: SimulationState, update: dict[str, object]) -> None:
    """Merge one node's output into shared state while retaining the event history."""

    existing_events = state.get("events", [])
    new_events = cast(list[WorkflowEvent], update.get("events", []))
    state.update(cast(SimulationState, update))
    state["events"] = [*existing_events, *new_events]


async def execute_scenario(scenario: SimulationScenario) -> SimulationResult:
    final_state: SimulationState = {"scenario": scenario, "events": []}

    apply_node_update(final_state, intake_node(final_state))
    apply_node_update(final_state, market_decision_node(final_state))
    apply_node_update(final_state, buyer_selection_node(final_state))
    apply_node_update(final_state, await parallel_negotiation_node(final_state))
    apply_node_update(final_state, ranking_node(final_state))
    apply_node_update(final_state, reporting_node(final_state))

    return SimulationResult(
        run_id=str(uuid4()),
        scenario_id=scenario.id,
        scenario_title=scenario.title,
        farmer_request=final_state["farmer_request"],
        intake_dialogue=scenario.intake_dialogue,
        market_assessments=final_state["market_assessments"],
        offers=final_state["offers"],
        recommended_middleman_id=final_state.get("recommended_middleman_id"),
        report_text=final_state["report_text"],
        events=final_state["events"],
    )
