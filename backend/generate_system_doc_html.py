"""Generate a styled, self-contained HTML version of the system documentation.

Reads docs/SITA_Platform_System_Documentation.md and renders a standalone
HTML page (dark/light theme toggle, embedded CSS, no external assets) so it
can be shared with stakeholders or opened directly in a browser.
"""
import re

SRC = r"C:\sita-platform\docs\SITA_Platform_System_Documentation.md"
OUT = r"C:\sita-platform\docs\SITA_Platform_System_Documentation.html"


def inline(text: str) -> str:
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def parse_table(lines: list[str], i: int) -> tuple[str, int]:
    header = [c.strip() for c in lines[i].strip().strip("|").split("|")]
    i += 2  # skip separator row
    rows = []
    while i < len(lines) and lines[i].strip().startswith("|"):
        rows.append([inline(c.strip()) for c in lines[i].strip().strip("|").split("|")])
        i += 1
    html = '<table>\n<thead><tr>' + "".join(f"<th>{inline(h)}</th>" for h in header) + "</tr></thead>\n<tbody>\n"
    for r in rows:
        html += "<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>\n"
    return html + "</tbody>\n</table>\n", i


def render(md: str) -> str:
    lines = md.splitlines()
    out: list[str] = []
    i = 0
    in_code = False
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("```"):
            code: list[str] = []
            in_code = not in_code
            i += 1
            if not in_code:
                continue
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
                i += 1
            out.append("<pre><code>" + "\n".join(code) + "</code></pre>\n")
            i += 1
            continue
        if not line.strip():
            i += 1
            continue
        if line.strip() == "---":
            out.append("<hr/>\n")
            i += 1
            continue
        if line.startswith("# "):
            out.append(f"<h1>{inline(line[2:])}</h1>\n")
            i += 1
            continue
        if line.startswith("## "):
            out.append(f"<h2>{inline(line[3:])}</h2>\n")
            i += 1
            continue
        if line.startswith("### "):
            out.append(f"<h3>{inline(line[4:])}</h3>\n")
            i += 1
            continue
        if line.strip().startswith("|"):
            tbl, i = parse_table(lines, i)
            out.append(tbl)
            continue
        if line.strip().startswith("- ") or line.strip().startswith("* "):
            items: list[str] = []
            while i < len(lines) and (lines[i].strip().startswith("- ") or lines[i].strip().startswith("* ")):
                items.append("<li>" + inline(lines[i].strip()[2:]) + "</li>")
                i += 1
            out.append("<ul>\n" + "\n".join(items) + "\n</ul>\n")
            continue
        if re.match(r"^\d+\.\s", line.strip()):
            items = []
            while i < len(lines) and re.match(r"^\d+\.\s", lines[i].strip()):
                items.append("<li>" + inline(re.sub(r"^\d+\.\s", "", lines[i].strip())) + "</li>")
                i += 1
            out.append("<ol>\n" + "\n".join(items) + "\n</ol>\n")
            continue
        out.append(f"<p>{inline(line)}</p>\n")
        i += 1
    return "\n".join(out)


CSS = """
:root {
  --bg: #0d1117; --panel: #161b22; --border: #30363d; --text: #e6edf3;
  --muted: #8b949e; --accent: #f0883e; --amber: #f0c674; --blue: #79c0ff; --green: #7ee787;
  --code: #1f2937;
}
html[data-theme="light"] {
  --bg: #fafbfc; --panel: #ffffff; --border: #d0d7de; --text: #1f2328;
  --muted: #6e7781; --accent: #cf5c19; --amber: #7a5d00; --blue: #0969da; --green: #1a7f37;
  --code: #f6f8fa;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--bg); color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
  line-height: 1.65; padding: 2rem 1rem; max-width: 980px; margin: 0 auto;
}
header {
  border-bottom: 1px solid var(--border); padding-bottom: 1rem; margin-bottom: 1.5rem;
  display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem;
}
header h1 { font-size: 1.6rem; color: var(--accent); }
header .sub { color: var(--muted); font-size: 0.95rem; margin-top: 0.25rem; }
button {
  background: var(--panel); color: var(--amber); border: 1px solid var(--border);
  border-radius: 8px; padding: 0.45rem 0.8rem; cursor: pointer; font-weight: 700;
  white-space: nowrap;
}
button:hover { border-color: var(--accent); }
h1 { font-size: 1.5rem; color: var(--accent); margin: 1.6rem 0 0.6rem; }
h2 { font-size: 1.25rem; color: var(--accent); margin: 1.5rem 0 0.5rem; }
h3 { font-size: 1.05rem; color: var(--amber); margin: 1.2rem 0 0.4rem; }
p { margin: 0.5rem 0; }
ul, ol { margin: 0.5rem 0 0.5rem 1.4rem; }
li { margin: 0.25rem 0; }
strong { color: var(--amber); }
code {
  background: var(--code); border: 1px solid var(--border); border-radius: 5px;
  padding: 0.1rem 0.35rem; font-size: 0.85em; font-family: Consolas, monospace;
}
pre { background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: 1rem; overflow-x: auto; margin: 0.75rem 0; }
pre code { background: none; border: none; padding: 0; }
table { border-collapse: collapse; width: 100%; margin: 0.75rem 0; font-size: 0.92rem; }
th, td { border: 1px solid var(--border); padding: 0.45rem 0.65rem; text-align: left; vertical-align: top; }
th { background: var(--panel); color: var(--amber); }
tr:nth-child(even) td { background: rgba(127,127,127,0.06); }
hr { border: none; border-top: 1px solid var(--border); margin: 1.5rem 0; }
a { color: var(--blue); }
footer { border-top: 1px solid var(--border); margin-top: 2.5rem; padding-top: 1rem; color: var(--muted); font-size: 0.85rem; }
@media print { button { display: none; } }
"""

JS = """
document.getElementById('themeToggle').addEventListener('click', () => {
  const root = document.documentElement;
  const next = root.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
  root.setAttribute('data-theme', next);
  try { localStorage.setItem('sita-doc-theme', next); } catch (e) {}
});
"""


def main():
    with open(SRC, encoding="utf-8") as f:
        md = f.read()
    body = render(md)
    html = f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SITA Consolidated Security Reporting — System Documentation</title>
<style>{CSS}</style>
</head>
<body>
<header>
  <div>
    <h1>SITA Consolidated Security Reporting — System Documentation</h1>
    <div class="sub">Full technical documentation · architecture, tenancy, API, infrastructure &amp; operations</div>
  </div>
  <button id="themeToggle" title="Toggle dark / light mode">&#127769; Theme</button>
</header>
{body}
<footer>Generated from the repository documentation set · <a href="SITA_Platform_System_Documentation.docx">Download Word version</a></footer>
<script>{JS}</script>
</body>
</html>
"""
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print("saved:", OUT, f"({len(html):,} bytes)")


if __name__ == "__main__":
    main()
