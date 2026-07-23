"""
FundAnalyzer — 公募基金智能分析工具包
====================================
基于公开数据的公募基金全维度分析工具。
覆盖业绩归因、风险评估、持仓分析、组合优化。

模块:
    fetcher  — 数据获取 (基于 akshare)
    analyzer — 业绩指标与风险分析
    portfolio — 投资组合优化
    reporter — 报告生成
"""

from importlib import import_module

__version__ = "1.1.0"
__author__ = "FundAnalyzer"
__all__ = [
    "fetcher",
    "analyzer",
    "portfolio",
    "reporter",
    "bond_attribution",
    "quarterly_parser",
    "bond_reporter",
]


def __getattr__(name):
    """按需加载子模块，离线归因/PDF 解析不被 AKShare 的联网依赖阻塞。"""
    if name in __all__:
        module = import_module(f".{name}", __name__)
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
