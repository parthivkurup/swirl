from enum import Enum

from pydantic import BaseModel


class DealType(str, Enum):
    percent_off = "percent_off"
    dollar_off = "dollar_off"
    fixed_price = "fixed_price"
    bogo = "bogo"
    freebie = "freebie"
    loyalty = "loyalty"
    bundle = "bundle"


class DiscountUnit(str, Enum):
    percent = "percent"
    aud = "aud"


class Channel(str, Enum):
    dine_in = "dine_in"
    takeaway = "takeaway"
    app = "app"
    delivery = "delivery"


class UnitBasis(str, Enum):
    flat = "flat"
    per_100g = "per_100g"
    per_kg = "per_kg"


class Category(str, Enum):
    froyo = "froyo"
    adjacent = "adjacent"
    other = "other"


class StatedLocation(str, Enum):
    """What the SOURCE says about where the offer applies. Deliberately not the
    deal's scope: the extractor reports caption-local evidence and nothing more.

    What silence means is a property of the CHAIN, not of the caption - for a
    one-shop Melbourne operator it means Melbourne, and for a national chain it
    means genuinely unknown - so the extractor is never asked to interpret it.
    ingest.postprocess.derive_scope combines this with the chain's footprint.
    """

    melbourne = "melbourne"  # a place is named, and it is in Greater Melbourne
    other = "other"  # a place is named, and it is definitely not
    unclear = "unclear"  # a place is named but cannot be placed (Richmond, a venue name)
    none = "none"  # no place named at all


class Deal(BaseModel):
    headline: str
    deal_type: DealType
    category: Category
    discount_value: float | None
    discount_unit: DiscountUnit | None
    unit_basis: UnitBasis | None
    conditions: str | None
    min_spend_aud: float | None
    max_grams: int | None
    channels: list[Channel]
    days_of_week: list[int]
    valid_from: str | None
    valid_to: str | None
    recurring: bool
    store_hint: str | None
    stated_location: StatedLocation
    confidence: float


class CaptionResult(BaseModel):
    # Echoes the CAPTION number from the request header, so the reader can verify
    # the response is aligned to the inputs (no reorder / drop-and-duplicate)
    # rather than trusting array position alone.
    caption_index: int
    deals: list[Deal]


class BatchResult(BaseModel):
    # One CaptionResult per input caption, in input order.
    captions: list[CaptionResult]
