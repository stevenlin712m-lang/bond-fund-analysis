#!/usr/bin/env python3
"""
FundAnalyzer CLI — 公募基金智能分析命令行工具
=============================================
用法:
    python fund_cli.py search <keyword>         搜索基金
    python fund_cli.py info <code>              基金基本信息
    python fund_cli.py analyze <code>           全面分析
    python fund_cli.py compare <code1> <code2>  对比两只基金
    python fund_cli.py optimize <c1> <c2> <c3>  组合优化 (3只)
    python fund_cli.py report <code>            生成 Markdown 报告
    python fund_cli.py export <code>            导出净值 CSV
    python fund_cli.py quarter <pdf>            解析基金定期报告
    python fund_cli.py reports <code>           查询可下载的定期报告
    python fund_cli.py download-report <code>   下载最新定期报告
    python fund_cli.py auto-report <code>       自动下载、解析并生成双版本
    python fund_cli.py bond-report <code>       生成债基专业版与客户版
    python fund_cli.py clearcache               清空缓存
"""

import argparse
import sys
import os

# 确保能找到 fund_analyzer 包
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fund_analyzer import (
    analyzer,
    bond_attribution,
    bond_reporter,
    disclosure_reporter,
    fetcher,
    portfolio,
    performance_summary,
    quarterly_parser,
    report_downloader,
    reporter,
)


def cmd_search(args):
    """搜索基金."""
    results = fetcher.search_fund(args.keyword)
    if not results:
        print(f"未找到匹配 '{args.keyword}' 的基金。")
        return

    print(f"\n找到 {len(results)} 只基金 (前 {min(20, len(results))} 条):\n")
    print(f"{'代码':<8} {'名称':<30} {'类型':<12} {'净值':<10} {'日涨跌':<10}")
    print("-" * 70)
    for r in results[:20]:
        code = r.get("code", r.get("基金代码", ""))
        name = r.get("name", r.get("基金简称", ""))[:28]
        ftype = r.get("type", r.get("基金类型", ""))[:10]
        nav = r.get("nav", r.get("单位净值", ""))
        dret = r.get("daily_return", r.get("日增长率", ""))
        print(f"{code:<8} {name:<30} {ftype:<12} {str(nav):<10} {str(dret):<10}")


def cmd_info(args):
    """显示基金基本信息."""
    info = fetcher.get_fund_info(args.code)
    if not info or not info.get("name"):
        print(f"无法获取基金 {args.code} 的信息。")
        return

    print(f"\n{'='*50}")
    print(f"  基金代码: {info.get('code', args.code)}")
    print(f"  基金名称: {info.get('name', 'N/A')}")
    print(f"  基金类型: {info.get('type', 'N/A')}")
    print(f"  管理人: {info.get('manager_company', 'N/A')}")
    print(f"  托管人: {info.get('custodian', 'N/A')}")
    print(f"  成立日期: {info.get('inception_date', 'N/A')}")
    print(f"  最新规模: {info.get('latest_size', 'N/A')}")
    print(f"  管理费: {info.get('management_fee', 'N/A')}")
    print(f"  托管费: {info.get('custody_fee', 'N/A')}")
    print(f"  {'='*50}")

    # 基金经理
    mgr = fetcher.get_fund_manager(args.code)
    if mgr and mgr.get("manager_name"):
        print(f"\n  基金经理: {mgr['manager_name']}")
        print(f"  任职起始: {mgr.get('tenure_start', 'N/A')}")

    # 评级
    rating = fetcher.get_fund_rating(args.code)
    if rating:
        print(f"\n  基金评级:")
        for k, v in rating.items():
            print(f"    {k}: {v}")


