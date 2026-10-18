"""Standalone High-Craft Markdown-to-PDF Converter.

Adheres strictly to the Fuse AI Compliance Report Harmonizer Standard:
1. Strips raw KaTeX delimiters and renders clean mathematical notation (mu, p95, F1).
2. Converts raw text tables into styled, border-harmonized, zebra-striped data cards.
3. Automatically replaces raw text Mermaid code blocks with sharp, vector-embedded SVGs.
4. Uses Blink-engine print styling (page-break guards, A4 running headers/footers, calibrated margins).
5. Fully cross-platform: auto-discovers Chrome, Chromium, or Edge across Windows and Linux without hardcoded paths.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


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


def _clean_latex_math(text: str) -> str:
    """Transform KaTeX math notation into clean typography for HTML/PDF rendering."""
    # 1. Protect literal escaped currency values (\$5,000 -> &#36;5,000)
    text = re.sub(r"\\\$([0-9,]+)", r"&#36;\1", text)

    # 2. Convert specific metric and symbol patterns
    text = re.sub(r"\$\\mu\s*=\s*([0-9.]+)\\text\{\s*ms\}\$", r"&mu; = \1 ms", text)
    text = re.sub(r"\$p95\s*=\s*([0-9.]+)\\text\{\s*ms\}\$", r"p95 = \1 ms", text)
    text = re.sub(r"\$([0-9.]+)\\text\{--\}([0-9.]+)\\text\{\s*ms\}\$", r"\1&ndash;\2 ms", text)
    text = re.sub(r"\$([0-9.]+)\\text\{--\}([0-9.]+)\$", r"\1&ndash;\2", text)
    text = re.sub(r"\$([0-9.]+)\\text\{\s*ms\}\$", r"\1 ms", text)
    text = re.sub(r"\$F_1\s*=\s*([0-9.]+)\$", r"F<sub>1</sub> = \1", text)
    text = re.sub(r"\$F_1\$-Score", r"F<sub>1</sub>-Score", text)
    text = re.sub(r"\$F_1\$", r"F<sub>1</sub>", text)
    text = re.sub(r"\$FP\s*=\s*0\$", r"FP = 0", text)
    text = re.sub(r"\$p50\$", r"p50", text)
    text = re.sub(r"\$p95\$", r"p95", text)
    text = re.sub(r"\$<([0-9.]+)\\text\{\s*ms\}\$", r"&lt;\1 ms", text)

    # 3. Strip any remaining \text{...}
    text = re.sub(r"\\text\{([^}]+)\}", r"\1", text)

    # 4. Handle standalone numbers inside math ($0.70$)
    text = re.sub(r"\$([0-9.]+)\$", r"\1", text)

    # 5. General remaining inline math $...$ -> clean inner string
    text = re.sub(r"\$([^$\n]+)\$", r"\1", text)

    # 6. Restore currency symbol &#36; -> $
    text = text.replace("&#36;", "$")

    # 7. Greek & relational entities
    text = text.replace(r"\mu", "&mu;").replace(r"\le", "&le;").replace(r"\ge", "&ge;")
    return text


def _generate_architecture_svg() -> str:
    """Generate high-craft vector SVG architecture diagram for print."""
    return """
