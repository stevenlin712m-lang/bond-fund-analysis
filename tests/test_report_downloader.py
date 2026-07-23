from datetime import date

import pandas as pd

from fund_analyzer import report_downloader


def _announcements(_code):
    return pd.DataFrame(
        [
            {
                "基金代码": "000001",
                "公告标题": "示例基金2025年第4季度报告",
                "基金名称": "示例基金",
                "公告日期": "2026-01-20",
                "报告ID": "AN202601200001",
            },
            {
                "基金代码": "000001",
                "公告标题": "示例基金2025年年度报告摘要",
                "基金名称": "示例基金",
                "公告日期": "2026-03-30",
                "报告ID": "AN202603300002",
            },
            {
                "基金代码": "000001",
                "公告标题": "示例基金2025年年度报告",
                "基金名称": "示例基金",
                "公告日期": "2026-03-30",
                "报告ID": "AN202603300001",
            },
            {
                "基金代码": "000001",
                "公告标题": "示例基金2025年半年度报告",
                "基金名称": "示例基金",
                "公告日期": "2025-08-30",
                "报告ID": "AN202508300001",
            },
        ]
    )


class _Response:
    content = b"%PDF-1.7\n" + b"x" * 200

    def raise_for_status(self):
        return None


class _Session:
    def __init__(self):
        self.headers = {}
        self.urls = []

    def get(self, url, timeout):
        self.urls.append((url, timeout))
        return _Response()


def test_list_reports_classifies_and_excludes_summary():
    records = report_downloader.list_reports(
        "000001", "all", announcement_fetcher=_announcements
    )
    assert [item.report_type for item in records] == [
        "annual",
        "quarter",
        "semiannual",
    ]
    assert records[0].report_id == "AN202603300001"
    assert records[0].published_date == date(2026, 3, 30)


def test_list_reports_filters_type_and_can_include_summary():
    records = report_downloader.list_reports(
        "000001",
        "annual",
        include_summary=True,
        announcement_fetcher=_announcements,
    )
    assert len(records) == 2
    assert any(item.is_summary for item in records)


def test_download_report_writes_pdf_and_metadata(tmp_path):
    record = report_downloader.list_reports(
        "000001", "quarter", announcement_fetcher=_announcements
    )[0]
    session = _Session()
    path = report_downloader.download_report(
        record, tmp_path, session=session
    )
    assert path.read_bytes().startswith(b"%PDF-")
    assert path.with_suffix(".json").is_file()
    assert "H2_AN202601200001_1.pdf" in session.urls[0][0]


def test_download_latest_uses_first_matching_report(tmp_path):
    record, path = report_downloader.download_latest_report(
        "000001",
        "annual",
        output_dir=tmp_path,
        announcement_fetcher=_announcements,
        session=_Session(),
    )
    assert record.report_id == "AN202603300001"
    assert path.is_file()