def cmd_analyze(args):
    """全面分析基金."""
    print(f"\n正在分析基金 {args.code} ...\n")

    # 基本信息
    info = fetcher.get_fund_info(args.code)
    name = info.get("name", args.code)
    print(f"基金: {name} ({args.code})\n")

    # 获取指标卡片
    card = analyzer.fund_report_card(args.code)
    if "error" in card:
        print(f"错误: {card['error']}")
        return

    print(f"{'指标':<24} {'数值':<12}")
    print("-" * 36)
    for key in [
        "分析区间", "数据天数", "年化收益率", "年化波动率",
        "最大回撤", "胜率", "盈亏比", "夏普比率", "索提诺比率",
        "卡尔玛比率", "VaR (95%, 历史)", "CVaR (95%)", "最大连续亏损天数",
    ]:
        val = card.get(key, "")
        if val != "" and val is not None:
            unit = "%" if key in ("年化收益率", "年化波动率", "最大回撤", "胜率",
                                   "VaR (95%, 历史)", "CVaR (95%)") else ""
            print(f"{key:<24} {val}{unit:<12}")

    # 区间收益
    period_returns = fetcher.get_fund_returns(args.code)
    if period_returns:
        print(f"\n{'区间收益':<24}")
        print("-" * 36)
        label_map = {
            "1w": "近1周", "1m": "近1月", "3m": "近3月", "6m": "近6月",
            "1y": "近1年", "3y": "近3年", "ytd": "今年来",
        }
        for k, label in label_map.items():
            if k in period_returns:
                print(f"{label:<24} {period_returns[k] * 100:6.2f}%")

    # 前十大持仓
    holdings = fetcher.get_fund_holdings(args.code)
    if holdings:
        print(f"\n{'前十大持仓':<24}")
        print("-" * 50)
        for i, h in enumerate(holdings[:10], 1):
            if "stock_name" in h:
                ratio = f"{h['ratio'] * 100:.2f}%" if h.get("ratio") else "N/A"
                print(f"  {i:2d}. {h['stock_name']} ({h.get('stock_code','')}) - {ratio}")


def cmd_compare(args):
    """对比两只基金."""
    codes = [args.code1, args.code2]
    print(f"\n基金对比: {codes[0]} vs {codes[1]}\n")
    print(reporter.fund_comparison(codes))
    print()


def cmd_optimize(args):
    """组合优化."""
    codes = [args.code1, args.code2, args.code3]
    print(f"\n组合优化: {', '.join(codes)}\n")

    # 获取各基金的收益率序列
    returns_dict = {}
    for code in codes:
        nav_df = fetcher.get_fund_nav(code)
        if nav_df.empty or "nav" not in nav_df.columns:
            print(f"警告: 无法获取 {code} 的净值数据，跳过")
            continue
        info = fetcher.get_fund_info(code)
        name = info.get("name", code)[:12]
        # 使用收益率序列
        ret = nav_df["nav"].pct_change().dropna()
        returns_dict[name] = ret

    if len(returns_dict) < 2:
        print("错误: 至少需要 2 只有效基金的数据。")
        return

    returns_df = pd.DataFrame(returns_dict)

    # 蒙特卡洛模拟
    print("运行蒙特卡洛模拟 (5000 次)...")
    mc_result = portfolio.monte_carlo_simulation(returns_df, n_portfolios=5000)
    print(f"\n最优组合 (最大夏普):")
    print(f"  年化收益: {mc_result['best_sharpe']['return'] * 100:.2f}%")
    print(f"  年化波动: {mc_result['best_sharpe']['vol'] * 100:.2f}%")
    print(f"  夏普比率: {mc_result['best_sharpe']['sharpe']:.4f}")
    print(f"  权重: {mc_result['best_sharpe']['weights']}")

    print(f"\n最稳健组合 (最小波动):")
    print(f"  年化收益: {mc_result['min_vol']['return'] * 100:.2f}%")
    print(f"  年化波动: {mc_result['min_vol']['vol'] * 100:.2f}%")
    print(f"  夏普比率: {mc_result['min_vol']['sharpe']:.4f}")
    print(f"  权重: {mc_result['min_vol']['weights']}")

    # 最大夏普 (二次优化)
    print(f"\n解析优化 (最大夏普):")
    max_sr = portfolio.max_sharpe_portfolio(returns_df)
    print(f"  年化收益: {max_sr['return'] * 100:.2f}%")
    print(f"  年化波动: {max_sr['vol'] * 100:.2f}%")
    print(f"  夏普比率: {max_sr['sharpe']:.4f}")
    print(f"  权重: {max_sr['weights']}")

    # 风险平价
    print(f"\n风险平价组合:")
    rp = portfolio.risk_parity_portfolio(returns_df)
    print(f"  年化收益: {rp['return'] * 100:.2f}%")
    print(f"  年化波动: {rp['vol'] * 100:.2f}%")
    print(f"  夏普比率: {rp['sharpe']:.4f}")
    print(f"  权重: {rp['weights']}")


