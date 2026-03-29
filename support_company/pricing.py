"""Pricing catalog for waste orders and operational actions."""

from __future__ import annotations

from dataclasses import dataclass, asdict

import random

from .models import ServiceWindow, WasteType


@dataclass(frozen=True)
class MarketPriceOption:
    option_id: str
    waste_type: str
    label: str
    category: str
    unit: str
    base_price_eur: float
    size_m3: float | None = None
    price_per_m3_eur: float | None = None
    price_per_kg_eur: float | None = None
    notes: str | None = None
    source_name: str = ""
    source_url: str = ""
    source_date: str | None = None


@dataclass(frozen=True)
class OperationalPriceOption:
    option_id: str
    waste_type: str
    bot_action: str
    label: str
    capacity_m3: float | None = None
    rental_cost_per_cycle_eur: float | None = None
    early_empty_cost_eur: float | None = None
    turnaround_hours: int | None = None
    notes: str | None = None
    derived_from_source: str | None = None


MARKET_PRICE_OPTIONS: tuple[MarketPriceOption, ...] = (
    MarketPriceOption(
        option_id="paper_container_7m3_zacelle",
        waste_type=WasteType.PAPER.value,
        label="Paper container 7 m3",
        category="customer_quote",
        unit="container",
        size_m3=7.0,
        base_price_eur=103.0,
        price_per_m3_eur=14.71,
        notes="Flat fee for paper/cardboard container.",
        source_name="Zweckverband Abfallwirtschaft Celle",
        source_url="https://www.zacelle.de/container/groessen-gebuehren/",
        source_date="2026-03-22",
    ),
    MarketPriceOption(
        option_id="paper_container_10m3_zacelle",
        waste_type=WasteType.PAPER.value,
        label="Paper container 10 m3",
        category="customer_quote",
        unit="container",
        size_m3=10.0,
        base_price_eur=103.0,
        price_per_m3_eur=10.3,
        notes="Flat fee for paper/cardboard container.",
        source_name="Zweckverband Abfallwirtschaft Celle",
        source_url="https://www.zacelle.de/container/groessen-gebuehren/",
        source_date="2026-03-22",
    ),
    MarketPriceOption(
        option_id="organic_container_7m3_zacelle",
        waste_type=WasteType.ORGANIC.value,
        label="Green or organic waste container 7 m3",
        category="customer_quote",
        unit="container",
        size_m3=7.0,
        base_price_eur=162.5,
        price_per_m3_eur=23.21,
        notes="Plus daily standing fee of 0.61 EUR.",
        source_name="Zweckverband Abfallwirtschaft Celle",
        source_url="https://www.zacelle.de/container/groessen-gebuehren/",
        source_date="2026-03-22",
    ),
    MarketPriceOption(
        option_id="organic_container_10m3_zacelle",
        waste_type=WasteType.ORGANIC.value,
        label="Green or organic waste container 10 m3",
        category="customer_quote",
        unit="container",
        size_m3=10.0,
        base_price_eur=188.0,
        price_per_m3_eur=18.8,
        notes="Plus daily standing fee of 0.61 EUR.",
        source_name="Zweckverband Abfallwirtschaft Celle",
        source_url="https://www.zacelle.de/container/groessen-gebuehren/",
        source_date="2026-03-22",
    ),
    MarketPriceOption(
        option_id="residual_container_7m3_zacelle",
        waste_type=WasteType.RESIDUAL.value,
        label="Mixed or residual waste container 7 m3",
        category="customer_quote",
        unit="container",
        size_m3=7.0,
        base_price_eur=285.0,
        price_per_m3_eur=40.71,
        notes="Mixed waste container, max 2.8 tonnes, plus daily standing fee of 0.61 EUR.",
        source_name="Zweckverband Abfallwirtschaft Celle",
        source_url="https://www.zacelle.de/container/groessen-gebuehren/",
        source_date="2026-03-22",
    ),
    MarketPriceOption(
        option_id="residual_dropoff_m3_aws",
        waste_type=WasteType.RESIDUAL.value,
        label="Residual waste drop-off rate",
        category="dropoff_rate",
        unit="m3",
        base_price_eur=45.0,
        price_per_m3_eur=45.0,
        notes="Residual waste up to 2 m3, billed per started cubic meter.",
        source_name="Abfallwirtschaft Schaumburg",
        source_url="https://aws-shg.de/entgelte-dauerannahmestellen.html",
        source_date="2026-03-22",
    ),
    MarketPriceOption(
        option_id="recycling_small_quote_containerfritze",
        waste_type=WasteType.RECYCLING.value,
        label="Mixed commercial recycling starting quote",
        category="customer_quote",
        unit="order",
        base_price_eur=99.0,
        notes="Starting quote for mixed commercial waste and recyclable business waste.",
        source_name="Containerfritze Berlin",
        source_url="https://containerfritze.de/gewerbeabfall-entsorgen-berlin/",
        source_date="2026-03-22",
    ),
    MarketPriceOption(
        option_id="recycling_container_7m3_langezaal",
        waste_type=WasteType.RECYCLING.value,
        label="Commercial waste container 7 m3",
        category="customer_quote",
        unit="container",
        size_m3=7.0,
        base_price_eur=585.0,
        price_per_m3_eur=83.57,
        notes="7 m3 commercial-waste container price shown for the Emsland region.",
        source_name="Langezaal Container",
        source_url="https://www.langezaalcontainer.de/gewerbeabfall/7m3-container/",
        source_date="2026-03-22",
    ),
    MarketPriceOption(
        option_id="glass_container_7m3_langezaal",
        waste_type=WasteType.GLASS.value,
        label="Glass container 7 m3",
        category="customer_quote",
        unit="container",
        size_m3=7.0,
        base_price_eur=435.0,
        price_per_m3_eur=62.14,
        notes="7 m3 glass container price shown for the Emsland region.",
        source_name="Langezaal Container",
        source_url="https://www.langezaalcontainer.de/glas/7m3-container/",
        source_date="2026-03-22",
    ),
    MarketPriceOption(
        option_id="hazardous_chemicals_bsr",
        waste_type=WasteType.HAZARDOUS.value,
        label="Hazardous chemicals disposal",
        category="hazardous_handling",
        unit="kg",
        base_price_eur=6.4,
        price_per_kg_eur=6.4,
        notes="Commercial small-quantity hazardous chemicals.",
        source_name="Berliner Stadtreinigung",
        source_url="https://www.bsr.de/assets/downloads/BSR-infoblatt-preislisten-schadstoffe-kleinmengen.pdf",
        source_date="2026-03-22",
    ),
    MarketPriceOption(
        option_id="hazardous_acids_bsr",
        waste_type=WasteType.HAZARDOUS.value,
        label="Hazardous acids or alkalis disposal",
        category="hazardous_handling",
        unit="kg",
        base_price_eur=2.1,
        price_per_kg_eur=2.1,
        notes="Commercial small-quantity acids and alkalis.",
        source_name="Berliner Stadtreinigung",
        source_url="https://www.bsr.de/assets/downloads/BSR-infoblatt-preislisten-schadstoffe-kleinmengen.pdf",
        source_date="2026-03-22",
    ),
    MarketPriceOption(
        option_id="hazardous_paint_aws",
        waste_type=WasteType.HAZARDOUS.value,
        label="Hazardous paints and coatings disposal",
        category="hazardous_handling",
        unit="kg",
        base_price_eur=2.56,
        price_per_kg_eur=2.56,
        notes="Altfarben and Altlacke rate.",
        source_name="Abfallwirtschaft Schaumburg",
        source_url="https://aws-shg.de/entgelte-dauerannahmestellen.html",
        source_date="2026-03-22",
    ),
)


