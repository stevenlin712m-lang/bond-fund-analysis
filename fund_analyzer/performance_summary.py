"""基金全历史净值指标与逐年度收益率。"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from . import analyzer


def _prepare_nav(nav_df: pd.DataFrame) -> pd.Series:
    if nav_df.empty or "date" not in nav_df.columns:
        raise ValueError("净值数据为空或缺少 date 字段")
    value_column = (
        "acc_nav"
        if "acc_nav" in nav_df.columns and nav_df["acc_nav"].notna().sum() >= 2
        else "nav"
    )
    if value_column not in nav_df.columns:
        raise ValueError("净值数据缺少 nav/acc_nav 字段")
    frame = nav_df[["date", value_column]].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame[value_column] = pd.to_numeric(frame[value_column], errors="coerce")
    frame = frame.dropna().sort_values("date").drop_duplicates("date", keep="last")
    if len(frame) < 2:
        raise ValueError("有效净值数据不足，无法计算指标")
    return frame.set_index("date")[value_column].rename("nav")


def calculate_annual_returns(nav_df: pd.DataFrame) -> list[dict]:
    """计算成立以来每个自然年度收益，首年和当年标记为非完整年度。"""
    nav = _prepare_nav(nav_df)
    years = sorted(nav.index.year.unique())
    current_year = date.today().year
    rows = []
    prior_close = None
    for year in years:
        values = nav[nav.index.year == year]
        if values.empty:
            continue
        start_value = prior_close if prior_close is not None else values.iloc[0]
        end_value = values.iloc[-1]
        annual_return = float(end_value / start_value - 1)
        rows.append(
            {
                "year": int(year),
                "return": annual_return,
                "return_pct": annual_return * 100,
                "start_date": values.index[0].strftime("%Y-%m-%d"),
                "end_date": values.index[-1].strftime("%Y-%m-%d"),
                "observations": int(len(values)),
                "is_partial": bool(year == years[0] or year == current_year),
            }
        )
        prior_close = end_value
    return rows


def calculate_performance_summary(nav_df: pd.DataFrame) -> dict:
    """用全部可得历史净值生成统一指标口径。"""
    nav = _prepare_nav(nav_df)
    returns = nav.pct_change().dropna()
    maximum_drawdown = analyzer.max_drawdown(nav)

    def finite(value, digits=4):
        return round(float(value), digits) if np.isfinite(value) else None

    metrics = {
        "analysis_start": nav.index[0].strftime("%Y-%m-%d"),
        "analysis_end": nav.index[-1].strftime("%Y-%m-%d"),
        "observations": int(len(nav)),
        "annualized_return_pct": finite(analyzer.annualized_return(nav) * 100, 2),
        "annualized_volatility_pct": finite(
            analyzer.annualized_volatility(returns) * 100, 2
        ),
        "max_drawdown_pct": finite(maximum_drawdown * 100, 2),
        "win_rate_pct": finite(analyzer.win_rate(returns) * 100, 2),
        "profit_factor": finite(analyzer.profit_factor(returns), 2),
        "sharpe_ratio": finite(analyzer.sharpe_ratio(returns), 4),
        "sortino_ratio": finite(analyzer.sortino_ratio(returns), 4),
        "calmar_ratio": finite(
            analyzer.calmar_ratio(returns, maximum_drawdown), 4
        ),
        "var_95_pct": finite(analyzer.var_historical(returns) * 100, 2),
        "cvar_95_pct": finite(analyzer.conditional_var(returns) * 100, 2),
        "max_consecutive_loss_days": analyzer.consecutive_losses(returns),
    }
    metrics["annual_returns"] = calculate_annual_returns(nav_df)
    return metrics