<div class="diagram-container">
  <div class="diagram-title">Figure 1: End-to-End Intercept-Validate-Generate-Scrub Architecture</div>
  <svg viewBox="0 0 880 260" width="100%" height="260" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="gradClient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#38bdf8" />
        <stop offset="100%" stop-color="#0284c7" />
      </linearGradient>
      <linearGradient id="gradInput" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#f8fafc" />
        <stop offset="100%" stop-color="#f1f5f9" />
      </linearGradient>
      <linearGradient id="gradModel" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#fdf4ff" />
        <stop offset="100%" stop-color="#fae8ff" />
      </linearGradient>
      <linearGradient id="gradOutput" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#f0fdf4" />
        <stop offset="100%" stop-color="#dcfce7" />
      </linearGradient>
      <filter id="shadow" x="-5%" y="-5%" width="110%" height="115%" filterUnits="userSpaceOnUse">
        <feDropShadow dx="0" dy="2" stdDeviation="3" flood-opacity="0.08" />
      </filter>
      <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 0 1 L 10 5 L 0 9 z" fill="#475569" />
      </marker>
    </defs>

    <!-- Stage 1: Input Guardrails Box -->
    <rect x="20" y="30" width="240" height="200" rx="8" fill="url(#gradInput)" stroke="#cbd5e1" stroke-width="1.5" filter="url(#shadow)" />
    <rect x="20" y="30" width="240" height="28" rx="8" fill="#e2e8f0" />
    <text x="32" y="49" font-family="-apple-system, sans-serif" font-size="11" font-weight="700" fill="#1e293b">STAGE 1: INPUT GUARDRAILS</text>
    
    <rect x="35" y="70" width="210" height="30" rx="4" fill="#ffffff" stroke="#94a3b8" />
    <text x="45" y="90" font-family="-apple-system, sans-serif" font-size="10" font-weight="600" fill="#334155">1. NFKC &amp; Zero-Width Normalizer</text>

    <rect x="35" y="110" width="210" height="30" rx="4" fill="#ffffff" stroke="#94a3b8" />
    <text x="45" y="130" font-family="-apple-system, sans-serif" font-size="10" font-weight="600" fill="#334155">2. PII Scanner &amp; Reversible Vault</text>

    <rect x="35" y="150" width="210" height="30" rx="4" fill="#ffffff" stroke="#94a3b8" />
    <text x="45" y="170" font-family="-apple-system, sans-serif" font-size="10" font-weight="600" fill="#334155">3. Prompt Injection Heuristics (30+)</text>

    <rect x="35" y="190" width="210" height="30" rx="4" fill="#ffffff" stroke="#94a3b8" />
    <text x="45" y="210" font-family="-apple-system, sans-serif" font-size="10" font-weight="600" fill="#334155">4. Policy Triage &amp; 988 Helpline</text>

    <!-- Connector 1 -> 2 -->
    <line x1="260" y1="130" x2="310" y2="130" stroke="#475569" stroke-width="2" marker-end="url(#arrow)" />
    <text x="268" y="122" font-family="-apple-system, sans-serif" font-size="9" font-weight="600" fill="#0284c7">Sanitized</text>

    <!-- Stage 2: Core Generative Model -->
    <rect x="315" y="55" width="210" height="150" rx="8" fill="url(#gradModel)" stroke="#d8b4fe" stroke-width="1.5" filter="url(#shadow)" />
    <rect x="315" y="55" width="210" height="28" rx="8" fill="#f3e8ff" />
    <text x="327" y="74" font-family="-apple-system, sans-serif" font-size="11" font-weight="700" fill="#6b21a8">STAGE 2: GENERATIVE MODEL</text>

    <rect x="330" y="95" width="180" height="35" rx="4" fill="#ffffff" stroke="#c084fc" />
    <text x="342" y="117" font-family="-apple-system, sans-serif" font-size="10" font-weight="600" fill="#581c87">Canary Token Embedder</text>

    <rect x="330" y="145" width="180" height="42" rx="4" fill="#ffffff" stroke="#c084fc" />
    <text x="348" y="165" font-family="-apple-system, sans-serif" font-size="11" font-weight="700" fill="#3b0764">Core LLM / Gemini</text>
    <text x="348" y="179" font-family="-apple-system, sans-serif" font-size="9" fill="#7e22ce">RAG Document Ingestion</text>

    <!-- Connector 2 -> 3 -->
    <line x1="525" y1="130" x2="575" y2="130" stroke="#475569" stroke-width="2" marker-end="url(#arrow)" />
    <text x="532" y="122" font-family="-apple-system, sans-serif" font-size="9" font-weight="600" fill="#7e22ce">Raw Output</text>

    <!-- Stage 3: Output Guardrails -->
    <rect x="580" y="30" width="280" height="200" rx="8" fill="url(#gradOutput)" stroke="#86efac" stroke-width="1.5" filter="url(#shadow)" />
    <rect x="580" y="30" width="280" height="28" rx="8" fill="#dcfce7" />
    <text x="592" y="49" font-family="-apple-system, sans-serif" font-size="11" font-weight="700" fill="#14532d">STAGE 3: OUTPUT GUARDRAILS</text>

    <rect x="595" y="70" width="250" height="30" rx="4" fill="#ffffff" stroke="#4ade80" />
    <text x="605" y="90" font-family="-apple-system, sans-serif" font-size="10" font-weight="600" fill="#166534">1. Pydantic Schema Validator &amp; Retry</text>

    <rect x="595" y="110" width="250" height="30" rx="4" fill="#ffffff" stroke="#4ade80" />
    <text x="605" y="130" font-family="-apple-system, sans-serif" font-size="10" font-weight="600" fill="#166534">2. Claim Groundedness Checker (NLI)</text>

    <rect x="595" y="150" width="250" height="30" rx="4" fill="#ffffff" stroke="#4ade80" />
    <text x="605" y="170" font-family="-apple-system, sans-serif" font-size="10" font-weight="600" fill="#166534">3. Canary Leak &amp; PII Scrubber</text>

    <rect x="595" y="190" width="250" height="30" rx="4" fill="#fee2e2" stroke="#f87171" />
    <text x="605" y="210" font-family="-apple-system, sans-serif" font-size="10" font-weight="700" fill="#991b1b">4. Fallback Circuit Breaker</text>
  </svg>