OPERATIONAL_PRICE_OPTIONS: tuple[OperationalPriceOption, ...] = (
    OperationalPriceOption(
        option_id="rent_residual_8m3",
        waste_type=WasteType.RESIDUAL.value,
        bot_action="rent_container",
        label="Residual overflow exchange unit 8 m3",
        capacity_m3=8.0,
        rental_cost_per_cycle_eur=180.0,
        early_empty_cost_eur=160.0,
        turnaround_hours=24,
        notes="Owned-fleet overflow exchange benchmark for standard residual pickups.",
        derived_from_source="ZAC Celle mixed-waste 7-10 m3 container pricing",
    ),
    OperationalPriceOption(
        option_id="rent_residual_14m3",
        waste_type=WasteType.RESIDUAL.value,
        bot_action="rent_container",
        label="Residual overflow exchange unit 14 m3",
        capacity_m3=14.0,
        rental_cost_per_cycle_eur=260.0,
        early_empty_cost_eur=210.0,
        turnaround_hours=24,
        notes="Larger exchange unit for high-pressure residual periods.",
        derived_from_source="Derived from mixed-waste container market rates and urgent transport overhead",
    ),
    OperationalPriceOption(
        option_id="rent_recycling_8m3",
        waste_type=WasteType.RECYCLING.value,
        bot_action="rent_container",
        label="Recycling overflow exchange unit 8 m3",
        capacity_m3=8.0,
        rental_cost_per_cycle_eur=160.0,
        early_empty_cost_eur=140.0,
        turnaround_hours=24,
        notes="Overflow exchange option for mixed recycling capacity.",
        derived_from_source="Derived from mixed commercial-waste and recycling quotes",
    ),
    OperationalPriceOption(
        option_id="rent_paper_7m3",
        waste_type=WasteType.PAPER.value,
        bot_action="rent_container",
        label="Paper overflow exchange unit 7 m3",
        capacity_m3=7.0,
        rental_cost_per_cycle_eur=120.0,
        early_empty_cost_eur=120.0,
        turnaround_hours=36,
        notes="Low-cost paper exchange option for temporary overflow.",
        derived_from_source="Derived from ZAC Celle paper container pricing",
    ),
    OperationalPriceOption(
        option_id="rent_glass_7m3",
        waste_type=WasteType.GLASS.value,
        bot_action="rent_container",
        label="Glass overflow exchange unit 7 m3",
        capacity_m3=7.0,
        rental_cost_per_cycle_eur=170.0,
        early_empty_cost_eur=155.0,
        turnaround_hours=48,
        notes="Glass exchange option with higher hauling burden.",
        derived_from_source="Derived from Langezaal 7 m3 glass container pricing",
    ),
    OperationalPriceOption(
        option_id="rent_organic_7m3",
        waste_type=WasteType.ORGANIC.value,
        bot_action="rent_container",
        label="Organic overflow exchange unit 7 m3",
        capacity_m3=7.0,
        rental_cost_per_cycle_eur=150.0,
        early_empty_cost_eur=135.0,
        turnaround_hours=24,
        notes="Organic exchange option with tighter servicing cadence.",
        derived_from_source="Derived from ZAC Celle green-waste container pricing",
    ),
    OperationalPriceOption(
        option_id="rent_hazardous_6m3",
        waste_type=WasteType.HAZARDOUS.value,
        bot_action="rent_container",
        label="Hazardous specialist exchange unit 6 m3",
        capacity_m3=6.0,
        rental_cost_per_cycle_eur=260.0,
        early_empty_cost_eur=220.0,
        turnaround_hours=12,
        notes="Specialist exchange option for hazardous overflow handling.",
        derived_from_source="Derived from Berlin hazardous small-quantity handling rates and specialist transport overhead",
    ),
    OperationalPriceOption(
        option_id="early_empty_standard",
        waste_type="all",
        bot_action="schedule_early_empty",
        label="Standard early empty slot",
        early_empty_cost_eur=120.0,
        turnaround_hours=12,
        notes="Best-effort same-shift emptying.",
        derived_from_source="Derived from container transport and handling surcharges in public price lists",
    ),
    OperationalPriceOption(
        option_id="early_empty_priority",
        waste_type="all",
        bot_action="schedule_early_empty",
        label="Priority early empty slot",
        early_empty_cost_eur=165.0,
        turnaround_hours=6,
        notes="Faster intervention with tighter dispatch priority.",
        derived_from_source="Derived from urgent transport markup against public container rates",
    ),
    OperationalPriceOption(
        option_id="early_empty_hazardous",
        waste_type=WasteType.HAZARDOUS.value,
        bot_action="schedule_early_empty",
        label="Hazardous early empty slot",
        early_empty_cost_eur=220.0,
        turnaround_hours=4,
        notes="Specialist call-out for hazardous capacity recovery.",
        derived_from_source="Derived from hazardous handling rates and specialist dispatch assumptions",
    ),
)


