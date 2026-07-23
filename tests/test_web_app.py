import web_app


def test_home_page_contains_analysis_form():
    page = web_app._page("", code="013864", selected="annual")
    assert "债券基金分析台" in page
    assert 'value="013864"' in page
    assert 'value="annual" selected' in page
    assert 'action="/analyze"' in page


def test_report_labels_cover_supported_types():
    assert set(web_app.REPORT_LABELS) == {"quarter", "semiannual", "annual"}
