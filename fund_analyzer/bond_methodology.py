"""把债券基金研究框架转换为可复核的结构化评估。"""

from __future__ import annotations

from .quarterly_parser import QuarterlyReport


def _text(parsed: QuarterlyReport) -> str:
    return f"{parsed.fund_name} {parsed.manager_commentary}".lower()


def classify_fund(parsed: QuarterlyReport) -> tuple[str, str]:
    """根据名称、资产配置和经理原文做保守分类。"""
    text = _text(parsed)
    stock = parsed.asset_allocation.get("stock")
    stock_pct = stock.value if stock and stock.value is not None else 0
    if "可转债" in text or "转债" in parsed.fund_name:
        return "可转债/转债增强型", "名称或经理原文出现可转债线索"
    if stock_pct > 0:
        return "混合二级债基（待核对合同）", f"报告期末股票占比约 {stock_pct:.2f}%"
    if "短债" in text or "中短债" in text:
        return "短债/中短债基金", "名称或经理原文出现短债线索"
    if any(word in text for word in ("利率债", "国债", "政策性金融债")):
        return "利率债策略型（推断）", "经理原文出现利率债相关线索"
    if any(word in text for word in ("信用债", "信用利差", "信用挖掘")):
        return "信用债策略型（推断）", "经理原文出现信用策略线索"
    return "债券型基金（细分类待核对合同）", "现有披露不足以可靠细分"


def _earning_modes(parsed: QuarterlyReport) -> list[dict]:
    text = _text(parsed)
    modes = []
    rules = [
        ("票息/持有收益", ("票息", "持有到期", "静态收益", "套息")),
        ("骑乘收益", ("骑乘", "期限利差", "收益率曲线")),
        ("久期与利率交易", ("久期", "利率债", "波段", "利率下行")),
        ("信用利差与信用挖掘", ("信用利差", "信用债", "信用挖掘", "信用下沉")),
        ("杠杆套息", ("杠杆", "回购", "融资成本")),
        ("可转债/权益增强", ("可转债", "转债", "权益", "股票")),
    ]
    for label, keywords in rules:
        hits = [word for word in keywords if word in text]
        if hits:
            modes.append(
                {
                    "label": label,
                    "evidence": f"经理原文/基金名称出现：{'、'.join(hits)}",
                    "confidence": "线索",
                }
            )
    if not modes:
        modes.append(
            {
                "label": "票息与持有收益（待核对）",
                "evidence": "未从原文识别到明确策略关键词",
                "confidence": "低",
            }
        )
    return modes


def _risk_flags(parsed: QuarterlyReport, performance: dict | None) -> list[str]:
    text = _text(parsed)
    flags = []
    stock = parsed.asset_allocation.get("stock")
    if stock and stock.value and stock.value > 0:
        flags.append(f"权益风险：报告期末股票占比约 {stock.value:.2f}%")
    if "可转债" in text or "转债" in text:
        flags.append("转债风险：净值可能受正股及转债估值波动影响")
    if any(word in text for word in ("信用下沉", "低评级", "城投")):
        flags.append("信用风险：原文出现信用下沉、低评级或城投相关线索")
    if any(word in text for word in ("拉长久期", "长久期", "久期策略")):
        flags.append("久期风险：原文出现拉长久期或久期交易线索")
    if parsed.leverage_ratio and parsed.leverage_ratio.value:
        flags.append(
            f"杠杆线索：自动提取比例约 {parsed.leverage_ratio.value:.2f}%（须核对原表）"
        )
    if performance and performance.get("max_drawdown_pct") is not None:
        drawdown = abs(performance["max_drawdown_pct"])
        if drawdown >= 3:
            flags.append(f"历史回撤风险：全历史最大回撤约 {drawdown:.2f}%")
    if not flags:
        flags.append("自动提取未发现突出的额外风险线索，但不代表没有信用或流动性风险")
    return flags


def _score_rows(parsed: QuarterlyReport, performance: dict | None) -> list[dict]:
    """只给有依据的维度打分；其余显示待补数据。"""
    rows = []

    def add(dimension, weight, score, basis):
        rows.append(
            {"dimension": dimension, "weight": weight, "score": score, "basis": basis}
        )

    annual = performance.get("annual_returns", []) if performance else []
    complete = [x for x in annual if not x["is_partial"]]
    if complete:
        positive = sum(x["return_pct"] > 0 for x in complete) / len(complete)
        add("收益稳定性", 15, round(6 + positive * 9, 1), f"完整年度正收益率 {positive:.0%}")
    else:
        add("收益稳定性", 15, None, "缺少完整自然年度净值")

    max_dd = abs(performance.get("max_drawdown_pct", 0)) if performance else None
    if max_dd is not None:
        score = 15 if max_dd <= 0.5 else 12 if max_dd <= 1 else 9 if max_dd <= 2 else 5
        add("最大回撤", 15, score, f"全历史最大回撤 {max_dd:.2f}%")
    else:
        add("最大回撤", 15, None, "缺少净值数据")

    calmar = performance.get("calmar_ratio") if performance else None
    if calmar is not None:
        score = 10 if calmar >= 3 else 8 if calmar >= 2 else 6 if calmar >= 1 else 3
        add("修复能力", 10, score, f"以卡尔玛比率 {calmar:.2f} 作为修复效率代理")
    else:
        add("修复能力", 10, None, "尚未计算精确回撤修复天数")

    sharpe = performance.get("sharpe_ratio") if performance else None
    if sharpe is not None:
        score = 10 if sharpe >= 2 else 8 if sharpe >= 1 else 5 if sharpe >= 0 else 2
        add("风险收益比", 10, score, f"夏普比率 {sharpe:.2f}")
    else:
        add("风险收益比", 10, None, "缺少可用夏普比率")

    add("持仓质量", 15, None, "需补发行人、评级、期限和流动性穿透")
    add("策略适配度", 15, None, "需结合实时久期、曲线、信用利差和资金面")
    add("基金经理", 10, None, "需补任职年限、周期业绩及一拖多情况")
    add("基金公司", 5, None, "需补信评团队、风控和历史信用事件")
    add("规模和持有人结构", 5, None, "需补规模、份额变化及机构持有人占比")
    return rows


def evaluate_bond_fund(
    parsed: QuarterlyReport, performance: dict | None = None
) -> dict:
    """生成专业版与客户版共用的方法论评估结果。"""
    fund_type, type_basis = classify_fund(parsed)
    score_rows = _score_rows(parsed, performance)
    assessed = [row for row in score_rows if row["score"] is not None]
    return {
        "fund_type": fund_type,
        "type_basis": type_basis,
        "earning_modes": _earning_modes(parsed),
        "risk_flags": _risk_flags(parsed, performance),
        "score_rows": score_rows,
        "assessed_score": round(sum(row["score"] for row in assessed), 1),
        "assessed_weight": sum(row["weight"] for row in assessed),
        "future_framework": [
            "利率：经济增长、通胀、货币政策、债券供给及预期定价程度",
            "曲线：短中长端形态，以及拉长久期获得的期限补偿",
            "信用：信用利差所处分位、发行人偿债能力与流动性",
            "资金：回购利率、同业存单利率及杠杆收益能否覆盖融资成本",
            "权益：股票与可转债仓位、转股溢价率及风险偏好",
        ],
        "missing_data": [
            "实时及历史久期",
            "杠杆率历史序列",
            "信用评级、发行人和区域穿透",
            "同类基金排名与基准超额",
            "精确回撤修复天数",
            "基金经理任职年限、管理总规模与一拖多",
            "机构持有人比例和份额变化",
            "当前利率曲线、信用利差与资金利率",
        ],
    }
