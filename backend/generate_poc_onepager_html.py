"""Generate a styled, self-contained HTML one-pager for the executive POC.

Source of truth is docs/POC_ONE_PAGER.md. The markdown -> HTML
rendering is reused from generate_system_doc_html so both documents stay
consistent; only the page chrome and CSS differ (executive one-pager layout,
A4 print rules).
"""
import re

from generate_system_doc_html import render  # reuse the shared renderer

SRC = r"C:\sita-platform\docs\POC_ONE_PAGER.md"
OUT = r"C:\sita-platform\POC_ONE_PAGER.html"

CSS = """
:root {
  --bg: #0d1117; --panel: #161b22; --border: #30363d; --text: #e6edf3;
  --muted: #8b949e; --accent: #f0883e; --amber: #f0c674; --blue: #79c0ff;
  --green: #7ee787; --red: #ff7b72; --code: #1f2937;
}
html[data-theme="light"] {
  --bg: #fafbfc; --panel: #ffffff; --border: #d0d7de; --text: #1f2328;
  --muted: #6e7781; --accent: #cf5c19; --amber: #7a5d00; --blue: #0969da;
  --green: #1a7f37; --red: #cf222e; --code: #f6f8fa;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--bg); color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
  line-height: 1.6; padding: 2rem 1.25rem 3rem; max-width: 900px; margin: 0 auto;
}
header.doc {
  border-bottom: 2px solid var(--accent); padding-bottom: 0.9rem; margin-bottom: 1.4rem;
  display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem;
}
header.doc h1 { font-size: 1.55rem; color: var(--accent); line-height: 1.2; }
header.doc .sub { color: var(--text); font-size: 1rem; margin-top: 0.35rem; font-weight: 600; }
header.doc .meta { color: var(--muted); font-size: 0.8rem; margin-top: 0.35rem; }
button {
  background: var(--panel); color: var(--amber); border: 1px solid var(--border);
  border-radius: 8px; padding: 0.45rem 0.8rem; cursor: pointer; font-weight: 700;
  white-space: nowrap;
}
button:hover { border-color: var(--accent); }
h1 { font-size: 1.15rem; color: var(--muted); font-weight: 700; margin: 0 0 0.8rem;
     text-transform: uppercase; letter-spacing: 0.06em; }
h2 { font-size: 1.3rem; color: var(--accent); margin: 1.7rem 0 0.5rem;
     padding-bottom: 0.3rem; border-bottom: 1px solid var(--border); }
h3 { font-size: 1.05rem; color: var(--red); margin: 1.3rem 0 0.4rem; }
p { margin: 0.5rem 0; }
ul, ol { margin: 0.5rem 0 0.5rem 1.3rem; }
li { margin: 0.3rem 0; }
strong { color: var(--amber); }
code {
  background: var(--code); border: 1px solid var(--border); border-radius: 5px;
  padding: 0.1rem 0.32rem; font-size: 0.86em; font-family: Consolas, monospace;
  color: var(--blue);
}
em { color: var(--muted); }
table { border-collapse: collapse; width: 100%; margin: 0.7rem 0 1rem; font-size: 0.9rem; }
th, td { border: 1px solid var(--border); padding: 0.45rem 0.6rem; text-align: left; vertical-align: top; }
th { background: var(--panel); color: var(--amber); }
tr:nth-child(even) td { background: rgba(127,127,127,0.06); }
hr { border: none; border-top: 1px solid var(--border); margin: 1.6rem 0; }
a { color: var(--blue); }

/* Callout for the risk-calibration warning */
.callout {
  border: 1px solid var(--accent); border-left-width: 4px; border-radius: 8px;
  background: rgba(240,136,62,0.08); padding: 0.9rem 1.1rem; margin: 0.9rem 0;
}
.callout p { margin: 0.4rem 0; }
.callout.verdict strong { color: var(--accent); }

footer {
  border-top: 1px solid var(--border); margin-top: 2.2rem; padding-top: 0.9rem;
  color: var(--muted); font-size: 0.82rem;
}
@media print {
  button { display: none; }
  body { max-width: none; padding: 0; font-size: 10pt; }
  h2 { break-after: avoid; }
  table, .callout { break-inside: avoid; }
  @page { size: A4; margin: 14mm; }
}
"""

JS = """
document.getElementById('themeToggle').addEventListener('click', () => {
  const root = document.documentElement;
  root.dataset.theme = root.dataset.theme === 'light' ? 'dark' : 'light';
  try { localStorage.setItem('poc_theme', root.dataset.theme); } catch (e) {}
});
try {
  const saved = localStorage.getItem('poc_theme');
  if (saved) document.documentElement.dataset.theme = saved;
} catch (e) {}
"""


def main():
    md = open(SRC, encoding="utf-8").read()

    # The page header already carries the title and tagline; drop both from
    # the body so they are not rendered twice.
    md = re.sub(r"^#\s+.*\n", "", md, count=1)
    md = re.sub(r"^\s*\*\*.+\*\*\s*$\n", "", md, count=1, flags=re.M)

    body = render(md)

    # Wrap the closing statement in a visual callout. Targeted structurally
    # at the final paragraph so it cannot drift when the prose is edited.
    last_p = body.rfind("<p>")
    last_close = body.rfind("</p>")
    if last_p != -1 and last_close > last_p:
        body = (
            body[:last_p]
            + '<div class="callout verdict">'
            + body[last_p : last_close + 4]
            + "</div>"
            + body[last_close + 4 :]
        )

    html = f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SITA Consolidated Security Reporting &mdash; Executive Overview</title>
<style>{CSS}</style>
</head>
<body>
<header class="doc">
  <div>
    <h1>SITA Consolidated Security Reporting</h1>
    <div class="sub">One national security picture &mdash; four vendor consoles, one login</div>
    <div class="meta">Prepared for executive sponsorship &amp; pilot approval &middot; Designated pilot: Department of Home Affairs (8 DDG branches)</div>
  </div>
  <button id="themeToggle" title="Toggle dark / light mode">&#127769; Theme</button>
</header>
{body}
<footer>All figures verified live against the running platform &middot;
generated from <code>docs/POC_ONE_PAGER.md</code> &middot;
<a href="POC_ONE_PAGER.docx">Download Word version</a></footer>
<script>{JS}</script>
</body>
</html>
"""
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print("saved:", OUT, f"({len(html):,} bytes)")


if __name__ == "__main__":
    main()
