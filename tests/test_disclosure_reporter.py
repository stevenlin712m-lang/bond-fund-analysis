from datetime import date

from fund_analyzer import disclosure_reporter
from fund_analyzer.quarterly_parser import ExtractedValue, QuarterlyReport
from fund_analyzer.report_downloader import ReportRecord


def test_disclosure_reports_distinguish_professional_and_client():
    record = ReportRecord(
        fund_code="000001",
        fund_name="示例债券基金",
        title="示例债券基金2025年第4季度报告",
        published_date=date(2026, 1, 20),
        report_id="AN202601200001",
        report_type="quarter",
    )
    parsed = QuarterlyReport(
        source_file="sample.pdf",
        pages=12,
        report_period="2025年第4季度报告",
        fund_name="示例债券基金",
        fund_code="000001",
        manager_commentary="报告期内保持中短久期并重视信用风险。",
        asset_allocation={
            "bond": ExtractedValue(112.34, "%", "债券投资占比112.34%")
        },
        warnings=["定期报告存在披露时滞"],
    )
    professional = disclosure_reporter.generate_professional(record, parsed)
    client = disclosure_reporter.generate_client(record, parsed)
    assert "原文证据" in professional
    assert "公告详情" in professional
    assert "不代表今天的实时持仓" in client
    assert professional != client
