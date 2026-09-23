from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SpeakerType(str, Enum):
    FARMER = "farmer"
    INTAKE_AGENT = "intake_agent"
    NEGOTIATION_AGENT = "negotiation_agent"
    MIDDLEMAN = "middleman"
    REPORTING_AGENT = "reporting_agent"
    SYSTEM = "system"


class OfferStatus(str, Enum):
    QUALIFIED = "qualified"
    BELOW_FLOOR = "below_floor"
    CROP_MISMATCH = "crop_mismatch"
    QUANTITY_MISMATCH = "quantity_mismatch"


class Location(BaseModel):
    village: str
    district: str
    state: str
    latitude: float | None = None
    longitude: float | None = None

    @property
    def label(self) -> str:
        return f"{self.village}, {self.district}, {self.state}"


class ProduceListing(BaseModel):
    id: str
    crop: str
    crop_local_name: str
    variety: str
    quantity_quintal: Decimal = Field(gt=0)
    quality_grade: str
    minimum_price_per_quintal: Decimal = Field(gt=0)
    urgency_hours: int = Field(gt=0)
    harvest_age_days: int = Field(ge=0)
    pickup_preferred: bool = True
    notes: str = ""


class FarmerProfile(BaseModel):
    id: str
    name: str
    location: Location
    preferred_language: str
    preferred_language_name: str
    secondary_languages: list[str] = Field(default_factory=list)
    phone_alias: str


class DialogueLine(BaseModel):
    speaker: SpeakerType
    text: str
    english_translation: str
    language: str
    speaker_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MarketSnapshot(BaseModel):
    id: str
    market_name: str
    district: str
    state: str
    crop: str
    min_price_per_quintal: Decimal = Field(gt=0)
    modal_price_per_quintal: Decimal = Field(gt=0)
    max_price_per_quintal: Decimal = Field(gt=0)
    distance_km: Decimal = Field(ge=0)
    transport_cost_total: Decimal = Field(ge=0)
    fees_total: Decimal = Field(ge=0)
    data_age_hours: int = Field(ge=0)

    @model_validator(mode="after")
    def prices_are_ordered(self) -> MarketSnapshot:
        if not (
            self.min_price_per_quintal <= self.modal_price_per_quintal <= self.max_price_per_quintal
        ):
            raise ValueError("market prices must satisfy min <= modal <= max")
        return self


class MiddlemanProfile(BaseModel):
    id: str
    name: str
    business_name: str
    market_id: str
    location: Location
    preferred_language: str
    supported_crops: list[str]
    minimum_quantity_quintal: Decimal = Field(gt=0)
    maximum_quantity_quintal: Decimal = Field(gt=0)
    initial_offer_per_quintal: Decimal = Field(gt=0)
    maximum_offer_per_quintal: Decimal = Field(gt=0)
    concession_per_round: Decimal = Field(gt=0)
    pickup_available: bool
    farmer_transport_cost_total: Decimal = Field(ge=0)
    handling_cost_total: Decimal = Field(ge=0)
    payment_delay_days: int = Field(ge=0)
    reliability_score: Decimal = Field(ge=1, le=5)
    negotiation_style: str
    is_available: bool = True
    available_quantity_quintal: Decimal | None = Field(default=None, gt=0)
    accepted_quality_keywords: list[str] = Field(default_factory=list)
    pickup_radius_km: Decimal | None = Field(default=None, ge=0)
    competing_demand_modifier_per_quintal: Decimal = Decimal(0)

    @model_validator(mode="after")
    def constraints_are_consistent(self) -> MiddlemanProfile:
        if self.minimum_quantity_quintal > self.maximum_quantity_quintal:
            raise ValueError("minimum quantity cannot exceed maximum quantity")
        if self.initial_offer_per_quintal > self.maximum_offer_per_quintal:
            raise ValueError("initial offer cannot exceed maximum offer")
        return self


class SimulationScenario(BaseModel):
    id: str
    title: str
    description: str
    farmer: FarmerProfile
    listing: ProduceListing
    intake_dialogue: list[DialogueLine]
    markets: list[MarketSnapshot]
    middlemen: list[MiddlemanProfile]

    @model_validator(mode="after")
    def references_are_valid(self) -> SimulationScenario:
        market_ids = {market.id for market in self.markets}
        unknown = {
            middleman.market_id
            for middleman in self.middlemen
            if middleman.market_id not in market_ids
        }
        if unknown:
            raise ValueError(f"middlemen reference unknown markets: {sorted(unknown)}")
        if not self.intake_dialogue:
            raise ValueError("scenario must include an intake dialogue")
        return self


class FarmerRequest(BaseModel):
    farmer_id: str
    farmer_name: str
    location: Location
    preferred_language: str
    listing_id: str
    crop: str
    crop_local_name: str
    variety: str
    quantity_quintal: Decimal
    quality_grade: str
    minimum_price_per_quintal: Decimal
    urgency_hours: int
    pickup_preferred: bool
    notes: str


class MarketAssessment(BaseModel):
    market: MarketSnapshot
    estimated_gross_total: Decimal
    estimated_net_total: Decimal
    estimated_net_per_quintal: Decimal
    rank: int = 0


class NegotiatedOffer(BaseModel):
    middleman_id: str
    middleman_name: str
    business_name: str
    initial_price_per_quintal: Decimal
    final_price_per_quintal: Decimal
    maximum_hidden_price_per_quintal: Decimal = Field(exclude=True)
    quantity_quintal: Decimal
    pickup_available: bool
    farmer_transport_cost_total: Decimal
    handling_cost_total: Decimal
    payment_delay_days: int
    reliability_score: Decimal
    gross_total: Decimal
    estimated_net_total: Decimal
    risk_adjusted_total: Decimal
    status: OfferStatus
    rounds: int
    market_id: str
    conversation: list[DialogueLine]
    rank: int | None = None


class WorkflowEvent(BaseModel):
    node: str
    message: str
    data: dict[str, Any] = Field(default_factory=dict)


class SimulationResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    run_id: str
    scenario_id: str
    scenario_title: str
    farmer_request: FarmerRequest
    intake_dialogue: list[DialogueLine]
    market_assessments: list[MarketAssessment]
    offers: list[NegotiatedOffer]
    recommended_middleman_id: str | None
    report_text: str
    events: list[WorkflowEvent]
