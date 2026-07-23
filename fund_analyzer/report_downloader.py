"""从天天基金公开公告列表发现并下载基金定期报告。"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Iterable, Optional

import requests


REPORT_TYPES = ("all", "quarter", "semiannual", "annual")
_PDF_URLS = (
    "https://pdf.dfcfw.com/pdf/H2_{report_id}_1.pdf",
    "https://pdf.dfcfw.com/pdf/H3_{report_id}_1.pdf",
)
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
    ),
    "Referer": "https://fundf10.eastmoney.com/",
}


@dataclass(frozen=True)
class ReportRecord:
    fund_code: str
    fund_name: str
    title: str
    published_date: date
    report_id: str
    report_type: str
    is_summary: bool = False

    @property
    def detail_url(self) -> str:
        return f"https://fundf10.eastmoney.com/jjgg_{self.fund_code}_3.html"

    @property
    def pdf_url(self) -> str:
        return _PDF_URLS[0].format(report_id=self.report_id)


def classify_report(title: str) -> Optional[str]:
    """把公告标题归为季报、半年报或年报；其他公告返回 None。"""
    normalized = re.sub(r"\s+", "", str(title))
    if "季度报告" in normalized:
        return "quarter"
    if "半年度报告" in normalized or "中期报告" in normalized:
        return "semiannual"
    if "年度报告" in normalized:
        return "annual"
    return None


def _default_announcement_fetcher(fund_code: str):
    import akshare as ak

    return ak.fund_announcement_report_em(symbol=fund_code)


def list_reports(
    fund_code: str,
    report_type: str = "all",
    *,
    years: Optional[int] = None,
    include_summary: bool = False,
    announcement_fetcher: Optional[Callable] = None,
) -> list[ReportRecord]:
    """查询定期报告并按公告日期从新到旧返回。"""
    if not re.fullmatch(r"\d{6}", fund_code):
        raise ValueError("基金代码必须是 6 位数字")
    if report_type not in REPORT_TYPES:
        raise ValueError(f"report_type 应为：{', '.join(REPORT_TYPES)}")
    if years is not None and years < 1:
        raise ValueError("years 必须大于等于 1")

    fetch = announcement_fetcher or _default_announcement_fetcher
    try:
        frame = fetch(fund_code)
    except Exception as exc:
        raise RuntimeError(
            "无法连接天天基金公告接口，请检查网络后重试；"
            "该公开接口也可能因网页调整而暂时不可用"
        ) from exc

    required = {"基金代码", "公告标题", "基金名称", "公告日期", "报告ID"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"公告数据缺少字段：{', '.join(sorted(missing))}")

    earliest_year = date.today().year - years + 1 if years else None
    records: list[ReportRecord] = []
    for row in frame.to_dict("records"):
        kind = classify_report(row["公告标题"])
        if kind is None or (report_type != "all" and kind != report_type):
            continue
        is_summary = "摘要" in str(row["公告标题"])
        if is_summary and not include_summary:
            continue
        published = row["公告日期"]
        if hasattr(published, "date") and not isinstance(published, date):
            published = published.date()
        if not isinstance(published, date):
            published = datetime.fromisoformat(str(published)[:10]).date()
        if earliest_year and published.year < earliest_year:
            continue
        records.append(
            ReportRecord(
                fund_code=str(row["基金代码"]).zfill(6),
                fund_name=str(row["基金名称"]),
                title=str(row["公告标题"]),
                published_date=published,
                report_id=str(row["报告ID"]),
                report_type=kind,
                is_summary=is_summary,
            )
        )
    return sorted(records, key=lambda item: item.published_date, reverse=True)


def _safe_filename(text: str, max_length: int = 90) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|\s]+', "_", text).strip("._")
    return cleaned[:max_length] or "fund_report"


def _valid_pdf(content: bytes) -> bool:
    return b"%PDF-" in content[:1024] and len(content) >= 100


def download_report(
    report: ReportRecord,
    output_dir: str | Path = "data/source_reports",
    *,
    force: bool = False,
    session: Optional[requests.Session] = None,
    timeout: int = 30,
    url_templates: Iterable[str] = _PDF_URLS,
) -> Path:
    """下载单份报告，校验 PDF 并保存可追溯元数据。"""
    target_dir = Path(output_dir) / report.fund_code
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = (
        f"{report.published_date.isoformat()}_{report.report_id}_"
        f"{_safe_filename(report.title)}.pdf"
    )
    target = target_dir / filename
    if target.exists() and not force and _valid_pdf(target.read_bytes()):
        return target

    client = session or requests.Session()
    client.headers.update(_HEADERS)
    errors = []
    for template in url_templates:
        url = template.format(report_id=report.report_id)
        try:
            response = client.get(url, timeout=timeout)
            response.raise_for_status()
            content = response.content
        except requests.RequestException as exc:
            errors.append(f"{url}: {exc}")
            continue
        if not _valid_pdf(content):
            errors.append(f"{url}: 返回内容不是有效 PDF")
            continue

        target.write_bytes(content)
        metadata = asdict(report)
        metadata["published_date"] = report.published_date.isoformat()
        metadata.update(
            {
                "source_url": url,
                "detail_url": report.detail_url,
                "downloaded_at": datetime.now().astimezone().isoformat(),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
        target.with_suffix(".json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return target
    raise RuntimeError("报告下载失败；" + "；".join(errors))


def download_latest_report(
    fund_code: str,
    report_type: str = "quarter",
    *,
    output_dir: str | Path = "data/source_reports",
    force: bool = False,
    announcement_fetcher: Optional[Callable] = None,
    session: Optional[requests.Session] = None,
) -> tuple[ReportRecord, Path]:
    """查询并下载指定类型的最新完整报告。"""
    records = list_reports(
        fund_code,
        report_type,
        include_summary=False,
        announcement_fetcher=announcement_fetcher,
    )
    if not records:
        raise LookupError(f"没有找到基金 {fund_code} 的{report_type}报告")
    record = records[0]
    return record, download_report(
        record, output_dir, force=force, session=session
    )
