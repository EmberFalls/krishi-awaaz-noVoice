from __future__ import annotations

import asyncio
from decimal import ROUND_HALF_UP, Decimal

from .localization import negotiation_language
from .models import (
    DialogueLine,
    FarmerRequest,
    MarketAssessment,
    MarketSnapshot,
    MiddlemanProfile,
    NegotiatedOffer,
    OfferStatus,
    SpeakerType,
)

TEN = Decimal(10)
PAISE = Decimal("0.01")

PAYMENT_NOW = {
    "hi-IN": "भुगतान उसी दिन कर दूँगा।",
    "mr-IN": "पैसे त्याच दिवशी देईन.",
    "pa-IN": "ਭੁਗਤਾਨ ਉਸੇ ਦਿਨ ਕਰ ਦਿੱਤਾ ਜਾਵੇਗਾ।",
    "ta-IN": "பணம் அதே நாளில் கொடுக்கப்படும்.",
    "te-IN": "చెల్లింపు అదే రోజు చేస్తాను.",
}
PAYMENT_ONE_DAY = {
    "hi-IN": "भुगतान एक दिन के भीतर कर दूँगा।",
    "mr-IN": "पैसे एका दिवसात देईन.",
    "pa-IN": "ਭੁਗਤਾਨ ਇੱਕ ਦਿਨ ਵਿੱਚ ਕਰ ਦਿੱਤਾ ਜਾਵੇਗਾ।",
    "ta-IN": "பணம் ஒரு நாளுக்குள் கொடுக்கப்படும்.",
    "te-IN": "చెల్లింపు ఒక రోజులో చేస్తాను.",
}
PAYMENT_LATER = {
    "hi-IN": "भुगतान {days} दिन के भीतर कर दूँगा।",
    "mr-IN": "पैसे {days} दिवसांत देईन.",
    "pa-IN": "ਭੁਗਤਾਨ {days} ਦਿਨਾਂ ਵਿੱਚ ਕਰ ਦਿੱਤਾ ਜਾਵੇਗਾ।",
    "ta-IN": "பணம் {days} நாட்களுக்குள் கொடுக்கப்படும்.",
    "te-IN": "చెల్లింపు {days} రోజుల్లో చేస్తాను.",
}
BUYER_PICKUP = {
    "hi-IN": "गाड़ी मैं भेजूँगा।",
    "mr-IN": "माल उचलण्यासाठी गाडी मी पाठवीन.",
    "pa-IN": "ਮਾਲ ਚੁੱਕਣ ਲਈ ਗੱਡੀ ਮੈਂ ਭੇਜਾਂਗਾ।",
    "ta-IN": "சரக்கை எடுக்க வண்டியை நான் அனுப்புவேன்.",
    "te-IN": "సరుకు తీసుకెళ్లడానికి వాహనం నేను పంపిస్తాను.",
}
FARMER_DELIVERS = {
    "hi-IN": "माल किसान को मेरे गोदाम तक पहुँचाना होगा।",
    "mr-IN": "माल शेतकऱ्याने माझ्या गोदामापर्यंत आणावा लागेल.",
    "pa-IN": "ਮਾਲ ਕਿਸਾਨ ਨੂੰ ਮੇਰੇ ਗੋਦਾਮ ਤੱਕ ਪਹੁੰਚਾਉਣਾ ਪਵੇਗਾ।",
    "ta-IN": "சரக்கை விவசாயி என் கிடங்கிற்கு கொண்டு வர வேண்டும்.",
    "te-IN": "సరుకును రైతే నా గోదాముకు తీసుకురావాలి.",
}


def rounded_price(value: Decimal) -> Decimal:
    return (value / TEN).quantize(Decimal(1), rounding=ROUND_HALF_UP) * TEN


def display_number(value: Decimal) -> str:
    normalized = value.quantize(PAISE)
    if normalized == normalized.to_integral():
        return f"{int(normalized):,}"
    return f"{normalized:,.2f}"


def payment_clause(language: str, delay_days: int) -> tuple[str, str]:
    if delay_days == 0:
        return (
            PAYMENT_NOW.get(language, PAYMENT_NOW["hi-IN"]),
            "Payment will be made the same day.",
        )
    if delay_days == 1:
        return (
            PAYMENT_ONE_DAY.get(language, PAYMENT_ONE_DAY["hi-IN"]),
            "Payment will be made within 1 day.",
        )
    local = PAYMENT_LATER.get(language, PAYMENT_LATER["hi-IN"]).format(days=delay_days)
    return local, f"Payment will be made within {delay_days} days."


