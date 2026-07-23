import pandas as pd

from fund_analyzer import performance_summary


def _sample_nav():
    return pd.DataFrame(
        {
            "date": [
                "2022-06-01",
                "2022-12-30",
                "2023-01-03",
                "2023-12-29",
                "2024-01-02",
                "2024-12-31",
            ],
            "nav": [1.00, 1.10, 1.10, 1.21, 1.21, 1.089],
            "acc_nav": [1.00, 1.10, 1.10, 1.21, 1.21, 1.089],
        }
    )


def test_annual_returns_cover_every_year_since_inception():
    rows = performance_summary.calculate_annual_returns(_sample_nav())
    assert [row["year"] for row in rows] == [2022, 2023, 2024]
    assert round(rows[0]["return_pct"], 2) == 10.00
    assert round(rows[1]["return_pct"], 2) == 10.00
    assert round(rows[2]["return_pct"], 2) == -10.00
    assert rows[0]["is_partial"] is True
    assert rows[1]["is_partial"] is False


def test_performance_summary_contains_risk_metrics_and_annual_returns():
    result = performance_summary.calculate_performance_summary(_sample_nav())
    assert result["analysis_start"] == "2022-06-01"
    assert result["analysis_end"] == "2024-12-31"
    assert result["max_drawdown_pct"] == 10.0
    assert len(result["annual_returns"]) == 3
    assert "sharpe_ratio" in result
