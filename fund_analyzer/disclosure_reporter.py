"""仅基于基金定期报告披露事实生成专业版和客户版 Markdown。"""

from __future__ import annotations

from datetime import datetime

from .quarterly_parser import QuarterlyReport
from .report_downloader import ReportRecord


def _identity(record: ReportRecord, parsed: QuarterlyReport) -> tuple[str, str]:
    return (
        parsed.fund_name or record.fund_name or record.fund_code,
        parsed.fund_code or record.fund_code,
    )


def generate_professional(
    record: ReportRecord, parsed: QuarterlyReport
) -> str:
    """生成带原文证据、数据口径和局限性的专业版。"""
    name, code = _identity(record, parsed)
    lines = [
        f"# 基金定期报告专业分析：{name}（{code}）",
        "",
        f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"> 公告：{record.title}",
        f"> 公告日期：{record.published_date.isoformat()}",
        f"> 报告期：{parsed.report_period or '未识别'}",
        f"> 原始文件：{parsed.source_file}",
        f"> 公告详情：{record.detail_url}",
        "",
        "## 一、已披露资产配置",
        "",
    ]
    if parsed.asset_allocation:
        labels = {"bond": "债券", "stock": "股票", "fund": "基金", "cash": "现金类"}
        lines += ["| 资产类别 | 占比 | 原文证据 |", "|---|---:|---|"]
        for key, item in parsed.asset_allocation.items():
            lines.append(
                f"| {labels.get(key, key)} | {item.value:.2f}{item.unit} | "
                f"{item.evidence} |"
            )
    else:
        lines.append("> PDF 文本层未提取到可靠的资产配置比例，需查看原文表格。")
    lines += ["", "## 二、前五大债券持仓", ""]
    if parsed.top_bond_holdings:
        lines += ["| 债券名称 | 代码 | 占基金净值 |", "|---|---|---:|"]
        for item in parsed.top_bond_holdings:
            lines.append(
                f"| {item['name']} | {item['code']} | "
                f"{item['nav_ratio_pct']:.2f}% |"
            )
    else:
        lines.append("> PDF 文本层未提取到可靠的前五大债券持仓，需查看原文表格。")
    lines += ["", "## 三、基金经理运作分析（原文提取）", ""]
    lines.append(parsed.manager_commentary or "> 未识别到该章节，请查阅原文。")
    lines += [
        "",
        "## 四、研究解读",
        "",
        "- 本报告中的配置比例和持仓属于公告日已披露事实，不等于当前实时持仓。",
        "- 经理观点用于识别久期、信用、杠杆或转债策略线索；若无明确原文，不作确定性归因。",
        "- 判断未来表现仍需叠加净值因子归因、利率曲线、信用利差和资金面数据。",
        "",
        "## 五、解析提示与风险",
        "",
    ]
    lines += [f"- {warning}" for warning in parsed.warnings]
    lines += [
        "- 自动提取可能受 PDF 表格结构影响，正式投研或对客前必须核对公告原文。",
        "- 本材料仅用于研究辅助，不构成投资建议；过往业绩不代表未来表现。",
        "",
    ]
    return "\n".join(lines)


def generate_client(record: ReportRecord, parsed: QuarterlyReport) -> str:
    """生成不承诺收益、避免过度推断的客户通俗版。"""
    name, code = _identity(record, parsed)
    bond = parsed.asset_allocation.get("bond")
    stock = parsed.asset_allocation.get("stock")
    allocation_text = (
        f"报告中提取的债券投资比例约为 {bond.value:.2f}%"
        if bond and bond.value is not None
        else "自动解析未能可靠读取债券投资比例"
    )
    if stock and stock.value is not None:
        allocation_text += f"，股票投资比例约为 {stock.value:.2f}%"
    lines = [
        f"# 客户沟通版：{name}（{code}）",
        "",
        "## 这份报告告诉了我们什么",
        "",
        f"根据 {record.published_date.isoformat()} 公告的《{record.title}》，"
        f"{allocation_text}。这些数字反映的是报告期末状态，不代表今天的实时持仓。",
        "",
        "## 基金经理做了什么",
        "",
        parsed.manager_commentary[:1200]
        if parsed.manager_commentary
        else "PDF 中没有自动识别到清晰的基金经理运作分析，建议直接查看公告原文。",
        "",
        "## 需要注意什么",
        "",
        "- 债券价格会受市场利率变化影响；久期越长，通常波动越明显。",
        "- 信用债可能受发行人资质和信用利差变化影响。",
        "- 若持有股票或可转债，净值还会受到权益市场波动影响。",
        "- 定期报告存在披露时滞，基金经理可能已在报告期后调仓。",
        "",
        "## 沟通边界",
        "",
        "这份材料是对公开报告的辅助解读，不承诺收益，也不能替代客户风险测评、"
        "产品说明书和基金公告原文。",
        "",
    ]
    return "\n".join(lines)
