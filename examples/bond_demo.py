"""离线演示：构造可重复的净值和债券因子，生成两种 Markdown 报告。"""

from pathlib import Path
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fund_analyzer import bond_attribution, bond_reporter


def main() -> None:
    rng = np.random.default_rng(2026)
    dates = pd.bdate_range("2025-01-02", periods=180)
    factors = pd.DataFrame(
        {
            "rate": rng.normal(0.00008, 0.0012, len(dates)),
            "credit": rng.normal(0.00006, 0.0006, len(dates)),
            "convertible": rng.normal(0.00012, 0.006, len(dates)),
            "liquidity": rng.normal(0.00001, 0.0003, len(dates)),
        },
        index=dates,
    )
    noise = rng.normal(0, 0.00025, len(dates))
    fund_returns = (
        0.000015
        + 0.65 * factors["rate"]
        + 0.45 * factors["credit"]
        + 0.08 * factors["convertible"]
        - 0.15 * factors["liquidity"]
        + noise
    )
    attribution = bond_attribution.attribute_returns(fund_returns, factors)

    output = Path("data/reports")
    output.mkdir(parents=True, exist_ok=True)
    professional = bond_reporter.generate_professional_report(
        fund_code="DEMO01",
        fund_name="债基归因离线示例",
        attribution=attribution,
    )
    client = bond_reporter.generate_client_report(
        fund_code="DEMO01",
        fund_name="债基归因离线示例",
        attribution=attribution,
    )
    (output / "DEMO01_professional.md").write_text(professional, encoding="utf-8")
    (output / "DEMO01_client.md").write_text(client, encoding="utf-8")
    print("已生成 data/reports/DEMO01_professional.md")
    print("已生成 data/reports/DEMO01_client.md")


if __name__ == "__main__":
    main()
