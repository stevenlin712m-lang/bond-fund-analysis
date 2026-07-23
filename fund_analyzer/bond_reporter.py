"""债券基金专业版与客户通俗版 Markdown 报告。"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from .bond_attribution import AttributionResult, dominant_exposures
from .quarterly_parser import QuarterlyReport


def _pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def _disclosure_section(report: Optional[QuarterlyReport]) -> list[str]:
    if report is None:
        return ["## 定期报告信息", "", "> 未提供季报 PDF，本节不作推断。", ""]
    lines = [
        "## 定期报告信息",
        "",
        f"- 文件：{report.source_file}",
        f"- 报告期：{report.report_period or '未识别'}",
        f"- 基金：{report.fund_name or '未识别'}（{report.fund_code or '代码未识别'}）",
        "",
    ]
    if report.asset_allocation:
        labels = {"bond": "债券", "stock": "股票", "fund": "基金", "cash": "现金类"}
        lines += ["| 资产 | 占比 | 原文证据 |", "|---|---:|---|"]
        for key, item in report.asset_allocation.items():
            lines.append(f"| {labels.get(key, key)} | {item.value:.2f}% | {item.evidence} |")
        lines.append("")
    if report.manager_commentary:
        lines += ["### 基金经理观点（原文提取）", "", report.manager_commentary, ""]
    if report.top_bond_holdings:
        lines += ["### 前五大债券持仓", "", "| 债券 | 代码 | 占净值 |", "|---|---|---:|"]
        for item in report.top_bond_holdings:
            lines.append(
                f"| {item['name']} | {item['code']} | {item['nav_ratio_pct']:.2f}% |"
            )
        lines.append("")
    if report.warnings:
        lines += ["### 解析提示", ""] + [f"- {item}" for item in report.warnings] + [""]
    return lines


def generate_professional_report(
    *,
    fund_code: str,
    fund_name: str,
    attribution: AttributionResult,
    quarterly_report: Optional[QuarterlyReport] = None,
) -> str:
    """生成保留方法、系数、证据和局限性的专业版报告。"""
    lines = [
        f"# 债券基金专业分析：{fund_name}（{fund_code}）",
        "",
        f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"> 归因区间：{attribution.start_date} 至 {attribution.end_date}",
        "",
        "## 净值因子归因",
        "",
        f"- 样本数：{attribution.observations} 个共同交易日",
        f"- 样本年化收益（算术近似）：{_pct(attribution.annualized_return_approx)}",
        f"- 年化 Alpha：{_pct(attribution.alpha_annual)}",
        f"- 拟合优度 R²：{attribution.r_squared:.3f}",
        "",
        "| 因子 | Beta | 年化贡献估计 | 相关系数 |",
        "|---|---:|---:|---:|",
    ]
    for item in attribution.factors:
        lines.append(
            f"| {item.label} | {item.beta:.3f} | {_pct(item.contribution_annual)} | "
            f"{item.correlation:.3f} |"
        )
    lines += [
        "",
        f"> 方法：{attribution.methodology}",
        "> 归因是基于净值与代理指数的统计估计，不代表管理人披露的真实持仓贡献。",
        "",
    ]
    lines += _disclosure_section(quarterly_report)
    lines += [
        "## 结论与风险",
        "",
        "- 将净值归因与最新定期报告交叉验证；若二者冲突，以已披露事实为准，并标记披露时滞。",
        "- 重点观察利率方向、信用利差、资金成本和可转债估值变化。",
        "- 本报告仅用于研究辅助，不构成投资建议；过往业绩不代表未来表现。",
        "",
    ]
    return "\n".join(lines)


def generate_client_report(
    *,
    fund_code: str,
    fund_name: str,
    attribution: AttributionResult,
    quarterly_report: Optional[QuarterlyReport] = None,
) -> str:
    """生成避免术语堆叠、明确场景和风险的客户通俗版报告。"""
    dominant = list(dominant_exposures(attribution))
    source_text = "、".join(item.label for item in dominant) or "票息与主动管理"
    volatility_hint = (
        "净值可能对市场利率变化较敏感"
        if any(item.factor == "rate" and abs(item.beta) >= 0.5 for item in dominant)
        else "净值对单一利率因子的敏感度暂未显示为特别突出"
    )
    disclosed = ""
    if quarterly_report and quarterly_report.asset_allocation.get("bond"):
        bond = quarterly_report.asset_allocation["bond"]
        disclosed = f"最新报告提取的债券占比约为 {bond.value:.2f}%（请以季报原文为准）。"

    lines = [
        f"# 客户沟通版：{fund_name}（{fund_code}）",
        "",
        "## 一句话认识",
        "",
        f"从历史净值与参考指数的关系看，这只基金的主要波动来源更接近：{source_text}。"
        f"{volatility_hint}。",
        "",
        "## 它可能靠什么赚钱",
        "",
    ]
    for item in dominant:
        direction = "正向" if item.contribution_annual >= 0 else "负向"
        lines.append(
            f"- **{item.label}**：样本期贡献估计为{direction}，约 "
            f"{abs(item.contribution_annual) * 100:.2f}%/年；这是统计推断，不是持仓承诺。"
        )
    if disclosed:
        lines += ["", disclosed]
    lines += [
        "",
        "## 什么环境下可能更有利",
        "",
        "- 市场利率平稳或下行、信用风险可控、资金面不过度收紧时，债券资产通常更容易积累票息或获得价格收益。",
        "- 若基金含可转债，权益市场回暖可能提供弹性，但也会增加净值波动。",
        "",
        "## 需要接受什么风险",
        "",
        "- 利率快速上升时，较长久期债券可能出现阶段性回撤。",
        "- 信用利差扩大或个券信用恶化时，信用债价格可能承压。",
        "- 基金定期报告有披露时滞，当前持仓可能已经变化。",
        "",
        "## 沟通边界",
        "",
        "这是一份基于公开数据的研究辅助材料，不承诺收益，也不替代适当性评估。"
        "购买前仍需结合客户的回撤承受能力、资金期限和流动性需求。",
        "",
    ]
    return "\n".join(lines)
