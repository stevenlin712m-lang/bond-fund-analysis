import web_app


def test_home_page_contains_analysis_form():
    page = web_app._page("", code="013864", selected="annual")
    assert "债券基金分析台" in page
    assert 'value="013864"' in page
    assert 'value="annual" selected' in page
    assert 'action="/analyze"' in page


def test_report_labels_cover_supported_types():
    assert set(web_app.REPORT_LABELS) == {"quarter", "semiannual", "annual"}


def test_annual_returns_table_shows_fixed_years():
    table = web_app._annual_returns_table(
        {
            "annual_returns": [
                {
                    "year": 2023,
                    "return_pct": 3.21,
                    "is_partial": False,
                    "start_date": "2023-01-03",
                    "end_date": "2023-12-29",
                },
                {
                    "year": 2024,
                    "return_pct": -1.23,
                    "is_partial": False,
                    "start_date": "2024-01-02",
                    "end_date": "2024-12-31",
                },
            ]
        }
    )
    assert "2024年" in table
    assert "-1.23%" in table
    assert "2023年" in table
    assert "3.21%" in table
