"""Convert Markdown Report to clean HTML and PDF using Microsoft Edge headless print."""

from __future__ import annotations

import subprocess
from pathlib import Path

import markdown_it

DOCS_DIR = Path(__file__).resolve().parent
MD_PATH = DOCS_DIR / "REPORT.md"
HTML_PATH = DOCS_DIR / "REPORT.html"
PDF_PATH = DOCS_DIR / "REPORT.pdf"

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def convert():
    md_text = MD_PATH.read_text(encoding="utf-8")
    md = markdown_it.MarkdownIt()
    html_body = md.render(md_text)

    css = """
  @page {
    size: A4;
    margin: 18mm 16mm;
  }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    line-height: 1.5;
    color: #1e293b;
    font-size: 10pt;
  }
  h1 { font-size: 17pt; border-bottom: 2px solid #0f172a; padding-bottom: 4px; margin-top: 0; }
  h2 { font-size: 13pt; border-bottom: 1px solid #cbd5e1; padding-bottom: 3px; margin-top: 16pt; color: #0f172a; }
  h3 { font-size: 11pt; margin-top: 12pt; color: #334155; }
  table { width: 100%; border-collapse: collapse; margin: 10pt 0; font-size: 9pt; }
  th, td { border: 1px solid #94a3b8; padding: 4pt 6pt; text-align: left; }
  th { background-color: #f1f5f9; font-weight: 600; }
  code { font-family: ui-monospace, SFMono-Regular, Consolas, monospace; background: #f1f5f9; padding: 1pt 3pt; font-size: 8.5pt; }
  pre { background: #f8fafc; border: 1px solid #e2e8f0; padding: 6pt; border-radius: 4px; font-size: 8pt; }
  blockquote { border-left: 3px solid #0284c7; margin: 8pt 0; padding-left: 8pt; color: #475569; }
"""

    full_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Technical Evaluation & Architecture Report: Trustworthy AI Guardrails</title>
<style>
{css}
</style>
</head>
<body>
{html_body}
</body>
</html>"""

    HTML_PATH.write_text(full_html, encoding="utf-8")
    print(f"Generated HTML at {HTML_PATH}")

    # Compile to PDF using Edge headless printer
    cmd = [
        EDGE_PATH,
        "--headless",
        "--disable-gpu",
        "--run-all-compositor-stages-before-draw",
        f"--print-to-pdf={PDF_PATH}",
        f"file:///{HTML_PATH.as_posix()}",
    ]
    subprocess.run(cmd, check=True)  # noqa: S603
    print(f"Generated PDF at {PDF_PATH}")


if __name__ == "__main__":
    convert()
