from fund_analyzer import quarterly_parser


SAMPLE_TEXT = """
稳健纯债证券投资基金
2025年第4季度报告
基金名称：稳健纯债证券投资基金
基金代码：000001
报告期内基金投资策略和运作分析
报告期内组合维持中性久期，以高等级信用债获取票息，并控制杠杆。
报告期内基金的业绩表现
本报告期净值增长率为1.20%。
债券投资 98.50%
股票投资 0.00%
银行存款和结算备付金合计 1.20%
按公允价值占基金资产净值比例大小排序的前五名债券投资明细
1 240001 24国债01 100,000 10,100,000 10.10
投资组合报告附注
"""


def test_parse_quarterly_report(monkeypatch, tmp_path):
    pdf = tmp_path / "quarter.pdf"
    pdf.write_bytes(b"%PDF-placeholder")
    monkeypatch.setattr(
        quarterly_parser, "extract_pdf_text", lambda path: (SAMPLE_TEXT, 12)
    )

    result = quarterly_parser.parse_quarterly_report(str(pdf))

    assert result.report_period == "2025年第4季度报告"
    assert result.fund_code == "000001"
    assert result.asset_allocation["bond"].value == 98.5
    assert "中性久期" in result.manager_commentary
    assert result.top_bond_holdings[0]["name"] == "24国债01"
