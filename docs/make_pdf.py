"""Standalone Cross-Platform Markdown-to-PDF Converter.

Designed for fresh clones and zero hardcoded user paths.
Supported backends:
1. Environment-specified MD2PDF_PATH (if configured or cloned adjacent).
2. Host System Pandoc (pandoc + wkhtmltopdf / xelatex / pdflatex).
3. Headless Chromium-based browsers (Chrome, Chromium, Edge) across Windows, Linux, and macOS.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def _find_md2pdf_runner() -> Path | None:
    """Find md2pdf entrypoint via environment variable or standard relative directory."""
    env_path = os.getenv("MD2PDF_PATH")
    if env_path:
        p = Path(env_path) / "direct_convert.py"
        if p.exists():
            return p

    # Check relative to repo root (e.g., ../md2pdf-desktop)
    repo_root = Path(__file__).resolve().parent.parent
    for candidate in [
        repo_root.parent / "md2pdf-desktop" / "direct_convert.py",
        repo_root.parent / "Utility" / "md2pdf-desktop" / "direct_convert.py",
    ]:
        if candidate.exists():
            return candidate

    return None


def _find_browser_executable() -> str | None:
    """Discover available Chromium-based browser executable across Windows and Linux."""
    # 1. Search system PATH dynamically
    for candidate in [
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
        "microsoft-edge",
        "microsoft-edge-stable",
        "chrome",
        "msedge",
    ]:
        found = shutil.which(candidate)
        if found:
            return found

    # 2. Windows standard system locations using environment variables
    if sys.platform == "win32":
        prog_files = os.getenv("ProgramFiles", r"C:\Program Files")
        prog_files_x86 = os.getenv("ProgramFiles(x86)", r"C:\Program Files (x86)")
        local_app_data = os.getenv("LocalAppData", "")

        for base in [prog_files, prog_files_x86, local_app_data]:
            if not base:
                continue
            for rel in [
                r"Microsoft\Edge\Application\msedge.exe",
                r"Google\Chrome\Application\chrome.exe",
            ]:
                target = Path(base) / rel
                if target.exists():
                    return str(target)

    # 3. Linux standard locations
    if sys.platform.startswith("linux"):
        for linux_path in [
            Path("/usr/bin/google-chrome"),
            Path("/usr/bin/chromium-browser"),
            Path("/usr/bin/chromium"),
            Path("/snap/bin/chromium"),
            Path("/usr/bin/microsoft-edge"),
        ]:
            if linux_path.exists():
                return str(linux_path)

    return None


def convert_with_md2pdf(md_file: Path, pdf_file: Path, mode: str = "auto") -> bool:
    """Attempt conversion using md2pdf engine if available."""
    runner = _find_md2pdf_runner()
    if not runner:
        return False

    cmd = [
        sys.executable,
        str(runner),
        str(md_file),
        "-o",
        str(pdf_file),
        "-m",
        mode,
        "--no-notify",
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)  # noqa: S603
        return pdf_file.exists() and pdf_file.stat().st_size > 0
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def convert_with_system_pandoc(md_file: Path, pdf_file: Path) -> bool:
    """Attempt conversion using system pandoc if installed on Linux / Windows."""
    pandoc_bin = shutil.which("pandoc")
    if not pandoc_bin:
        return False

    cmd = [
        pandoc_bin,
        str(md_file),
        "-o",
        str(pdf_file),
        "--pdf-engine=wkhtmltopdf",
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)  # noqa: S603
        return pdf_file.exists() and pdf_file.stat().st_size > 0
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def convert_with_browser_headless(md_file: Path, pdf_file: Path) -> bool:
    """Cross-platform headless browser printing using Edge / Chrome / Chromium."""
    browser_bin = _find_browser_executable()
    if not browser_bin:
        return False

    try:
        import markdown_it
    except ImportError:
        return False

    html_file = md_file.with_suffix(".html")
    md_text = md_file.read_text(encoding="utf-8")
    md = markdown_it.MarkdownIt()
    html_body = md.render(md_text)

    css = """
  @page { size: A4; margin: 18mm 16mm; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
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
    full_html = f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>{md_file.stem}</title><style>{css}</style></head><body>{html_body}</body></html>"
    html_file.write_text(full_html, encoding="utf-8")

    file_uri = html_file.resolve().as_uri()
    cmd = [
        browser_bin,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--run-all-compositor-stages-before-draw",
        f"--print-to-pdf={pdf_file.resolve()}",
        file_uri,
    ]
    try:
        subprocess.run(cmd, check=True)  # noqa: S603
        return pdf_file.exists() and pdf_file.stat().st_size > 0
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def convert_markdown(input_md: Path, output_pdf: Path | None = None, mode: str = "auto") -> Path:
    """Unified cross-platform conversion entrypoint."""
    input_path = input_md.resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input Markdown file not found: {input_path}")

    target_pdf = output_pdf.resolve() if output_pdf else input_path.with_suffix(".pdf")

    # 1. Primary md2pdf engine (if configured or detected)
    if convert_with_md2pdf(input_path, target_pdf, mode=mode):
        return target_pdf

    # 2. System Pandoc
    if convert_with_system_pandoc(input_path, target_pdf):
        return target_pdf

    # 3. Headless Chrome/Chromium/Edge
    if convert_with_browser_headless(input_path, target_pdf):
        return target_pdf

    raise RuntimeError(
        "Failed to generate PDF: No supported PDF backend found.\n"
        "Please ensure Chrome/Chromium, Edge, or pandoc is installed and accessible on PATH."
    )


def main():
    parser = argparse.ArgumentParser(
        description="Standalone Cross-Platform Markdown-to-PDF Converter (Windows, Linux, macOS)."
    )
    parser.add_argument("input", help="Path to input Markdown (.md) file")
    parser.add_argument("-o", "--output", help="Path to output PDF file (defaults to input.pdf)")
    parser.add_argument(
        "-m",
        "--mode",
        default="auto",
        choices=["auto", "sidebar", "latex", "simple"],
        help="Conversion mode (used if md2pdf engine is available)",
    )
    args = parser.parse_args()

    input_file = Path(args.input)
    output_file = Path(args.output) if args.output else None

    try:
        result = convert_markdown(input_file, output_file, mode=args.mode)
        size_kb = result.stat().st_size / 1024.0
        print(f"[Success] PDF generated: {result} ({size_kb:.1f} KB)")
    except Exception as e:
        print(f"[Error] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