WASTE_DENSITY_KG_PER_M3 = {
    WasteType.RESIDUAL.value: 140.0,
    WasteType.RECYCLING.value: 95.0,
    WasteType.PAPER.value: 60.0,
    WasteType.GLASS.value: 380.0,
    WasteType.ORGANIC.value: 320.0,
    WasteType.HAZARDOUS.value: 40.0,
}

QUOTE_MARGIN_MULTIPLIER = {
    WasteType.RESIDUAL.value: 1.12,
    WasteType.RECYCLING.value: 1.1,
    WasteType.PAPER.value: 1.12,
    WasteType.GLASS.value: 1.1,
    WasteType.ORGANIC.value: 1.12,
    WasteType.HAZARDOUS.value: 1.14,
}

SERVICE_BASE_COST_EUR = {
    WasteType.RESIDUAL.value: 58.0,
    WasteType.RECYCLING.value: 40.0,
    WasteType.PAPER.value: 24.0,
    WasteType.GLASS.value: 48.0,
    WasteType.ORGANIC.value: 42.0,
    WasteType.HAZARDOUS.value: 110.0,
}

SERVICE_COST_PER_M3_EUR = {
    WasteType.RESIDUAL.value: 11.0,
    WasteType.RECYCLING.value: 8.0,
    WasteType.PAPER.value: 5.0,
    WasteType.GLASS.value: 12.0,
    WasteType.ORGANIC.value: 13.0,
    WasteType.HAZARDOUS.value: 34.0,
}


