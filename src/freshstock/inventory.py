"""A deterministic, batch-aware inventory simulator with explicit accounting."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import ceil, isfinite


@dataclass(frozen=True)
class Scenario:
    lead_time: int = 2
    shelf_life: int = 7
    unit_cost: float = 1.0
    holding_cost: float = 0.02
    disposal_cost: float = 0.1
    lost_sale_penalty: float = 2.0
    warmup_days: int = 14

    def __post_init__(self) -> None:
        if not 1 <= self.lead_time <= 7 or self.shelf_life < 1 or self.warmup_days < 0:
            raise ValueError("Invalid lead time, shelf life or warm-up length.")
        for value in (self.unit_cost, self.holding_cost, self.disposal_cost, self.lost_sale_penalty):
            if not isfinite(value) or value < 0:
                raise ValueError("Costs must be finite and nonnegative.")


def simulate(demand: list[float], targets: list[float], scenario: Scenario) -> dict:
    """Place orders after demand; arrivals and expiry occur before next day's demand.

    targets[t] is the stock target predicted at the close of t. Targets are inputs,
    so every ordering policy can use the same demand stream without feedback leakage.
    """
    if len(demand) != len(targets) or len(demand) <= scenario.warmup_days:
        raise ValueError("Demand and targets must align and extend beyond the warm-up.")
    if any(not isfinite(value) or value < 0 for value in [*demand, *targets]):
        raise ValueError("Demand and targets must be finite and nonnegative.")
    if any(value != int(value) for value in demand):
        raise ValueError("The simulator requires whole-unit demand.")
    batches: list[dict] = []
    pipeline: list[dict] = []
    history = []
    for day, requested in enumerate(demand):
        opening = sum(batch["quantity"] for batch in batches)
        arrivals = [order for order in pipeline if order["arrival"] == day]
        received = sum(order["quantity"] for order in arrivals)
        batches.extend(
            {"quantity": order["quantity"], "expiry": day + scenario.shelf_life}
            for order in arrivals
        )
        pipeline = [order for order in pipeline if order["arrival"] != day]
        expired = sum(batch["quantity"] for batch in batches if batch["expiry"] <= day)
        batches = sorted(
            (batch for batch in batches if batch["expiry"] > day),
            key=lambda batch: batch["expiry"],
        )
        remaining = int(requested)
        for batch in batches:
            served = min(remaining, batch["quantity"])
            remaining -= served
            batch["quantity"] -= served
        batches = [batch for batch in batches if batch["quantity"]]
        closing = sum(batch["quantity"] for batch in batches)
        fulfilled = int(requested) - remaining
        if opening + received != fulfilled + expired + closing:
            raise AssertionError("Inventory conservation failed.")
        position = closing + sum(order["quantity"] for order in pipeline)
        ordered = max(0, ceil(targets[day] - position))
        if ordered:
            pipeline.append({"arrival": day + scenario.lead_time, "quantity": ordered})
        history.append(
            {
                "day": day,
                "demand": int(requested),
                "opening": opening,
                "received": received,
                "fulfilled": fulfilled,
                "expired": expired,
                "unmet": remaining,
                "closing": closing,
                "ordered": ordered,
                "cost": (
                    (fulfilled + expired) * scenario.unit_cost
                    + closing * scenario.holding_cost
                    + expired * scenario.disposal_cost
                    + remaining * scenario.lost_sale_penalty
                ),
            }
        )
    scored = history[scenario.warmup_days :]
    total_demand = sum(row["demand"] for row in scored)
    fulfilled = sum(row["fulfilled"] for row in scored)
    received = sum(row["received"] for row in scored)
    expired = sum(row["expired"] for row in scored)
    opening = scored[0]["opening"]
    closing = scored[-1]["closing"]
    return {
        "scenario": asdict(scenario),
        "days": len(scored),
        "fill_rate": fulfilled / total_demand if total_demand else None,
        "expired_units": expired,
        "waste_rate": expired / (opening + received) if opening + received else None,
        "unmet_units": total_demand - fulfilled,
        "cost": sum(row["cost"] for row in scored),
        "opening_units": opening,
        "received_units": received,
        "fulfilled_units": fulfilled,
        "closing_units": closing,
        "outstanding_units": sum(order["quantity"] for order in pipeline),
        "average_inventory": sum(row["closing"] for row in scored) / len(scored),
        "cash_outflow": received * scenario.unit_cost,
        "history": history,
    }
