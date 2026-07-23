from fund_analyzer import bond_methodology
from fund_analyzer.quarterly_parser import ExtractedValue, QuarterlyReport


def _parsed():
    return QuarterlyReport(
        source_file="sample.pdf",
        pages=10,
        fund_name="稳健中短债基金",
        manager_commentary="组合保持中短久期，以高等级信用债票息为主。",
        asset_allocation={"bond": ExtractedValue(110.0, "%", "债券投资110.0%")},
    )


def test_methodology_answers_three_core_questions():
    result = bond_methodology.evaluate_bond_fund(
        _parsed(),
        {
            "max_drawdown_pct": -0.8,
            "calmar_ratio": 2.5,
            "sharpe_ratio": 1.2,
            "annual_returns": [
                {"return_pct": 3.0, "is_partial": False},
                {"return_pct": 2.0, "is_partial": False},
            ],
        },
    )
    assert result["fund_type"] == "短债/中短债基金"
    assert any(item["label"] == "票息/持有收益" for item in result["earning_modes"])
    assert result["assessed_weight"] == 50
    assert len(result["score_rows"]) == 9
    assert "实时及历史久期" in result["missing_data"]


def test_methodology_detects_equity_and_convertible_risk():
    parsed = _parsed()
    parsed.fund_name = "示例可转债基金"
    parsed.asset_allocation["stock"] = ExtractedValue(12.0, "%", "股票投资12%")
    result = bond_methodology.evaluate_bond_fund(parsed)
    assert result["fund_type"] == "可转债/转债增强型"
    assert any("权益风险" in item for item in result["risk_flags"])
    assert any("转债风险" in item for item in result["risk_flags"])