def pickup_clause(language: str, pickup_available: bool) -> tuple[str, str]:
    if pickup_available:
        return (
            BUYER_PICKUP.get(language, BUYER_PICKUP["hi-IN"]),
            "I will send a vehicle for pickup.",
        )
    return (
        FARMER_DELIVERS.get(language, FARMER_DELIVERS["hi-IN"]),
        "The farmer must deliver the produce to my warehouse.",
    )


def assess_markets(request: FarmerRequest, markets: list[MarketSnapshot]) -> list[MarketAssessment]:
    assessments: list[MarketAssessment] = []
    for market in markets:
        gross = market.modal_price_per_quintal * request.quantity_quintal
        net = gross - market.transport_cost_total - market.fees_total
        assessments.append(
            MarketAssessment(
                market=market,
                estimated_gross_total=gross.quantize(PAISE),
                estimated_net_total=net.quantize(PAISE),
                estimated_net_per_quintal=(net / request.quantity_quintal).quantize(PAISE),
            )
        )

    assessments.sort(key=lambda item: item.estimated_net_total, reverse=True)
    return [
        assessment.model_copy(update={"rank": rank})
        for rank, assessment in enumerate(assessments, 1)
    ]


def eligible_middleman(request: FarmerRequest, middleman: MiddlemanProfile) -> bool:
    quality_matches = not middleman.accepted_quality_keywords or any(
        term.casefold() in request.quality_grade.casefold()
        for term in middleman.accepted_quality_keywords
    )
    capacity = middleman.available_quantity_quintal or middleman.maximum_quantity_quintal
    return (
        middleman.is_available
        and request.crop in middleman.supported_crops
        and middleman.minimum_quantity_quintal
        <= request.quantity_quintal
        <= min(middleman.maximum_quantity_quintal, capacity)
        and quality_matches
    )


def _line(
    speaker: SpeakerType,
    speaker_id: str,
    language: str,
    rendered: tuple[str, str],
    **metadata: object,
) -> DialogueLine:
    return DialogueLine(
        speaker=speaker,
        speaker_id=speaker_id,
        language=language,
        text=rendered[0],
        english_translation=rendered[1],
        metadata=dict(metadata),
    )


