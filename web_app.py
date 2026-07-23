"""零额外依赖的债券基金分析网页。"""

from __future__ import annotations

import html
import mimetypes
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from fund_analyzer import disclosure_reporter, quarterly_parser, report_downloader


HOST = "127.0.0.1"
PORT = 8765
ROOT = Path(__file__).resolve().parent
REPORT_LABELS = {
    "quarter": "最新季报",
    "semiannual": "最新半年报",
    "annual": "最新年报",
}


def _page(content: str, *, code: str = "", selected: str = "quarter") -> str:
    options = "".join(
        f'<option value="{key}"{" selected" if key == selected else ""}>{label}</option>'
        for key, label in REPORT_LABELS.items()
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>债券基金分析台</title>
<style>
:root{{--ink:#182230;--muted:#667085;--line:#e4e7ec;--blue:#315efb;--pale:#f5f7fb}}
*{{box-sizing:border-box}} body{{margin:0;background:#f3f5f8;color:var(--ink);
font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",sans-serif}}
.shell{{max-width:1160px;margin:auto;padding:54px 24px 80px}}
.eyebrow{{color:var(--blue);font-weight:700;font-size:13px;letter-spacing:.12em}}
h1{{font-size:42px;letter-spacing:-.04em;margin:10px 0 8px}}
.lead{{color:var(--muted);margin:0 0 30px}}
.panel{{background:white;border:1px solid var(--line);border-radius:20px;
padding:24px;box-shadow:0 10px 36px rgba(16,24,40,.06)}}
form{{display:grid;grid-template-columns:2fr 1.2fr 1fr;gap:14px;align-items:end}}
label{{display:block;font-weight:650;font-size:14px;margin-bottom:8px}}
input,select{{width:100%;height:48px;border:1px solid #d0d5dd;border-radius:11px;
padding:0 14px;font-size:16px;background:white}}
button{{height:48px;border:0;border-radius:11px;background:var(--blue);color:white;
font-size:16px;font-weight:700;cursor:pointer}} button:hover{{background:#244bd7}}
.hint{{margin-top:18px;color:var(--muted);font-size:13px}}
.status{{margin-top:22px;padding:14px 16px;border-radius:11px;background:#eef4ff;
border-left:4px solid var(--blue)}} .error{{background:#fff1f0;border-color:#d92d20}}
.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:22px 0}}
.metric{{background:white;border:1px solid var(--line);border-radius:15px;padding:16px}}
.metric small{{color:var(--muted)}} .metric strong{{display:block;font-size:21px;margin-top:7px}}
.tabs{{display:flex;gap:8px;margin-top:24px}} .tab{{background:#e9edf5;color:#344054;
padding:0 17px}} .tab.active{{background:#182230;color:white}}
.tabbody{{display:none;margin-top:12px}} .tabbody.active{{display:block}}
pre{{white-space:pre-wrap;word-break:break-word;font:14px/1.75 ui-monospace,SFMono-Regular,Menlo,monospace;
background:#101828;color:#e6eaf2;padding:24px;border-radius:15px;max-height:720px;overflow:auto}}
.downloads{{display:flex;flex-wrap:wrap;gap:10px;margin:14px 0}}
.downloads a{{text-decoration:none;color:#244bd7;background:#eef4ff;padding:10px 14px;border-radius:9px;font-weight:650}}
.source{{line-height:1.8}} .source a{{color:#244bd7}}
@media(max-width:760px){{form,.metrics{{grid-template-columns:1fr}} h1{{font-size:34px}}}}
</style>
</head>
<body><main class="shell">
<div class="eyebrow">BOND FUND RESEARCH</div>
<h1>债券基金分析台</h1>
<p class="lead">输入基金代码，自动获取最新定期报告，并生成专业版与客户沟通版。</p>
<section class="panel">
<form method="post" action="/analyze">
  <div><label for="code">基金代码</label>
  <input id="code" name="code" value="{html.escape(code)}" maxlength="6"
  inputmode="numeric" pattern="[0-9]{{6}}" placeholder="例如：013864" required></div>
  <div><label for="report_type">报告类型</label>
  <select id="report_type" name="report_type">{options}</select></div>
  <button type="submit">开始分析</button>
</form>
<div class="hint">公开报告存在披露时滞；自动分析用于研究辅助，正式投研或对客前请核对公告原文。</div>
</section>
{content}
</main>
<script>
function showTab(id,button){{
 document.querySelectorAll('.tabbody').forEach(x=>x.classList.remove('active'));
 document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));
 document.getElementById(id).classList.add('active'); button.classList.add('active');
}}
</script></body></html>"""


def _download_link(path: Path, label: str) -> str:
    relative = path.resolve().relative_to(ROOT)
    return f'<a href="/download?path={quote(str(relative))}">{html.escape(label)}</a>'


def _result_html(code: str, report_type: str) -> str:
    record, pdf_path = report_downloader.download_latest_report(
        code, report_type, output_dir=ROOT / "data/source_reports"
    )
    parsed = quarterly_parser.parse_quarterly_report(str(pdf_path))
    professional = disclosure_reporter.generate_professional(record, parsed)
    client = disclosure_reporter.generate_client(record, parsed)

    output_dir = ROOT / "data/reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    professional_path = output_dir / f"{code}_{report_type}_professional.md"
    client_path = output_dir / f"{code}_{report_type}_client.md"
    professional_path.write_text(professional, encoding="utf-8")
    client_path.write_text(client, encoding="utf-8")

    bond = parsed.asset_allocation.get("bond")
    bond_text = f"{bond.value:.2f}%" if bond and bond.value is not None else "待核对"
    warnings = "<br>".join(html.escape(item) for item in parsed.warnings)
    return f"""
<div class="status">分析完成：{html.escape(record.title)}</div>
<section class="metrics">
 <div class="metric"><small>基金代码</small><strong>{code}</strong></div>
 <div class="metric"><small>报告期</small><strong>{html.escape(parsed.report_period or "待核对")}</strong></div>
 <div class="metric"><small>债券占比</small><strong>{bond_text}</strong></div>
 <div class="metric"><small>识别债券</small><strong>{len(parsed.top_bond_holdings)}只</strong></div>
</section>
<div class="tabs">
 <button class="tab active" onclick="showTab('professional',this)">专业分析</button>
 <button class="tab" onclick="showTab('client',this)">客户沟通版</button>
 <button class="tab" onclick="showTab('source',this)">原始资料</button>
</div>
<section id="professional" class="tabbody active">
 <div class="downloads">{_download_link(professional_path, "下载专业版 Markdown")}</div>
 <pre>{html.escape(professional)}</pre>
</section>
<section id="client" class="tabbody">
 <div class="downloads">{_download_link(client_path, "下载客户版 Markdown")}</div>
 <pre>{html.escape(client)}</pre>
</section>
<section id="source" class="tabbody panel source">
 <p><b>公告：</b>{html.escape(record.title)}</p>
 <p><b>公告日期：</b>{record.published_date.isoformat()}</p>
 <p><b>解析提示：</b><br>{warnings}</p>
 <div class="downloads">
 {_download_link(Path(pdf_path), "下载原始 PDF")}
 <a href="{html.escape(record.detail_url)}" target="_blank">查看天天基金公告页</a>
 </div>
</section>"""


class Handler(BaseHTTPRequestHandler):
    def _send_html(self, body: str, status: int = 200) -> None:
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/download":
            requested = parse_qs(parsed.query).get("path", [""])[0]
            try:
                target = (ROOT / requested).resolve()
                target.relative_to(ROOT / "data")
                if not target.is_file():
                    raise FileNotFoundError
            except (ValueError, FileNotFoundError):
                self.send_error(404)
                return
            data = target.read_bytes()
            self.send_response(200)
            self.send_header(
                "Content-Type",
                mimetypes.guess_type(target.name)[0] or "application/octet-stream",
            )
            self.send_header(
                "Content-Disposition",
                f"attachment; filename*=UTF-8''{quote(target.name)}",
            )
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        self._send_html(_page(""))

    def do_POST(self) -> None:
        if self.path != "/analyze":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        form = parse_qs(self.rfile.read(length).decode("utf-8"))
        code = form.get("code", [""])[0].strip()
        report_type = form.get("report_type", ["quarter"])[0]
        if not re.fullmatch(r"\d{6}", code) or report_type not in REPORT_LABELS:
            self._send_html(
                _page('<div class="status error">请输入正确的6位基金代码。</div>', code=code),
                400,
            )
            return
        try:
            content = _result_html(code, report_type)
            self._send_html(_page(content, code=code, selected=report_type))
        except Exception as exc:
            message = html.escape(str(exc))
            self._send_html(
                _page(
                    f'<div class="status error">分析失败：{message}<br>'
                    "请检查网络连接后重试。</div>",
                    code=code,
                    selected=report_type,
                ),
                500,
            )

    def log_message(self, format: str, *args) -> None:
        return


def run(host: str = HOST, port: int = PORT) -> None:
    print(f"债券基金分析网页已启动：http://{host}:{port}")
    print("按 Control+C 可以关闭。")
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    run()
