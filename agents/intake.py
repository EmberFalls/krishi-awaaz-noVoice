"""Deterministic multilingual farmer-intake extraction and follow-up planning.

This module deliberately uses reviewable rules instead of an LLM.  It provides a
safe local prototype for collecting a request from free-form, possibly
mixed-language transcripts.  An LLM extractor can later implement the same
``FarmerIntakeDraft`` contract after it has been evaluated on real consented
calls.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, Field

from .models import ProduceListing


class FarmerIntakeDraft(BaseModel):
    """Fields observed during a voice intake; omitted fields require confirmation."""

    crop: str | None = None
    crop_local_name: str | None = None
    quantity_quintal: Decimal | None = Field(default=None, gt=0)
    minimum_price_per_quintal: Decimal | None = Field(default=None, gt=0)
    village: str | None = None
    pickup_preferred: bool | None = None
    payment_preference: str | None = None
    source_texts: list[str] = Field(default_factory=list)

    def missing_required_fields(self) -> list[str]:
        fields = {
            "crop": self.crop,
            "quantity": self.quantity_quintal,
            "minimum price": self.minimum_price_per_quintal,
            "village": self.village,
            "pickup preference": self.pickup_preferred,
        }
        return [name for name, value in fields.items() if value is None]


_CROPS: dict[str, tuple[str, str]] = {
    "onion": ("onion", "onion"),
    "प्याज": ("onion", "प्याज"),
    "कांदा": ("onion", "कांदा"),
    "प्याज़": ("onion", "प्याज़"),
    "ਪਿਆਜ਼": ("onion", "ਪਿਆਜ਼"),
    "வெங்காயம்": ("onion", "வெங்காயம்"),
    "ఉల్లిపాయ": ("onion", "ఉల్లిపాయ"),
    "ਟਮਾਟਰ": ("tomato", "ਟਮਾਟਰ"),
    "tomato": ("tomato", "tomato"),
    "टमाटर": ("tomato", "टमाटर"),
    "தக்காளி": ("tomato", "தக்காளி"),
    "టమాట": ("tomato", "టమాట"),
    "mirchi": ("dried_chilli", "mirchi"),
    "chilli": ("dried_chilli", "chilli"),
    "मिर्च": ("dried_chilli", "मिर्च"),
    "ਮਿਰਚ": ("dried_chilli", "ਮਿਰਚ"),
    "மிளகாய்": ("dried_chilli", "மிளகாய்"),
    "మిర్చి": ("dried_chilli", "మిర్చి"),
    "potato": ("potato", "potato"),
    "आलू": ("potato", "आलू"),
    "बटाटा": ("potato", "बटाटा"),
    "ਕਣਕ": ("wheat", "ਕਣਕ"),
    "wheat": ("wheat", "wheat"),
    "गेहूं": ("wheat", "गेहूं"),
    "rice": ("rice", "rice"),
    "धान": ("rice", "धान"),
    "भात": ("rice", "भात"),
    "नारियल": ("coconut", "नारियल"),
    "coconut": ("coconut", "coconut"),
}

_QUANTITY_PATTERN = re.compile(
    r"(?:quantity\s*(?:is|=)?\s*)?(\d+(?:\.\d+)?)\s*"
    r"(?:quintal|quintals|qtl|क्विंटल|किंटल|ਕੁਇੰਟਲ|குவிண்டால்|క్వింటాళ్లు)",
    re.IGNORECASE,
)
_PRICE_PATTERN = re.compile(
    r"(?:₹|rs\.?|inr|rupees?|रुपये|रुपये|ਰੁਪਏ|ரூபாய்|రూపాయలు)?\s*"
    r"(\d{3,6}(?:\.\d{1,2})?)\s*"
    r"(?:per\s*(?:quintal|qtl)|/\s*(?:quintal|qtl)|प्रति\s*क्विंटल|"
    r"ਪ੍ਰਤੀ\s*ਕੁਇੰਟਲ|ஒரு\s*குவிண்டாலுக்கு|క్వింటాల్\s*కి)",
    re.IGNORECASE,
)
_CURRENCY_PRICE_PATTERN = re.compile(r"(?:₹|rs\.?|inr)\s*([\d,]{3,8}(?:\.\d{1,2})?)", re.IGNORECASE)
_PREFIX_PRICE_PATTERN = re.compile(
    r"(?:क्विंटलला|ਕੁਇੰਟਲ(?:\s*ਲਈ)?|குவிண்டாலுக்கு|క్వింటాల్\s*కి)\s*"
    r"([\d,]{3,8}(?:\.\d{1,2})?)",
    re.IGNORECASE,
)
_VILLAGE_PATTERN = re.compile(
    r"(?:village|gaon|गांव|गाव|ਪਿੰਡ|கிராமம்|గ్రామం)\s*[:\-]?\s*"
    r"([A-Za-z\u0900-\u097F\u0A00-\u0A7F\u0B80-\u0BFF\u0C00-\u0C7F][\w\- ]{1,50})",
    re.IGNORECASE,
)


def extract_farmer_details(
    text: str, current: FarmerIntakeDraft | None = None
) -> FarmerIntakeDraft:
    """Merge facts found in one transcript into a draft.

    The most recent explicit answer wins, which lets a caller correct an
    earlier figure.  Numbers are deliberately accepted only with a unit so a
    phone number is never misclassified as a sale quantity or price.
    """

    draft = current.model_copy(deep=True) if current else FarmerIntakeDraft()
    clean_text = " ".join(_normalise_digits(text).split())
    lowered = clean_text.casefold()

    for term, (crop, local_name) in _CROPS.items():
        if term.casefold() in lowered:
            draft.crop, draft.crop_local_name = crop, local_name
            break
    if match := _QUANTITY_PATTERN.search(clean_text):
        draft.quantity_quintal = _decimal(match.group(1))
    if (
        (match := _CURRENCY_PRICE_PATTERN.search(clean_text))
        or (match := _PREFIX_PRICE_PATTERN.search(clean_text))
        or (match := _PRICE_PATTERN.search(clean_text))
    ):
        draft.minimum_price_per_quintal = _decimal(match.group(1))
    if match := _VILLAGE_PATTERN.search(clean_text):
        draft.village = match.group(1).strip(" .,")

    if any(
        term in lowered
        for term in ("pickup", "pick up", "गाड़ी भेज", "गाडी पाठव", "उचलला", "ਲੈ ਜਾਓ", "வண்டி", "వాహనం")
    ):
        draft.pickup_preferred = True
    if any(
        term in lowered
        for term in (
            "i will deliver",
            "deliver myself",
            "खुद पहुंचा",
            "स्वतः आण",
            "ਆਪ ਲੈ",
            "நானே கொண்டு",
            "నేనే తీసుక",
        )
    ):
        draft.pickup_preferred = False
    if any(term in lowered for term in ("same day", "today", "आज", "आजच", "ਅੱਜ", "இன்றே", "ఈరోజే")):
        draft.payment_preference = "same_day"
    elif any(term in lowered for term in ("bank transfer", "upi", "बैंक", "ਬੈਂਕ", "வங்கி", "బ్యాంక్")):
        draft.payment_preference = "bank_transfer"

    draft.source_texts.append(clean_text)
    return draft


def apply_draft_to_listing(listing: ProduceListing, draft: FarmerIntakeDraft) -> ProduceListing:
    """Create a listing using confirmed voice facts and safe fixture defaults."""

    updates: dict[str, object] = {}
    for field in (
        "crop",
        "crop_local_name",
        "quantity_quintal",
        "minimum_price_per_quintal",
        "pickup_preferred",
    ):
        value = getattr(draft, field)
        if value is not None:
            updates[field] = value
    return listing.model_copy(update=updates)


def next_follow_up(draft: FarmerIntakeDraft, language: str) -> str | None:
    """Return the next concise question, or ``None`` once required facts exist."""

    prompts = {
        "crop": {
            "mr-IN": "तुम्ही कोणते पीक विकत आहात?",
            "pa-IN": "ਤੁਸੀਂ ਕਿਹੜੀ ਫਸਲ ਵੇਚ ਰਹੇ ਹੋ?",
            "ta-IN": "நீங்கள் எந்த பயிரை விற்கிறீர்கள்?",
            "te-IN": "మీరు ఏ పంట అమ్ముతున్నారు?",
            "default": "Which crop are you selling?",
        },
        "quantity": {"default": "How many quintals are available?"},
        "minimum price": {"default": "What is your minimum price per quintal?"},
        "village": {"default": "Which village is the produce in?"},
        "pickup preference": {"default": "Should the buyer arrange pickup, or will you deliver?"},
    }
    missing = draft.missing_required_fields()
    if not missing:
        return None
    choices = prompts[missing[0]]
    return choices.get(language, choices["default"])


def _decimal(value: str) -> Decimal | None:
    try:
        return Decimal(value.replace(",", ""))
    except InvalidOperation:
        return None


def _normalise_digits(text: str) -> str:
    return text.translate(str.maketrans("०१२३४५६७८९٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