def cmd_report(args):
    """生成 Markdown 报告."""
    print(f"生成基金分析报告: {args.code}")
    md = reporter.generate_report(args.code)
    out_dir = os.path.join("data", "reports")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{args.code}_report.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"报告已保存: {out_path}")
    print(md)


def cmd_export(args):
    """导出净值 CSV."""
    path = reporter.export_to_csv(args.code)
    print(f"已导出: {path}")


def cmd_clearcache(args):
    """清空缓存."""
    fetcher.clear_cache()


def cmd_quarter(args):
    """解析基金定期报告 PDF."""
    result = quarterly_parser.parse_quarterly_report(args.pdf)
    print(f"报告期: {result.report_period or '未识别'}")
    print(f"基金: {result.fund_name or '未识别'} ({result.fund_code or '未识别'})")
    print(f"页数: {result.pages}")
    if result.asset_allocation:
        print("\n资产配置:")
        for key, item in result.asset_allocation.items():
            print(f"  {key}: {item.value:.2f}{item.unit}")
    if result.manager_commentary:
        print(f"\n基金经理观点:\n{result.manager_commentary}")
    if result.warnings:
        print("\n提示:")
        for warning in result.warnings:
            print(f"  - {warning}")


def cmd_reports(args):
    """查询天天基金可下载的定期报告。"""
    records = report_downloader.list_reports(
        args.code,
        args.type,
        years=args.years,
        include_summary=args.include_summary,
    )
    if not records:
        print("没有找到符合条件的定期报告。")
        return
    labels = {"quarter": "季报", "semiannual": "半年报", "annual": "年报"}
    print(f"\n找到 {len(records)} 份报告：\n")
    print(f"{'公告日期':<12} {'类型':<8} {'公告标题'}")
    print("-" * 90)
    for item in records:
        print(
            f"{item.published_date.isoformat():<12} "
            f"{labels[item.report_type]:<8} {item.title}"
        )


def cmd_download_report(args):
    """查询并下载基金定期报告。"""
    records = report_downloader.list_reports(
        args.code,
        args.type,
        years=args.years,
        include_summary=args.include_summary,
    )
    if not records:
        raise LookupError("没有找到符合条件的定期报告")
    selected = records if args.all else records[:1]
    for record in selected:
        path = report_downloader.download_report(
            record, args.output_dir, force=args.force
        )
        print(f"已下载：{path}")


def cmd_auto_report(args):
    """自动下载最新报告、解析 PDF 并生成双版本 Markdown。"""
    record, pdf_path = report_downloader.download_latest_report(
        args.code,
        args.type,
        output_dir=args.download_dir,
        force=args.force,
    )
    print(f"已取得最新报告：{record.title}")
    print(f"PDF：{pdf_path}")
    parsed = quarterly_parser.parse_quarterly_report(str(pdf_path))
    nav_df = fetcher.get_fund_nav(
        args.code, start_date="1990-01-01", end_date=None
    )
    performance = performance_summary.calculate_performance_summary(nav_df)
    professional = disclosure_reporter.generate_professional(
        record, parsed, performance
    )
    client = disclosure_reporter.generate_client(record, parsed, performance)
    os.makedirs(args.output_dir, exist_ok=True)
    stem = f"{args.code}_{args.type}"
    professional_path = os.path.join(
        args.output_dir, f"{stem}_professional.md"
    )
    client_path = os.path.join(args.output_dir, f"{stem}_client.md")
    with open(professional_path, "w", encoding="utf-8") as file:
        file.write(professional)
    with open(client_path, "w", encoding="utf-8") as file:
        file.write(client)
    print(f"专业版已保存：{professional_path}")
    print(f"客户版已保存：{client_path}")


