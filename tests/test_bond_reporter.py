import pandas as pd

from fund_analyzer.bond_attribution import attribute_returns
from fund_analyzer.bond_reporter import (
    generate_client_report,
    generate_professional_report,
)


def _result():
    dates = pd.bdate_range("2025-01-01", periods=40)
    factors = pd.DataFrame(
        {"rate": [0.001, -0.0005] * 20, "credit": [0.0002, 0.0001] * 20},
        index=dates,
    )
    fund = 0.00001 + 0.6 * factors["rate"] + 0.2 * factors["credit"]
    return attribute_returns(fund, factors)


def test_two_report_versions_have_distinct_audiences():
    result = _result()
    professional = generate_professional_report(
        fund_code="000001", fund_name="示例债基", attribution=result
    )
    client = generate_client_report(
        fund_code="000001", fund_name="示例债基", attribution=result
    )
    assert "拟合优度 R²" in professional
    assert "原文证据" not in client
    assert "需要接受什么风险" in client