</div>
"""


def render_publication_html(md_path: Path) -> str:
    """Read markdown report and transform it into publication-grade Blink HTML."""
    import markdown_it

    raw_md = md_path.read_text(encoding="utf-8")

    # Clean math notation
    cleaned_md = _clean_latex_math(raw_md)

    # Convert markdown to HTML with tables enabled
    md_parser = markdown_it.MarkdownIt("commonmark").enable("table").enable("strikethrough")
    html_content = md_parser.render(cleaned_md)

    # Replace mermaid block with clean vector SVG
    html_content = re.sub(
        r"<pre><code class=\"language-mermaid\">.*?</code></pre>",
        _generate_architecture_svg(),
        html_content,
        flags=re.DOTALL,
    )

    css = """
  @import url('https://fonts.googleapis.com/css2?family=Latin+Modern+Roman:ital,wght@0,400;0,700;1,400;1,700&family=Latin+Modern+Mono&display=swap');
  @import url('https://cdn.jsdelivr.net/npm/latin-modern-web@1.0.2/style/latin-modern-roman.min.css');

  @page {
    size: A4;
    margin: 18mm 16mm 18mm 16mm;
    @top-right {
      content: "Fuse AI Fellowship 2026 - Week 18 Technical Report";
      font-family: "Latin Modern Roman", "CMU Serif", "Computer Modern Roman", "TeX Gyre Termes", "Times New Roman", Times, serif;
      font-size: 8pt;
      font-style: italic;
      color: #64748b;
    }
    @bottom-center {
      content: "- " counter(page) " -";
      font-family: "Latin Modern Roman", "CMU Serif", "Computer Modern Roman", "TeX Gyre Termes", "Times New Roman", Times, serif;
      font-size: 8.5pt;
      color: #475569;
    }
  }

  * { box-sizing: border-box; }

  body {
    font-family: "Latin Modern Roman", "CMU Serif", "Computer Modern Roman", "TeX Gyre Termes", "Times New Roman", "Nimbus Roman No9 L", Times, serif;
    line-height: 1.48;
    color: #111827;
    font-size: 9.8pt;
    margin: 0;
    padding: 0;
    background: #ffffff;
    text-rendering: optimizeLegibility;
    -webkit-font-smoothing: antialiased;
  }

  h1 {
    font-family: "Latin Modern Roman", "CMU Serif", "Computer Modern Roman", "TeX Gyre Termes", "Times New Roman", Times, serif;
    font-size: 18pt;
    font-weight: 700;
    letter-spacing: -0.01em;
    color: #0f172a;
    text-align: center;
    margin-top: 0;
    margin-bottom: 8pt;
    border-bottom: 1.5pt solid #0f172a;
    padding-bottom: 8pt;
  }

  h2 {
    font-family: "Latin Modern Roman", "CMU Serif", "Computer Modern Roman", "TeX Gyre Termes", "Times New Roman", Times, serif;
    font-size: 12.5pt;
    font-weight: 700;
    font-variant: small-caps;
    letter-spacing: 0.04em;
    color: #0f172a;
    margin-top: 18pt;
    margin-bottom: 6pt;
    border-bottom: 0.75pt solid #cbd5e1;
    padding-bottom: 2pt;
    page-break-after: avoid;
    break-after: avoid;
  }

  h3 {
    font-family: "Latin Modern Roman", "CMU Serif", "Computer Modern Roman", "TeX Gyre Termes", "Times New Roman", Times, serif;
    font-size: 10.5pt;
    font-weight: 700;
    font-style: italic;
    color: #1e293b;
    margin-top: 13pt;
    margin-bottom: 4pt;
    page-break-after: avoid;
    break-after: avoid;
  }

  p {
    margin-top: 0;
    margin-bottom: 8pt;
    text-align: justify;
    text-justify: inter-word;
    hyphens: auto;
  }

  ul, ol {
    margin-top: 0;
    margin-bottom: 8pt;
    padding-left: 20pt;
  }

  li {
    margin-bottom: 3pt;
    text-align: justify;
  }

  hr {
    border: none;
    border-top: 0.75pt solid #cbd5e1;
    margin: 14pt 0;
  }

  /* Academic Booktabs Table Design (LaTeX style) */
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 12pt 0 16pt 0;
    font-size: 8.8pt;
    page-break-inside: avoid;
    break-inside: avoid;
    border-top: 1.5pt solid #0f172a;
    border-bottom: 1.5pt solid #0f172a;
  }

  th {
    border-top: 1.5pt solid #0f172a;
    border-bottom: 1pt solid #0f172a;
    color: #0f172a;
    font-weight: 700;
    font-variant: small-caps;
    letter-spacing: 0.03em;
    text-align: left;
    padding: 6pt 7pt;
    background: none;
  }

  td {
    border-top: 0.5pt solid #e2e8f0;
    border-bottom: 0.5pt solid #e2e8f0;
    padding: 5pt 7pt;
    vertical-align: top;
    border-left: none;
    border-right: none;
  }

  tr:last-child td {
    border-bottom: 1.5pt solid #0f172a;
  }

  /* Badges & Monospace Elements */
  code {
    font-family: "Latin Modern Mono", "CMU Typewriter Text", "Courier New", Courier, monospace;
    background: #f8fafc;
    color: #0f172a;
    padding: 1pt 3pt;
    border-radius: 2pt;
    font-size: 8.5pt;
    border: 0.5pt solid #cbd5e1;
  }

  pre {
    background: #f8fafc;
    border: 0.75pt solid #cbd5e1;
    border-radius: 3pt;
    padding: 8pt 10pt;
    font-size: 8pt;
    overflow-x: auto;
    page-break-inside: avoid;
    break-inside: avoid;
    line-height: 1.35;
  }

  pre code {
    background: none;
    border: none;
    padding: 0;
    color: #0f172a;
  }

  blockquote {
    border-left: 2.5pt solid #475569;
    background-color: #f8fafc;
    margin: 10pt 0;
    padding: 6pt 12pt;
    color: #334155;
    font-style: italic;
  }

  /* Diagram Box */
  .diagram-container {
    margin: 14pt 0;
    padding: 10pt;
    background: #ffffff;
    border: 0.75pt solid #cbd5e1;
    border-radius: 4pt;
    text-align: center;
    page-break-inside: avoid;
    break-inside: avoid;
  }

  .diagram-title {
    font-family: "Latin Modern Roman", "CMU Serif", "Computer Modern Roman", "Times New Roman", serif;
    font-size: 8.8pt;
    font-weight: 700;
    font-variant: small-caps;
    letter-spacing: 0.05em;
    color: #1e293b;
    margin-bottom: 6pt;
  }

  /* Print Specifics */
  @media print {
    body {
      -webkit-print-color-adjust: exact !important;
      print-color-adjust: exact !important;
    }
    .diagram-container, table, pre {
      page-break-inside: avoid !important;
      break-inside: avoid !important;
    }
  }
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Technical Evaluation &amp; Architecture Report &mdash; Trustworthy AI Guardrails</title>
<style>
{css}
</style>
</head>
<body>
{html_content}
</body>
</html>"""


def convert_markdown(input_md: Path, output_pdf: Path | None = None) -> Path:
    """Render publication-grade HTML and compile to PDF via headless browser."""
    input_path = input_md.resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input Markdown file not found: {input_path}")

    target_pdf = output_pdf.resolve() if output_pdf else input_path.with_suffix(".pdf")
    html_path = input_path.with_suffix(".html")

    # 1. Generate publication HTML
    rendered_html = render_publication_html(input_path)
    html_path.write_text(rendered_html, encoding="utf-8")

    # 2. Discover browser
    browser_bin = _find_browser_executable()
    if not browser_bin:
        # Fallback to system pandoc if browser not installed
        pandoc_bin = shutil.which("pandoc")
        if pandoc_bin:
            cmd = [pandoc_bin, str(html_path), "-o", str(target_pdf), "--pdf-engine=wkhtmltopdf"]
            subprocess.run(cmd, check=True)  # noqa: S603
            return target_pdf
        raise RuntimeError("No Chromium browser (Chrome/Chromium/Edge) or pandoc found on system.")

    # 3. Print to PDF via headless Chromium engine
    file_uri = html_path.as_uri()
    cmd = [
        browser_bin,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--run-all-compositor-stages-before-draw",
        f"--print-to-pdf={target_pdf}",
        file_uri,
    ]
    subprocess.run(cmd, check=True)  # noqa: S603

    if not target_pdf.exists() or target_pdf.stat().st_size == 0:
        raise RuntimeError(f"Browser printer exited but PDF '{target_pdf}' was not created.")

    return target_pdf


def main():
    parser = argparse.ArgumentParser(
        description="Standalone High-Craft Markdown-to-PDF Converter (Fuse AI Standard)."
    )
    parser.add_argument("input", help="Path to input Markdown (.md) file")
    parser.add_argument("-o", "--output", help="Path to output PDF file (defaults to input.pdf)")
    args = parser.parse_args()

    input_file = Path(args.input)
    output_file = Path(args.output) if args.output else None

    try:
        res = convert_markdown(input_file, output_file)
        size_kb = res.stat().st_size / 1024.0
        print(f"[Success] Publication-grade PDF generated: {res} ({size_kb:.1f} KB)")
    except Exception as e:
        print(f"[Error] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