async def negotiate_with_middleman(
    request: FarmerRequest,
    middleman: MiddlemanProfile,
    market_assessments: list[MarketAssessment],
    max_rounds: int = 3,
) -> NegotiatedOffer:
    """Run a deterministic, reproducible provisional negotiation.

    The middleman's maximum price is simulator-only hidden state. The negotiation
    agent sees market-derived targets and the farmer's floor, never that maximum.
    """

    await asyncio.sleep(0)
    language = negotiation_language(middleman.preferred_language)
    market_by_id = {item.market.id: item for item in market_assessments}
    associated_market = market_by_id[middleman.market_id]
    market_target = rounded_price(associated_market.estimated_net_per_quintal)
    target_price = max(request.minimum_price_per_quintal, market_target)
    agent_ask = target_price
    competing_modifier = middleman.competing_demand_modifier_per_quintal
    buyer_offer = middleman.initial_offer_per_quintal + competing_modifier
    buyer_ceiling = middleman.maximum_offer_per_quintal + competing_modifier
    conversation: list[DialogueLine] = []

    values = {
        "name": middleman.name,
        "location": request.location.label,
        "quantity": display_number(request.quantity_quintal),
        "crop": request.crop_local_name,
        "crop_en": request.crop.replace("_", " "),
        "grade": request.quality_grade,
    }
    payment_local, payment_english = payment_clause(
        middleman.preferred_language, middleman.payment_delay_days
    )
    pickup_local, pickup_english = pickup_clause(
        middleman.preferred_language, middleman.pickup_available
    )
    values.update(
        {
            "payment_clause": payment_local,
            "payment_clause_en": payment_english,
            "pickup_clause": pickup_local,
            "pickup_clause_en": pickup_english,
        }
    )
    conversation.append(
        _line(
            SpeakerType.NEGOTIATION_AGENT,
            "negotiation-agent",
            middleman.preferred_language,
            language.quote_request.render(**values),
            action="request_quote",
        )
    )
    conversation.append(
        _line(
            SpeakerType.MIDDLEMAN,
            middleman.id,
            middleman.preferred_language,
            language.opening_offer.render(
                **values,
                price=display_number(buyer_offer),
            ),
            action="opening_offer",
            price=str(buyer_offer),
            pickup_available=middleman.pickup_available,
        )
    )

    ask_reduction = max(
        TEN, rounded_price(max(Decimal(0), target_price - request.minimum_price_per_quintal) / 3)
    )
    rounds = 0
    accepted_counter = False
    for rounds in range(1, max_rounds + 1):
        conversation.append(
            _line(
                SpeakerType.NEGOTIATION_AGENT,
                "negotiation-agent",
                middleman.preferred_language,
                language.agent_counter.render(price=display_number(agent_ask)),
                action="counter_offer",
                price=str(agent_ask),
                round=rounds,
            )
        )

        if agent_ask <= buyer_ceiling:
            buyer_offer = max(buyer_offer, agent_ask)
            accepted_counter = True
            conversation.append(
                _line(
                    SpeakerType.MIDDLEMAN,
                    middleman.id,
                    middleman.preferred_language,
                    language.buyer_accept.render(price=display_number(buyer_offer)),
                    action="accept_counter",
                    price=str(buyer_offer),
                    round=rounds,
                )
            )
            break

        next_offer = min(
            buyer_ceiling,
            buyer_offer + middleman.concession_per_round,
        )
        buyer_offer = max(buyer_offer, next_offer)
        conversation.append(
            _line(
                SpeakerType.MIDDLEMAN,
                middleman.id,
                middleman.preferred_language,
                language.buyer_counter.render(price=display_number(buyer_offer)),
                action="buyer_counter",
                price=str(buyer_offer),
                round=rounds,
            )
        )

        if buyer_offer >= target_price or buyer_offer == buyer_ceiling:
            break
        agent_ask = max(request.minimum_price_per_quintal, agent_ask - ask_reduction)

    status = (
        OfferStatus.QUALIFIED
        if buyer_offer >= request.minimum_price_per_quintal
        else OfferStatus.BELOW_FLOOR
    )
    if status is OfferStatus.QUALIFIED:
        conversation.append(
            _line(
                SpeakerType.NEGOTIATION_AGENT,
                "negotiation-agent",
                middleman.preferred_language,
                language.agent_close.render(price=display_number(buyer_offer)),
                action="record_provisional_quote",
                price=str(buyer_offer),
                accepted_counter=accepted_counter,
            )
        )
        conversation.append(
            _line(
                SpeakerType.MIDDLEMAN,
                middleman.id,
                middleman.preferred_language,
                language.buyer_ack.render(valid_hours=6),
                action="acknowledge_provisional_quote",
                valid_hours=6,
            )
        )
    else:
        conversation.append(
            _line(
                SpeakerType.NEGOTIATION_AGENT,
                "negotiation-agent",
                middleman.preferred_language,
                language.below_floor_close.render(
                    price=display_number(buyer_offer),
                    floor=display_number(request.minimum_price_per_quintal),
                ),
                action="reject_below_floor",
                price=str(buyer_offer),
            )
        )

    gross = buyer_offer * request.quantity_quintal
    transport = Decimal(0) if middleman.pickup_available else middleman.farmer_transport_cost_total
    net = gross - transport - middleman.handling_cost_total
    reliability_penalty = (Decimal(5) - middleman.reliability_score) * Decimal("0.005")
    payment_penalty = Decimal(middleman.payment_delay_days) * Decimal("0.001")
    risk_adjusted = net * (Decimal(1) - reliability_penalty - payment_penalty)

    return NegotiatedOffer(
        middleman_id=middleman.id,
        middleman_name=middleman.name,
        business_name=middleman.business_name,
        initial_price_per_quintal=middleman.initial_offer_per_quintal,
        final_price_per_quintal=buyer_offer,
        maximum_hidden_price_per_quintal=buyer_ceiling,
        quantity_quintal=request.quantity_quintal,
        pickup_available=middleman.pickup_available,
        farmer_transport_cost_total=transport,
        handling_cost_total=middleman.handling_cost_total,
        payment_delay_days=middleman.payment_delay_days,
        reliability_score=middleman.reliability_score,
        gross_total=gross.quantize(PAISE),
        estimated_net_total=net.quantize(PAISE),
        risk_adjusted_total=risk_adjusted.quantize(PAISE),
        status=status,
        rounds=rounds,
        market_id=middleman.market_id,
        conversation=conversation,
    )


def rank_offers(offers: list[NegotiatedOffer]) -> list[NegotiatedOffer]:
    qualified = [offer for offer in offers if offer.status is OfferStatus.QUALIFIED]
    unqualified = [offer for offer in offers if offer.status is not OfferStatus.QUALIFIED]
    qualified.sort(
        key=lambda offer: (
            offer.risk_adjusted_total,
            offer.estimated_net_total,
            offer.reliability_score,
            -offer.payment_delay_days,
        ),
        reverse=True,
    )
    ranked = [offer.model_copy(update={"rank": rank}) for rank, offer in enumerate(qualified, 1)]
    return ranked + unqualified
