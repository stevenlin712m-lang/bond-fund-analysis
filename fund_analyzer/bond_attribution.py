"""
债券基金收益归因
================

用基金日收益对一组可解释的债券因子做多元线性回归。模块只依赖
pandas/numpy，既可以接真实指数数据，也可以使用用户准备的 CSV。

重要口径：
    - 回归结果是基于净值和代理指数的统计推断，不等同于基金真实持仓归因。
    - contribution_annual 是 beta × 因子年化平均收益，用于解释样本期内收益来源。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Iterable, Mapping, Optional

import numpy as np
import pandas as pd


DEFAULT_FACTOR_LABELS = {
    "rate": "利率债/久期",
    "credit": "信用利差",
    "convertible": "可转债/权益弹性",
    "liquidity": "资金面",
}


@dataclass(frozen=True)
class FactorResult:
    factor: str
    label: str
    beta: float
    contribution_annual: float
    correlation: float


@dataclass(frozen=True)
class AttributionResult:
    start_date: str
    end_date: str
    observations: int
    annualized_return_approx: float
    alpha_annual: float
    residual_annual: float
    r_squared: float
    factors: tuple[FactorResult, ...]
    methodology: str = "OLS：基金日收益 ~ 债券因子日收益；年化按252个交易日"

    def to_dict(self) -> dict:
        return asdict(self)


def _normalise_series(values: pd.Series, name: str) -> pd.Series:
    series = pd.to_numeric(values, errors="coerce").rename(name)
    if not isinstance(series.index, pd.DatetimeIndex):
        series.index = pd.to_datetime(series.index, errors="coerce")
    return series[~series.index.isna()].sort_index()


def returns_from_nav(nav: pd.Series) -> pd.Series:
    """把净值序列转成日收益率。"""
    clean = _normalise_series(nav, "fund")
    return clean.pct_change().replace([np.inf, -np.inf], np.nan).dropna()


def factor_returns_from_levels(levels: pd.DataFrame) -> pd.DataFrame:
    """把因子指数点位转换成日收益率。"""
    frame = levels.copy()
    if "date" in frame.columns:
        frame = frame.set_index("date")
    frame.index = pd.to_datetime(frame.index, errors="coerce")
    frame = frame[~frame.index.isna()].sort_index()
    numeric = frame.apply(pd.to_numeric, errors="coerce")
    return numeric.pct_change().replace([np.inf, -np.inf], np.nan).dropna(how="all")


def load_factor_csv(path: str, values_are_returns: bool = False) -> pd.DataFrame:
    """
    读取因子 CSV。第一列必须为 date，其余列为 rate/credit/convertible/liquidity
    等因子；默认将列值视为指数点位。
    """
    frame = pd.read_csv(path)
    if "date" not in frame.columns:
        raise ValueError("因子 CSV 必须包含 date 列")
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame = frame.dropna(subset=["date"]).set_index("date").sort_index()
    numeric = frame.apply(pd.to_numeric, errors="coerce")
    return numeric if values_are_returns else factor_returns_from_levels(numeric)


def attribute_returns(
    fund_returns: pd.Series,
    factor_returns: pd.DataFrame,
    *,
    factor_labels: Optional[Mapping[str, str]] = None,
    periods_per_year: int = 252,
    min_observations: int = 30,
) -> AttributionResult:
    """
    对基金日收益做多因子 OLS 归因。

    factor_returns 各列必须是收益率而非指数点位。函数会按日期取交集，
    自动剔除空值和零方差因子。
    """
    fund = _normalise_series(fund_returns, "fund")
    factors = factor_returns.copy()
    if not isinstance(factors.index, pd.DatetimeIndex):
        factors.index = pd.to_datetime(factors.index, errors="coerce")
    factors = factors[~factors.index.isna()].sort_index()
    factors = factors.apply(pd.to_numeric, errors="coerce")
    usable = [col for col in factors if factors[col].std(skipna=True) > 0]
    if not usable:
        raise ValueError("没有可用的非零方差因子")

    joined = pd.concat([fund, factors[usable]], axis=1, join="inner").dropna()
    if len(joined) < min_observations:
        raise ValueError(
            f"共同交易日只有 {len(joined)} 天，至少需要 {min_observations} 天"
        )

    y = joined["fund"].to_numpy(dtype=float)
    x = joined[usable].to_numpy(dtype=float)
    design = np.column_stack([np.ones(len(x)), x])
    coefficients, *_ = np.linalg.lstsq(design, y, rcond=None)
    fitted = design @ coefficients
    residuals = y - fitted
    ss_total = float(np.square(y - y.mean()).sum())
    ss_residual = float(np.square(residuals).sum())
    r_squared = 1.0 - ss_residual / ss_total if ss_total > 0 else np.nan

    labels: Dict[str, str] = dict(DEFAULT_FACTOR_LABELS)
    if factor_labels:
        labels.update(factor_labels)

    results = []
    for idx, name in enumerate(usable, start=1):
        beta = float(coefficients[idx])
        contribution = beta * float(joined[name].mean()) * periods_per_year
        corr = float(joined["fund"].corr(joined[name]))
        results.append(
            FactorResult(
                factor=name,
                label=labels.get(name, name),
                beta=beta,
                contribution_annual=contribution,
                correlation=corr,
            )
        )

    return AttributionResult(
        start_date=joined.index.min().strftime("%Y-%m-%d"),
        end_date=joined.index.max().strftime("%Y-%m-%d"),
        observations=len(joined),
        annualized_return_approx=float(joined["fund"].mean()) * periods_per_year,
        alpha_annual=float(coefficients[0]) * periods_per_year,
        residual_annual=float(residuals.mean()) * periods_per_year,
        r_squared=float(r_squared),
        factors=tuple(results),
    )


def dominant_exposures(
    result: AttributionResult, limit: int = 2
) -> Iterable[FactorResult]:
    """按贡献绝对值返回最主要的风险暴露。"""
    return sorted(
        result.factors,
        key=lambda item: abs(item.contribution_annual),
        reverse=True,
    )[:limit]
