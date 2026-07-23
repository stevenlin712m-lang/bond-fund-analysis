# 债券基金分析扩展：Codex 分步使用指南

## 第一步：准备环境

在 Codex 中打开项目目录后，让 Codex 执行：

```text
请安装 requirements.txt，并运行全部测试。
```

使用 Python 3.10 或更高版本。项目新增的关键依赖是 `pypdf`（读取文本型 PDF）
和 `pytest`（离线测试）；新版 AKShare 也需要较新的 Python。

## 网页版：最简单的日常使用方式

```bash
python start_web.py
```

浏览器会自动打开债券基金分析台。输入6位基金代码、选择报告类型，然后点击
“开始分析”即可。页面可以直接切换专业分析和客户沟通版，并下载报告或原始 PDF。
关闭网页服务时，在启动它的终端按 `Control+C`。

## 第二步：准备债券因子

准备一个 CSV，第一列名为 `date`，其他列是因子指数点位：

```csv
date,rate,credit,convertible,liquidity
2025-01-02,100.01,100.02,99.80,100.00
2025-01-03,100.05,100.03,100.20,99.99
```

- `rate`：利率债或中长期国债指数
- `credit`：信用债指数
- `convertible`：可转债指数
- `liquidity`：资金面代理指数

指数必须使用同一频率，日期应覆盖基金净值区间。若 CSV 已经是日收益率，加
`--factor-values-are-returns`。

## 第三步：自动查询和下载季报、年报

不再需要先到网页手动下载。输入基金代码即可查看报告：

```bash
python fund_cli.py reports 000001 --type all --years 3
```

报告类型可选：

- `quarter`：季报
- `semiannual`：半年报
- `annual`：年报
- `all`：全部定期报告

下载最新一份季报：

```bash
python fund_cli.py download-report 000001 --type quarter
```

原始 PDF 和来源元数据会保存在 `data/source_reports/基金代码/`。程序会校验
PDF 文件头并记录 SHA256，重复执行时默认使用本地文件。

## 第四步：一步生成专业版和客户版

```bash
python fund_cli.py auto-report 000001 --type quarter
```

这个命令会自动完成：

1. 查询天天基金定期报告公告；
2. 选择最新的完整报告（默认排除“摘要”）；
3. 从东方财富 PDF 服务器下载并校验文件；
4. 提取资产配置、经理观点和前五大债券持仓；
5. 在 `data/reports/` 生成专业版和客户通俗版 Markdown。

半年报或年报只需更改类型：

```bash
python fund_cli.py auto-report 000001 --type annual
```

## 第五步：解析已有 PDF

```bash
python fund_cli.py quarter path/to/基金季报.pdf
```

Codex 会提取报告期、基金代码、资产配置、基金经理观点和前五大债券持仓。
若 PDF 是扫描件，先 OCR；任何自动提取结果都应回看原文证据。

## 第六步：加入净值因子归因后生成两种报告

```bash
python fund_cli.py bond-report 000001 \
  --factor-csv data/factors.csv \
  --quarter-pdf path/to/基金季报.pdf
```

输出到 `data/reports/`：

- `000001_professional.md`：包含 Beta、贡献估计、R²、原文证据和方法局限。
- `000001_client.md`：说明主要收益来源、适合行情、风险和沟通边界。

## 第七步：先跑离线示例

```bash
python examples/bond_demo.py
```

示例不访问网络，会生成两份 `DEMO01` 报告，适合先验证整个链路。

## 口径说明

净值因子归因属于统计推断，不能写成基金真实持仓事实；季报属于已披露事实，
但有披露时滞。报告固定区分这两类信息，正式对客前仍需人工复核。

自动下载依赖天天基金/东方财富公开网页接口，不需要 API Key，但不属于承诺
稳定性的商业数据服务。若网页结构变化，程序会明确报错，不会把错误页面当成 PDF。
