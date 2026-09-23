from decimal import Decimal

from agents.intake import extract_farmer_details, next_follow_up


def test_extracts_mixed_language_farmer_sale_facts() -> None:
    draft = extract_farmer_details(
        "Village Niphad. 50 quintals कांदा, minimum ₹1,750 per quintal. Buyer pickup please, UPI same day."
    )

    assert draft.crop == "onion"
    assert draft.quantity_quintal == Decimal(50)
    assert draft.minimum_price_per_quintal == Decimal(1750)
    assert draft.village == "Niphad"
    assert draft.pickup_preferred is True
    assert draft.payment_preference == "same_day"
    assert draft.missing_required_fields() == []


def test_extracts_indic_digits_and_asks_only_for_missing_field() -> None:
    draft = extract_farmer_details("माझ्याकडे ५० क्विंटल कांदा आहे. क्विंटलला १,७५० रुपयांपेक्षा कमी नको.")

    assert draft.quantity_quintal == Decimal(50)
    assert draft.minimum_price_per_quintal == Decimal(1750)
    assert next_follow_up(draft, "mr-IN") == "Which village is the produce in?"


def test_latest_explicit_quantity_corrects_prior_value() -> None:
    draft = extract_farmer_details("30 quintals tomato, village Alanganallur")
    draft = extract_farmer_details("Correction: 35 quintals tomato.", draft)

    assert draft.quantity_quintal == Decimal(35)
