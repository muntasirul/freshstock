import pytest

from freshstock.inventory import Scenario, simulate


def test_delivery_expiry_and_conservation():
    result = simulate(
        demand=[3, 2, 0, 0, 0, 0],
        targets=[10, 0, 0, 0, 0, 0],
        scenario=Scenario(lead_time=1, shelf_life=2, warmup_days=0),
    )
    assert result["history"][0]["unmet"] == 3
    assert result["history"][1]["received"] == 10
    assert result["history"][3]["expired"] == 8
    assert result["opening_units"] + result["received_units"] == (
        result["fulfilled_units"] + result["expired_units"] + result["closing_units"]
    )


def test_simulator_rejects_fractional_demand():
    with pytest.raises(ValueError, match="whole-unit"):
        simulate(
            [1.5, 0, 0],
            [0, 0, 0],
            Scenario(lead_time=1, shelf_life=1, warmup_days=0),
        )