def cmd_bond_report(args):
    """生成债券基金专业版和客户版报告."""
    nav_df = fetcher.get_fund_nav(args.code, args.start_date, args.end_date)
    if nav_df.empty or "nav" not in nav_df.columns:
        raise ValueError(f"无法获取基金 {args.code} 的净值")
    nav = nav_df.copy()
    if "date" in nav.columns:
        nav["date"] = pd.to_datetime(nav["date"])
        nav = nav.set_index("date")

    factor_returns = bond_attribution.load_factor_csv(
        args.factor_csv, values_are_returns=args.factor_values_are_returns
    )
    attribution = bond_attribution.attribute_returns(
        bond_attribution.returns_from_nav(nav["nav"]),
        factor_returns,
        min_observations=args.min_observations,
    )
    quarter = (
        quarterly_parser.parse_quarterly_report(args.quarter_pdf)
        if args.quarter_pdf
        else None
    )
    info = fetcher.get_fund_info(args.code)
    name = info.get("name") or (quarter.fund_name if quarter else "") or args.code

    professional = bond_reporter.generate_professional_report(
        fund_code=args.code,
        fund_name=name,
        attribution=attribution,
        quarterly_report=quarter,
    )
    client = bond_reporter.generate_client_report(
        fund_code=args.code,
        fund_name=name,
        attribution=attribution,
        quarterly_report=quarter,
    )
    os.makedirs(args.output_dir, exist_ok=True)
    professional_path = os.path.join(args.output_dir, f"{args.code}_professional.md")
    client_path = os.path.join(args.output_dir, f"{args.code}_client.md")
    with open(professional_path, "w", encoding="utf-8") as file:
        file.write(professional)
    with open(client_path, "w", encoding="utf-8") as file:
        file.write(client)
    print(f"专业版已保存: {professional_path}")
    print(f"客户版已保存: {client_path}")


