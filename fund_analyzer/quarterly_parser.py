"""
基金定期报告 PDF 解析
====================

提取文本型基金季报/中报/年报中的关键事实。解析器采用“原文证据 + 结构化字段”
设计：每个数值尽可能保留命中的原句，方便人工复核。
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from pypdf import PdfReader


@dataclass(frozen=True)
class ExtractedValue:
    value: Optional[float]
    unit: str
    evidence: str


@dataclass
class QuarterlyReport:
    source_file: str
    pages: int
    report_period: str = ""
    fund_name: str = ""
    fund_code: str = ""
    manager_commentary: str = ""
    asset_allocation: Dict[str, ExtractedValue] = field(default_factory=dict)
    leverage_ratio: Optional[ExtractedValue] = None
    top_bond_holdings: List[dict] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


_SPACE_RE = re.compile(r"[ \t\u3000]+")


def extract_pdf_text(path: str) -> tuple[str, int]:
    """逐页提取 PDF 文本。扫描版无文本层时抛出可操作的错误。"""
    reader = PdfReader(path)
    pages = [(page.extract_text() or "") for page in reader.pages]
    text = "\n".join(pages)
    if len(re.sub(r"\s+", "", text)) < 80:
        raise ValueError(
            "PDF 几乎没有可提取文字，可能是扫描件；请先做 OCR 后再解析"
        )
    return text, len(reader.pages)


def _clean(text: str) -> str:
    text = text.replace("\r", "\n")
    text = _SPACE_RE.sub(" ", text)
    return re.sub(r"\n{3,}", "\n\n", text)


def _first(patterns: list[str], text: str, flags: int = 0) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags)
        if match:
            return match.group(1).strip()
    return ""


def _number_near(label: str, text: str) -> Optional[ExtractedValue]:
    pattern = rf"({label}.{{0,45}}?(-?\d+(?:\.\d+)?)\s*%)"
    match = re.search(pattern, text, re.S)
    if not match:
        return None
    return ExtractedValue(float(match.group(2)), "%", _clean(match.group(1)))


def _extract_manager_commentary(text: str) -> str:
    headings = [
        r"报告期内基金投资策略和运作分析",
        r"报告期内基金的投资策略和运作分析",
        r"报告期内基金的投资策略和业绩表现说明",
    ]
    end = r"(?:报告期内基金的业绩表现|管理人对宏观经济|投资组合报告|§\s*\d+)"
    for heading in headings:
        match = re.search(rf"{heading}\s*(.*?){end}", text, re.S)
        if match:
            content = _clean(match.group(1)).strip()
            content = re.sub(r"\s*\d+(?:\.\d+)+\s*$", "", content)
            return content[:4000]
    return ""


def _extract_top_bonds(text: str) -> List[dict]:
    section = re.search(
        r"(?:按公允价值占基金资产净值比例大小排序的前五名债券投资明细)"
        r"(.*?)(?:按公允价值占基金资产净值比例大小排序的前十名|投资组合报告附注|§\s*\d+)",
        text,
        re.S,
    )
    if not section:
        return []
    rows = []
    line_pattern = re.compile(
        r"(?ms)^\s*([1-5])\s+([A-Za-z0-9.\-]{4,20})\s+(.+?)\s+"
        r"([\d,]+(?:\.\d+)?)\s+([\d,]+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s*"
        r"(?=^\s*[1-5]\s+[A-Za-z0-9.\-]{4,20}\s|^\s*5\.6|\Z)"
    )
    for match in line_pattern.finditer(section.group(1)):
        rows.append(
            {
                "code": match.group(2),
                "name": re.sub(r"\s+", "", match.group(3)),
                "quantity": match.group(4),
                "market_value": match.group(5),
                "nav_ratio_pct": float(match.group(6)),
                "evidence": _clean(match.group(0)),
            }
        )
    return rows[:5]


def _extract_asset_allocation(text: str) -> Dict[str, ExtractedValue]:
    """从投资组合报告的资产组合表提取占基金总资产比例。"""
    match = re.search(
        r"5\.1\s*报告期末基金资产组合情况(.*?)(?:5\.2\s|报告期末按行业分类)",
        text,
        re.S,
    )
    if not match:
        return {}
    section = match.group(1)
    labels = {
        "bond": r"(?:固定收益投资|其中[：:]\s*债券)",
        "stock": r"(?:权益投资|其中[：:]\s*股票)",
        "fund": r"基金投资",
        "cash": r"银行存款和结算备付金合计",
    }
    result = {}
    for key, label in labels.items():
        row = re.search(
            rf"({label}\s+([\d,]+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s*)",
            section,
            re.S,
        )
        if row:
            result[key] = ExtractedValue(
                float(row.group(3)), "%", _clean(row.group(1))
            )
    return result


def parse_quarterly_report(path: str) -> QuarterlyReport:
    """解析一份基金定期报告 PDF，返回可序列化的结构化结果。"""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"找不到 PDF：{path}")
    text, pages = extract_pdf_text(str(source))
    text = _clean(text)
    result = QuarterlyReport(source_file=source.name, pages=pages)

    result.report_period = _first(
        [
            r"(20\d{2}\s*年\s*第\s*[一二三四1234]\s*季度报告)",
            r"(20\d{2}\s*年\s*(?:中期|年度)报告)",
        ],
        text,
    )
    result.report_period = re.sub(r"\s+", "", result.report_period)
    result.fund_code = _first(
        [r"基金(?:主)?代码[：:\s]+(\d{6})", r"基金代码[：:\s]+(\d{6})"], text
    )
    result.fund_name = _first(
        [r"基金名称[：:\s]+([^\n]{2,60})", r"\n([^\n]{2,50}基金)\s*\n20\d{2}年"],
        text,
    )
    result.manager_commentary = _extract_manager_commentary(text)

    result.asset_allocation = _extract_asset_allocation(text)
    if not result.asset_allocation:
        allocation_labels = {
            "bond": r"(?:债券投资|固定收益投资)",
            "stock": r"股票投资",
            "fund": r"基金投资",
            "cash": (
                r"(?:银行存款和结算备付金合计|"
                r"现金及到期日在一年以内的政府债券)"
            ),
        }
        for key, label in allocation_labels.items():
            value = _number_near(label, text)
            if value:
                result.asset_allocation[key] = value

    result.leverage_ratio = _number_near(r"基金资产总值[^\n]{0,25}基金资产净值", text)
    result.top_bond_holdings = _extract_top_bonds(text)

    if not result.report_period:
        result.warnings.append("未识别报告期")
    if not result.manager_commentary:
        result.warnings.append("未识别基金经理投资策略与运作分析")
    if not result.asset_allocation:
        result.warnings.append("未识别资产配置比例，请核对 PDF 表格文本层")
    if not result.top_bond_holdings:
        result.warnings.append("未识别前五大债券持仓，请核对 PDF 表格文本层")
    result.warnings.append("定期报告存在披露时滞；解析结果须结合原文复核")
    return result
