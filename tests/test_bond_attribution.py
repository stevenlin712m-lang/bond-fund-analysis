import numpy as np
import pandas as pd

from fund_analyzer.bond_attribution import attribute_returns, returns_from_nav


def test_attribution_recovers_known_exposures():
    rng = np.random.default_rng(7)
    dates = pd.bdate_range("2024-01-02", periods=240)
    factors = pd.DataFrame(
        {
            "rate": rng.normal(0, 0.002, len(dates)),
            "credit": rng.normal(0, 0.001, len(dates)),
        },
        index=dates,
    )
    fund = 0.00002 + 0.8 * factors["rate"] + 0.3 * factors["credit"]
    result = attribute_returns(fund, factors)
    by_name = {item.factor: item for item in result.factors}

    assert result.observations == 240
    assert result.r_squared > 0.999
    assert by_name["rate"].beta == pytest.approx(0.8, abs=1e-8)
    assert by_name["credit"].beta == pytest.approx(0.3, abs=1e-8)


def test_returns_from_nav():
    dates = pd.date_range("2025-01-01", periods=3)
    nav = pd.Series([1.0, 1.01, 1.0201], index=dates)
    result = returns_from_nav(nav)
    assert result.tolist() == pytest.approx([0.01, 0.01])


import pytest