def list_market_price_options(waste_type: str | None = None) -> list[dict]:
    options = [asdict(option) for option in MARKET_PRICE_OPTIONS]
    if waste_type is None:
        return options
    return [option for option in options if option["waste_type"] == waste_type]


def list_operational_price_options(waste_type: str | None = None) -> list[dict]:
    options = [asdict(option) for option in OPERATIONAL_PRICE_OPTIONS]
    if waste_type is None:
        return options
    return [option for option in options if option["waste_type"] in {waste_type, "all"}]


def estimate_customer_quote(
    *,
    waste_type: WasteType,
    quantity_m3: float,
    service_window: ServiceWindow,
    contamination_risk: bool = False,
    hazardous_flag: bool = False,
    rng: random.Random,
) -> float:
    matches = [option for option in MARKET_PRICE_OPTIONS if option.waste_type == waste_type.value]
    if not matches:
        return round(quantity_m3 * 50.0, 2)

    chosen = rng.choice(matches)
    if chosen.price_per_m3_eur is not None:
        price = chosen.price_per_m3_eur * quantity_m3
    elif chosen.price_per_kg_eur is not None:
        density = WASTE_DENSITY_KG_PER_M3[waste_type.value]
        price = chosen.price_per_kg_eur * density * quantity_m3
    elif chosen.size_m3:
        price = chosen.base_price_eur * (quantity_m3 / chosen.size_m3)
    else:
        price = chosen.base_price_eur

    if service_window == ServiceWindow.SAME_DAY:
        price *= 1.18
    elif service_window == ServiceWindow.NEXT_DAY:
        price *= 1.05

    projected_cost = estimate_service_cost(
        waste_type=waste_type,
        quantity_m3=quantity_m3,
        service_window=service_window,
        contamination_risk=contamination_risk,
        hazardous_flag=hazardous_flag,
    )
    minimum_viable_quote = (projected_cost * QUOTE_MARGIN_MULTIPLIER[waste_type.value]) + 8.0
    price = max(price, minimum_viable_quote)

    return round(price, 2)


def estimate_service_cost(
    *,
    waste_type: WasteType,
    quantity_m3: float,
    service_window: ServiceWindow,
    contamination_risk: bool,
    hazardous_flag: bool,
) -> float:
    base = SERVICE_BASE_COST_EUR[waste_type.value]
    variable = SERVICE_COST_PER_M3_EUR[waste_type.value] * quantity_m3
    subtotal = base + variable

    if service_window == ServiceWindow.SAME_DAY:
        subtotal *= 1.22
    elif service_window == ServiceWindow.NEXT_DAY:
        subtotal *= 1.05
    else:
        subtotal *= 0.94

    if contamination_risk:
        subtotal += 14.0
    if hazardous_flag:
        subtotal += 35.0

    return round(subtotal, 2)


def estimate_payment_delay_hours(service_window: ServiceWindow) -> int:
    if service_window == ServiceWindow.SAME_DAY:
        return 48
    if service_window == ServiceWindow.NEXT_DAY:
        return 72
    return 96


def estimate_vendor_payment_delay_hours(service_window: ServiceWindow, hazardous_flag: bool) -> int:
    if hazardous_flag:
        return 12
    if service_window == ServiceWindow.SAME_DAY:
        return 12
    if service_window == ServiceWindow.NEXT_DAY:
        return 24
    return 36
