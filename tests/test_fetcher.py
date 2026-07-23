import pandas as pd

from fund_analyzer import fetcher


def test_get_fund_nav_supports_current_akshare(monkeypatch, tmp_path):
    monkeypatch.setattr(fetcher, "CACHE_DIR", str(tmp_path))
    monkeypatch.delattr(fetcher.ak, "fund_open_fund_hist_em", raising=False)

    def fake_info(symbol, indicator, period):
        assert symbol == "013864"
        assert period == "成立来"
        if indicator == "单位净值走势":
            return pd.DataFrame(
                {
                    "净值日期": pd.to_datetime(
                        ["2023-12-29", "2024-01-02", "2024-12-31"]
                    ).date,
                    "单位净值": [1.01, 1.02, 1.05],
                    "日增长率": [0.01, 0.02, 0.03],
                }
            )
        return pd.DataFrame(
            {
                "净值日期": pd.to_datetime(
                    ["2023-12-29", "2024-01-02", "2024-12-31"]
                ).date,
                "累计净值": [1.01, 1.02, 1.05],
            }
        )

    monkeypatch.setattr(fetcher.ak, "fund_open_fund_info_em", fake_info)

    result = fetcher.get_fund_nav(
        "013864",
        start_date="2024-01-01",
        end_date="2024-12-31",
    )

    assert list(result.columns) == ["date", "nav", "daily_return", "acc_nav"]
    assert result["date"].dt.strftime("%Y-%m-%d").tolist() == [
        "2024-01-02",
        "2024-12-31",
    ]
    assert result["acc_nav"].tolist() == [1.02, 1.05]


def test_get_fund_nav_keeps_legacy_akshare_path(monkeypatch, tmp_path):
    monkeypatch.setattr(fetcher, "CACHE_DIR", str(tmp_path))

    def fake_legacy(**kwargs):
        assert kwargs["indicator"] == "累计净值"
        return pd.DataFrame(
            {
                "净值日期": ["2024-01-02"],
                "单位净值": [1.02],
                "累计净值": [1.02],
                "日增长率": [0.02],
            }
        )

    monkeypatch.setattr(
        fetcher.ak, "fund_open_fund_hist_em", fake_legacy, raising=False
    )
    result = fetcher.get_fund_nav(
        "013864",
        start_date="2024-01-01",
        end_date="2024-12-31",
    )

    assert len(result) == 1
    assert result.iloc[0]["nav"] == 1.02