def main():
    parser = argparse.ArgumentParser(
        description="FundAnalyzer — 公募基金智能分析工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python fund_cli.py search 沪深300
  python fund_cli.py info 110020
  python fund_cli.py analyze 110020
  python fund_cli.py compare 110020 000311
  python fund_cli.py optimize 110020 000311 005827
  python fund_cli.py report 110020
  python fund_cli.py quarter data/reports/基金季报.pdf
  python fund_cli.py reports 000001 --type annual --years 3
  python fund_cli.py download-report 000001 --type quarter
  python fund_cli.py auto-report 000001 --type quarter
  python fund_cli.py bond-report 000000 --factor-csv data/factors.csv --quarter-pdf data/基金季报.pdf
  python fund_cli.py export 110020
  python fund_cli.py clearcache
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # search
    p_search = subparsers.add_parser("search", help="搜索基金")
    p_search.add_argument("keyword", type=str, help="基金名称或代码关键词")

    # info
    p_info = subparsers.add_parser("info", help="基金基本信息")
    p_info.add_argument("code", type=str, help="基金代码 (如 110020)")

    # analyze
    p_analyze = subparsers.add_parser("analyze", help="全面分析基金")
    p_analyze.add_argument("code", type=str, help="基金代码")

    # compare
    p_compare = subparsers.add_parser("compare", help="对比两只基金")
    p_compare.add_argument("code1", type=str, help="基金代码1")
    p_compare.add_argument("code2", type=str, help="基金代码2")

    # optimize
    p_optimize = subparsers.add_parser("optimize", help="组合优化 (3只基金)")
    p_optimize.add_argument("code1", type=str, help="基金代码1")
    p_optimize.add_argument("code2", type=str, help="基金代码2")
    p_optimize.add_argument("code3", type=str, help="基金代码3")

    # report
    p_report = subparsers.add_parser("report", help="生成 Markdown 报告")
    p_report.add_argument("code", type=str, help="基金代码")

    # quarter
    p_quarter = subparsers.add_parser("quarter", help="解析基金季报/中报/年报 PDF")
    p_quarter.add_argument("pdf", type=str, help="定期报告 PDF 路径")

    # reports
    p_reports = subparsers.add_parser("reports", help="查询天天基金定期报告")
    p_reports.add_argument("code", type=str, help="基金代码")
    p_reports.add_argument(
        "--type",
        choices=report_downloader.REPORT_TYPES,
        default="all",
        help="报告类型",
    )
    p_reports.add_argument("--years", type=int, help="仅显示最近 N 个自然年")
    p_reports.add_argument(
        "--include-summary", action="store_true", help="同时显示报告摘要"
    )

    # download-report
    p_download = subparsers.add_parser(
        "download-report", help="从天天基金下载定期报告 PDF"
    )
    p_download.add_argument("code", type=str, help="基金代码")
    p_download.add_argument(
        "--type",
        choices=report_downloader.REPORT_TYPES,
        default="quarter",
        help="报告类型",
    )
    p_download.add_argument("--years", type=int, help="仅查最近 N 个自然年")
    p_download.add_argument(
        "--all", action="store_true", help="下载所有符合条件的报告，默认只下载最新一份"
    )
    p_download.add_argument(
        "--include-summary", action="store_true", help="允许下载报告摘要"
    )
    p_download.add_argument(
        "--output-dir", default=os.path.join("data", "source_reports")
    )
    p_download.add_argument("--force", action="store_true", help="覆盖本地缓存")

    # auto-report
    p_auto = subparsers.add_parser(
        "auto-report", help="自动下载最新报告并生成专业版和客户版"
    )
    p_auto.add_argument("code", type=str, help="基金代码")
    p_auto.add_argument(
        "--type",
        choices=("quarter", "semiannual", "annual"),
        default="quarter",
        help="报告类型",
    )
    p_auto.add_argument(
        "--download-dir", default=os.path.join("data", "source_reports")
    )
    p_auto.add_argument(
        "--output-dir", default=os.path.join("data", "reports")
    )
    p_auto.add_argument("--force", action="store_true", help="重新下载报告")

    # bond-report
    p_bond = subparsers.add_parser("bond-report", help="生成债基专业版与客户版报告")
    p_bond.add_argument("code", type=str, help="基金代码")
    p_bond.add_argument("--factor-csv", required=True, help="债券因子 CSV 路径")
    p_bond.add_argument("--quarter-pdf", help="基金季报/中报/年报 PDF 路径")
    p_bond.add_argument("--start-date", help="净值开始日期 YYYY-MM-DD")
    p_bond.add_argument("--end-date", help="净值结束日期 YYYY-MM-DD")
    p_bond.add_argument(
        "--factor-values-are-returns",
        action="store_true",
        help="因子 CSV 已经是日收益率，默认按指数点位转换",
    )
    p_bond.add_argument("--min-observations", type=int, default=30)
    p_bond.add_argument("--output-dir", default=os.path.join("data", "reports"))

    # export
    p_export = subparsers.add_parser("export", help="导出净值 CSV")
    p_export.add_argument("code", type=str, help="基金代码")

    # clearcache
    subparsers.add_parser("clearcache", help="清空数据缓存")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # 命令路由
    cmd_map = {
        "search": cmd_search,
        "info": cmd_info,
        "analyze": cmd_analyze,
        "compare": cmd_compare,
        "optimize": cmd_optimize,
        "report": cmd_report,
        "quarter": cmd_quarter,
        "reports": cmd_reports,
        "download-report": cmd_download_report,
        "auto-report": cmd_auto_report,
        "bond-report": cmd_bond_report,
        "export": cmd_export,
        "clearcache": cmd_clearcache,
    }

    # 确保 optimize 命令有 pandas
    if args.command in ("optimize", "bond-report"):
        import pandas as pd

    cmd_func = cmd_map[args.command]
    cmd_func(args)


if __name__ == "__main__":
    main()
