"""Generate the styled HTML version of the AIMI value-propositions document.

Reads docs/AIMI_INTELLIGENCE_VALUE_PROPOSITIONS.md and renders a standalone
HTML page: dark/light theme toggle, embedded CSS, no external assets.

Shares the palette and theme-toggle contract with
``generate_system_doc_html.py`` so the documentation set renders as one set.
Extends that renderer with the constructs AVP-R1 uses and the system document
does not: blockquotes, heading anchors, an auto-built table of contents, nested
lists and fenced code with a language label.
"""
import re

SRC = r"C:\sita-platform\docs\AIMI_INTELLIGENCE_VALUE_PROPOSITIONS.md"
BLUE_SRC = r"C:\sita-platform\docs\BLUE_TEAM_CAPABILITY_ASSESSMENT.md"
OUT = r"C:\sita-platform\docs\AIMI_INTELLIGENCE_VALUE_PROPOSITIONS.html"

#: Verdict keywords rendered as a colour-coded badge inside a table cell.
BADGES = (
    ("strong win", "b-good"),
    ("strong need", "b-good"),
    ("real gap", "b-warn"),
    ("weak", "b-dim"),
    ("negative", "b-bad"),
    ("strongest win", "b-good"),
    ("do not integrate", "b-bad"),
    ("exclude", "b-bad"),
    ("take this area", "b-warn"),
)

#: Plain-English explanation for each proposition, surfaced in a modal.
#:
#: The markdown is the source of truth for the technical argument; this is the
#: non-technical restatement, for an audience that will not read Â§6. Keyed by the
#: AVP number exactly as it appears in the heading. ``main`` asserts that the key
#: set and the set of AVP headings in the markdown are identical in both
#: directions, so an added, removed or renamed proposition cannot silently lose
#: its explanation or keep a stale one.
LAYMAN = {
    # --- the five AI propositions -------------------------------------
    2: (
        "The part that genuinely needs AI",
        "There is a public catalogue of how real attackers break in, called MITRE ATT&amp;CK. The "
        "platform had never heard of it, so it could not tell you which methods appear in the data "
        "it receives or whether it would alert on any of them.",
        "Working out that gap is now done, and ordinary computing did it. "
        "<strong>What genuinely needs AI is writing the missing alert.</strong> Given a technique, "
        "someone has to decide which vendor source and which normalised field would show it, set "
        "the threshold, and write the rule in the form the platform's rule engine actually reads.",
        "Worth being clear about what this platform is: it does not scan and does not run "
        "security sensors. It receives findings from its vendors and alerts on them. So the rule "
        "is written against the records the platform holds - not against network traffic or host "
        "logs, which it never sees.",
    ),
    3: (
        "The part that genuinely needs AI",
        "Two identical critical problems score exactly the same: one unfixed for eighteen months "
        "with nobody attacking it, and one that appeared last week and is being actively "
        "exploited against South African government.",
        "Adding the field that holds the vulnerability identifier is a schema change. Looking up "
        "how much activity surrounds it is an ordinary lookup. Folding that into the risk score is "
        "arithmetic. <strong>None of that is AI.</strong>",
        "<strong>What genuinely needs AI is the judgement.</strong> Reading threat reporting and "
        "deciding whether a named campaign actually targets this sector, and whether its technique "
        "set matches what this estate is exposed to. That is interpretation, and it is the part "
        "that cannot be reduced to a lookup.",
    ),
    5: (
        "The part that genuinely needs AI",
        "Your monitoring tool spots someone breaking into records holding personal information. "
        "The law says you may have to notify the regulator when that happens.",
        "Gathering the evidence, assembling the packet and signing it is plumbing the platform "
        "already does. <strong>What genuinely needs AI is the legal judgement</strong>: deciding "
        "whether this particular compromise is serious enough to trigger the duty. That turns on "
        "what the data was, how sensitive the people are, and the circumstances - and no rule "
        "encodes it.",
        "The platform assembles the packet and stops. A named person decides whether to send it. "
        "<strong>It never sends anything to a regulator.</strong>",
    ),
    8: (
        "The part that genuinely needs AI",
        "Your dashboard shows a trend line. When it moves up, nothing says why - and that is the "
        "first question any executive asks.",
        "<strong>The arithmetic half is already built</strong> and needs no model: the platform "
        "stores each contributing signal separately, so it can tell you a rise of 6.4 points was 92 "
        "per cent one kind of problem on one application.",
        "<strong>What genuinely needs AI is the external explanation</strong> - which vulnerability, "
        "which campaign, and why that accounts for the movement the arithmetic already measured.",
    ),
    11: (
        "The part that genuinely needs AI",
        "The platform records every privileged action - who did what, when, under which role - and "
        "signs it so it cannot be altered. Nothing was reading those records.",
        "<strong>Every individual check is an ordinary query</strong>, and three are built and "
        "working: who acted without authority, which accounts hold conflicting roles, who exported "
        "more data than their role allows.",
        "<strong>What genuinely needs AI is reading across the rows</strong> - recognising that a "
        "particular ordering and timing of individually valid actions is not something any single "
        "check reveals.",
    ),
    # --- the seven demoted to engineering -----------------------------
    1: (
        "Demoted to engineering - and already built",
        "The platform showed a POPIA percentage that somebody typed in by hand, and its own code "
        "comments admitted it. That is now replaced by a real calculation.",
        "The part worth knowing: <strong>the machinery was already written and simply never "
        "switched on.</strong> The platform held a weighted model of the eight POPIA conditions and "
        "the function that adds them up. Nothing was calling it, which is exactly why the number "
        "was typed.",
        "The real score comes out near <strong>54</strong> against the claimed <strong>78</strong> - "
        "not a broken calculation, but four of eight conditions having nothing in the product that "
        "could evidence them. <strong>No AI involved.</strong> Engineering work, and done.",
    ),
    4: (
        "Demoted to engineering - and already built",
        "Four security vendors watch your estate and produce noticeably different pictures of it. "
        "Nobody could see the disagreements, because each vendor only sees its own slice.",
        "SITA sees all four at once, so SITA can ask which known endpoints have never triggered a "
        "block, which application has a database nobody is monitoring, and which applications only "
        "one vendor reports on.",
        "<strong>Ordinary database queries over data already held.</strong> Five of six checks are "
        "built and working. No AI, and describing it as AI would overstate it.",
    ),
    6: (
        "Demoted to engineering - and already built",
        "Every row carries six labels: which application, department, branch, ministry, cluster and "
        "vendor. Nobody had ever joined on them.",
        "Joining on them answers what nothing could: is one application claimed by two departments "
        "in two provinces, so nobody owns the fix? Which departments share applications, so a "
        "compromise reaches all of them?",
        "<strong>A single query pattern over columns that already exist</strong>, built and "
        "working. No vectors, no machine learning, nothing to buy.",
    ),
    7: (
        "Demoted to engineering - and already built",
        "The ranking that compares departments against each other was secure and correct, and no "
        "one could see it.",
        "It now adds the answer to \"so what do I do?\": the three departments above you all block "
        "a particular attack on a particular endpoint, you block none of it, and here are the "
        "attempts that got through.",
        "<strong>The comparison is the finding, not the wording.</strong> It is a set difference "
        "over data the platform already holds, and no peer's findings are read to produce it.",
    ),
    9: (
        "Demoted to engineering - and already built",
        "The security team had 551 alerts and nine fixed rules, with no way to know what it had not "
        "looked for.",
        "It now turns the coverage gaps into a to-do list: which attack methods the estate is "
        "exposed to with no alarm for, the exact query to run, what a positive result looks like, "
        "and how long it takes.",
        "<strong>Once the gap is known the hunt is a query plus a count the platform already "
        "computes.</strong> The mapping is curated and reviewed like any other config file.",
    ),
    10: (
        "Demoted to engineering - and already built",
        "No vendor tool grades itself. SITA sees all four and can compare them.",
        "It reports findings per vendor, how many sit unfixed past six months, and the interesting "
        "one: which applications each pair of vendors both report on. Overlap of forty out of nine "
        "hundred means they are looking at different estates.",
        "<strong>Counts and ratios over data already held</strong>, three of four measures built. The "
        "fourth would be a coverage percentage, which cannot be computed without a list of what you "
        "actually own.",
    ),
    12: (
        "Demoted to engineering - and already built",
        "The platform could produce one signed summary of its compliance position. That was all.",
        "It now builds a pack answering any audit question: who knew, when, what they did, what "
        "supports the claim it was fixed, and proof none of it was altered since.",
        "<strong>The signing, hashing and offline verification already existed</strong> for the "
        "Auditor-General attestation. A packet is those tools applied to a different set of "
        "records. There is nothing to generate.",
    ),
}
def slug(text: str, _seen: dict | None = None) -> str:
    """Anchor id for a heading, guaranteed unique within the document.

    Repeated sub-headings are common in a structured argument ("Why that is the
    wrong build" appears once per proposition). Without de-duplication they
    collapse onto one id, the TOC points at the wrong place, and two sections
    share a fragment link.
    """
    s = re.sub(r"<[^>]+>", "", text)
    s = re.sub(r"[^\w\s-]", "", s.lower())
    s = re.sub(r"[\s_]+", "-", s.strip()) or "section"
    if _seen is None:
        return s
    n = _seen.get(s, 0)
    _seen[s] = n + 1
    return s if n == 0 else f"{s}-{n}"


def inline(text: str) -> str:
    """Escape, then apply inline markdown. Code spans are protected first so
    that ** and * inside a code span are not treated as emphasis."""
    spans: list[str] = []

    def _hold(m: re.Match) -> str:
        spans.append(m.group(1))
        return f"\x00{len(spans) - 1}\x00"

    text = re.sub(r"`([^`]+)`", _hold, text)
    text = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", text)
    text = re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{spans[int(m.group(1))]}</code>", text)
    return text


def badge(cell_html: str) -> str:
    """Wrap a verdict keyword in a badge span. Matched on the plain text only,
    so a cell is never restyled on account of a word appearing inside a code
    span or a partial phrase."""
    plain = re.sub(r"<[^>]+>", "", cell_html).strip().lower().rstrip(".")
    for needle, cls in BADGES:
        if plain.startswith(needle):
            return f'<span class="badge {cls}">{cell_html}</span>'
    return cell_html


def parse_table(lines: list[str], i: int) -> tuple[str, int]:
    header = [c.strip() for c in lines[i].strip().strip("|").split("|")]
    i += 2  # skip separator row
    rows = []
    while i < len(lines) and lines[i].strip().startswith("|"):
        rows.append([badge(inline(c.strip())) for c in lines[i].strip().strip("|").split("|")])
        i += 1
    html = (
        "<table>\n<thead><tr>"
        + "".join(f"<th>{inline(h)}</th>" for h in header)
        + "</tr></thead>\n<tbody>\n"
    )
    for r in rows:
        html += "<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>\n"
    return html + "</tbody>\n</table>\n", i


def parse_quote(lines: list[str], i: int) -> tuple[str, int]:
    quoted: list[str] = []
    while i < len(lines) and lines[i].strip().startswith(">"):
        quoted.append(re.sub(r"^\s*>\s?", "", lines[i]).rstrip())
        i += 1
    inner = "\n".join(quoted).strip()
    # A quote that is itself a fenced block is rendered as a quoted code block.
    if inner.startswith("```"):
        body = inner.strip("`")
        return f"<blockquote><pre><code>{body}</code></pre></blockquote>\n", i
    return f"<blockquote>{inline(inner)}</blockquote>\n", i


def parse_list(lines: list[str], i: int) -> tuple[str, int]:
    ordered = bool(re.match(r"^\d+\.\s", lines[i].strip()))
    tag = "ol" if ordered else "ul"
    items: list[str] = []
    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()
        if not stripped:
            # A blank line ends the list unless the next line continues it.
            if i + 1 < len(lines) and re.match(r"^\s*(?:[-*]\s|\d+\.\s)", lines[i + 1]):
                i += 1
                continue
            break
        m = re.match(r"^(\s*)(?:[-*]\s+|\d+\.\s+)(.*)$", raw)
        if not m:
            break
        depth = len(m.group(1)) // 2
        items.append((depth, m.group(2)))
        i += 1
    out = [f"<{tag}>"]
    open_depth = 0
    for depth, text in items:
        while open_depth < depth:
            out.append("<ul>")
            open_depth += 1
        while open_depth > depth:
            out.append("</ul>")
            open_depth -= 1
        out.append(f"<li>{inline(text)}</li>")
    while open_depth > 0:
        out.append("</ul>")
        open_depth -= 1
    out.append(f"</{tag}>")
    return "\n".join(out) + "\n", i


def render(md: str) -> tuple[str, str, dict[int, str]]:
    lines = md.splitlines()
    out: list[str] = []
    headings: list[tuple[int, str, str]] = []
    seen: dict[int, str] = {}
    triggered: set[int] = set()
    first_h1_done = False
    slug_ids: dict[str, int] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            lang = stripped[3:].strip()
            code: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
                i += 1
            label = f'<span class="lang">{inline(lang)}</span>' if lang else ""
            out.append(f"<pre>{label}<code>" + "\n".join(code) + "</code></pre>\n")
            i += 1
            continue

        if not stripped:
            i += 1
            continue

        if stripped == "---":
            out.append("<hr/>\n")
            i += 1
            continue

        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            level = len(m.group(1))
            text = inline(m.group(2))
            sid = slug(m.group(2), slug_ids)
            # An AVP heading gets a plain-English trigger. The copy lives in
            # LAYMAN, not in the markdown, so this is the one place the two
            # representations meet and main() asserts they stay in step.
            # Only the detailed propositions (h3) carry a trigger â€” Part III's
            # h2 cross-references point at them and would otherwise duplicate
            # both the button and the heading id.
            avp = re.search(r"\bAVP-(\d+)\b", m.group(2)) if level == 3 else None
            # Only the first occurrence of each proposition carries a trigger.
            # Later sections cross-reference the propositions by number; a
            # trigger there would duplicate the button and compete with the
            # canonical one.
            if avp and int(avp.group(1)) in LAYMAN and int(avp.group(1)) not in triggered:
                n = int(avp.group(1))
                seen[n] = sid
                triggered.add(n)
                text += (
                    f'<button class="plain-btn" data-avp="{n}" '
                    f'aria-label="Explain AVP-{n} in plain English" '
                    f'title="Plain English">'
                    f'<span class="plain-q" aria-hidden="true">?</span>'
                    f"Plain English</button>"
                )
            out.append(f'<h{level} id="{sid}">{text}</h{level}>\n')
            # The first h1 is the document title and is rendered in the header.
            # Subsequent h1s (e.g. PART II) are section divisions and go into the TOC.
            if level == 1:
                if first_h1_done:
                    headings.append((level, m.group(2), sid))
                else:
                    first_h1_done = True
            elif level > 1:
                headings.append((level, m.group(2), sid))
            i += 1
            continue

        if stripped.startswith(">"):
            html, i = parse_quote(lines, i)
            out.append(html)
            continue

        if stripped.startswith("|"):
            html, i = parse_table(lines, i)
            out.append(html)
            continue

        if re.match(r"^\s*(?:[-*]\s|\d+\.\s)", line):
            html, i = parse_list(lines, i)
            out.append(html)
            continue

        out.append(f"<p>{inline(line)}</p>\n")
        i += 1

    toc: list[str] = ['<h2 id="contents">Contents</h2>', "<ul class='toc'>"]
    for level, text, sid in headings:
        toc.append(f'<li class="toc-l{level}"><a href="#{sid}">{inline(text)}</a></li>')
    toc.append("</ul>")
    return "\n".join(out), "\n".join(toc), seen


def build_modals(avp_slugs: dict[int, str]) -> str:
    out: list[str] = []
    for n in sorted(LAYMAN):
        title, *paras = LAYMAN[n]
        body = "".join(f"<p>{p}</p>" for p in paras)
        anchor = avp_slugs.get(n, "")
        src = (
            f'<a class="modal-src" href="#{anchor}">Read the full technical proposition &rarr;</a>'
            if anchor
            else ""
        )
        out.append(
            f'<div class="modal" id="modal-{n}" role="dialog" aria-modal="true" '
            f'aria-labelledby="modal-{n}-title" hidden>'
            f'<div class="modal-backdrop" data-close></div>'
            f'<div class="modal-card">'
            f'<div class="modal-head">'
            f'<span class="modal-tag">AVP-{n}</span>'
            f'<h2 class="modal-title" id="modal-{n}-title">{title}</h2>'
            f'<button class="modal-x" data-close aria-label="Close">&#10005;</button>'
            f"</div>"
            f'<div class="modal-body">{body}</div>'
            f'<div class="modal-foot">{src}</div>'
            f"</div>"
            f"</div>"
        )
    return "\n".join(out)


CSS = """
:root {
  --bg: #0d1117; --panel: #161b22; --border: #30363d; --text: #e6edf3;
  --muted: #8b949e; --accent: #f0883e; --amber: #f0c674; --blue: #79c0ff; --green: #7ee787;
  --code: #1f2937; --red: #ff7b72; --violet: #d2a8ff;
}
html[data-theme="light"] {
  --bg: #fafbfc; --panel: #ffffff; --border: #d0d7de; --text: #1f2328;
  --muted: #6e7781; --accent: #cf5c19; --amber: #7a5d00; --blue: #0969da; --green: #1a7f37;
  --code: #f6f8fa; --red: #cf222e; --violet: #8250df;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }
body {
  background: var(--bg); color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
  line-height: 1.65; padding: 2rem 1rem 4rem; max-width: 1040px; margin: 0 auto;
}
header {
  border-bottom: 1px solid var(--border); padding-bottom: 1rem; margin-bottom: 1.5rem;
  display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem;
}
header h1 { font-size: 1.6rem; color: var(--accent); line-height: 1.25; }
header .sub { color: var(--muted); font-size: 0.95rem; margin-top: 0.4rem; }
header .meta { color: var(--muted); font-size: 0.82rem; margin-top: 0.6rem; }
header .meta code { font-size: 0.95em; }
button {
  background: var(--panel); color: var(--amber); border: 1px solid var(--border);
  border-radius: 8px; padding: 0.45rem 0.8rem; cursor: pointer; font-weight: 700;
  white-space: nowrap;
}
button:hover { border-color: var(--accent); }
h1 { font-size: 1.55rem; color: var(--accent); margin: 1.8rem 0 0.6rem; }
h2 { font-size: 1.3rem; color: var(--accent); margin: 2rem 0 0.5rem;
     padding-top: 0.4rem; border-top: 1px solid var(--border); }
h3 { font-size: 1.08rem; color: var(--amber); margin: 1.4rem 0 0.4rem; }
h4 { font-size: 1rem; color: var(--violet); margin: 1.1rem 0 0.35rem; }
h2:first-of-type { border-top: none; }
p { margin: 0.55rem 0; }
ul, ol { margin: 0.5rem 0 0.6rem 1.5rem; }
li { margin: 0.28rem 0; }
li > ul, li > ol { margin: 0.2rem 0 0.2rem 0.2rem; }
strong { color: var(--amber); }
em { color: var(--violet); }
code {
  background: var(--code); border: 1px solid var(--border); border-radius: 5px;
  padding: 0.1rem 0.35rem; font-size: 0.86em; font-family: Consolas, monospace;
}
pre { background: var(--panel); border: 1px solid var(--border); border-radius: 8px;
      padding: 1rem; overflow-x: auto; margin: 0.8rem 0; position: relative; }
pre code { background: none; border: none; padding: 0; font-size: 0.84rem; }
pre .lang {
  position: absolute; top: 0.45rem; right: 0.6rem; color: var(--muted);
  font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.06em;
  font-family: -apple-system, sans-serif;
}
blockquote {
  margin: 0.8rem 0; padding: 0.7rem 1rem; border-left: 3px solid var(--accent);
  background: var(--panel); border-radius: 0 8px 8px 0; color: var(--text);
}
blockquote pre { background: var(--code); }
table { border-collapse: collapse; width: 100%; margin: 0.85rem 0; font-size: 0.9rem;
        display: block; overflow-x: auto; }
th, td { border: 1px solid var(--border); padding: 0.45rem 0.65rem;
         text-align: left; vertical-align: top; }
th { background: var(--panel); color: var(--amber); font-weight: 700; }
tr:nth-child(even) td { background: rgba(127,127,127,0.06); }
hr { border: none; border-top: 1px solid var(--border); margin: 2rem 0; }
a { color: var(--blue); }
.badge { display: inline-block; padding: 0.1rem 0.5rem; border-radius: 999px;
         font-size: 0.8rem; font-weight: 700; border: 1px solid; }
.badge strong { color: inherit; }
.b-good  { color: var(--green); border-color: var(--green);
           background: rgba(46,160,67,0.12); }
.b-warn  { color: var(--amber); border-color: var(--amber);
           background: rgba(240,198,116,0.12); }
.b-bad   { color: var(--red); border-color: var(--red);
           background: rgba(248,81,73,0.12); }
.b-dim   { color: var(--muted); border-color: var(--muted);
           background: rgba(139,148,158,0.12); }
ul.toc { list-style: none; margin-left: 0; columns: 2; column-gap: 2rem; }
ul.toc li { margin: 0.15rem 0; break-inside: avoid; }
ul.toc .toc-l1 { font-weight: 800; color: var(--accent); margin-top: 0.8rem; font-size: 0.95rem; border-bottom: 1px solid var(--border); padding-bottom: 0.2rem; }
ul.toc .toc-l2 { font-weight: 600; color: var(--text); font-size: 0.9rem; }
ul.toc .toc-l3 { padding-left: 0.9rem; font-size: 0.86rem; }
ul.toc .toc-l4 { padding-left: 1.6rem; font-size: 0.82rem; color: var(--muted); }

/* --- Plain English trigger on each AVP heading --- */
.plain-btn {
  display: inline-flex; align-items: center; gap: 0.35rem;
  margin-left: 0.6rem; padding: 0.1rem 0.6rem 0.15rem;
  background: transparent; color: var(--blue);
  border: 1px solid var(--blue); border-radius: 999px;
  font-size: 0.62rem; font-weight: 700; letter-spacing: 0.05em;
  text-transform: uppercase; vertical-align: middle;
  cursor: pointer; white-space: nowrap; transition: background 0.12s, color 0.12s;
}
.plain-btn:hover, .plain-btn:focus-visible { background: var(--blue); color: var(--bg); }
.plain-q {
  display: inline-flex; align-items: center; justify-content: center;
  width: 0.95rem; height: 0.95rem; border-radius: 50%;
  border: 1px solid currentColor; font-size: 0.6rem; line-height: 1;
}

/* --- Modal --- */
.modal { position: fixed; inset: 0; z-index: 100; display: flex;
         align-items: center; justify-content: center; padding: 1.25rem; }
.modal[hidden] { display: none; }
.modal-backdrop { position: absolute; inset: 0; background: rgba(1, 4, 9, 0.72);
                  backdrop-filter: blur(2px); }
.modal-card {
  position: relative; width: min(660px, 100%); max-height: 84vh; overflow-y: auto;
  background: var(--panel); border: 1px solid var(--border); border-radius: 12px;
  box-shadow: 0 18px 48px rgba(0, 0, 0, 0.45); padding: 1.4rem 1.5rem;
}
.modal-head { display: flex; align-items: flex-start; gap: 0.7rem;
              padding-bottom: 0.85rem; margin-bottom: 0.9rem;
              border-bottom: 1px solid var(--border); }
.modal-tag { flex: none; margin-top: 0.15rem; padding: 0.15rem 0.5rem;
             border: 1px solid var(--accent); border-radius: 999px;
             color: var(--accent); font-size: 0.68rem; font-weight: 700;
             letter-spacing: 0.05em; }
.modal-title { flex: 1; font-size: 1.15rem; color: var(--accent);
               margin: 0; border: none; padding: 0; line-height: 1.3; }
.modal-x { flex: none; background: none; border: 1px solid var(--border);
           border-radius: 8px; color: var(--muted); cursor: pointer;
           padding: 0.25rem 0.5rem; font-size: 0.75rem; line-height: 1; }
.modal-x:hover { border-color: var(--red); color: var(--red); }
.modal-body p { margin: 0 0 0.75rem; line-height: 1.7; }
.modal-body p:last-child { margin-bottom: 0; }
.modal-foot { margin-top: 1.1rem; padding-top: 0.85rem;
              border-top: 1px solid var(--border); }
.modal-src { font-size: 0.85rem; font-weight: 700; text-decoration: none; }
.modal-src:hover { text-decoration: underline; }
body.modal-open { overflow: hidden; }
footer { border-top: 1px solid var(--border); margin-top: 2.5rem; padding-top: 1rem;
         color: var(--muted); font-size: 0.85rem; }
@media (max-width: 760px) {
  body { padding: 1rem 0.75rem 3rem; }
  header { flex-direction: column; }
  ul.toc { columns: 1; }
}
@media print {
  button, pre .lang { display: none; }
  body { max-width: none; padding: 0; }
  h2 { page-break-after: avoid; }
  table, pre, blockquote { page-break-inside: avoid; }
}
"""

JS = """
(function () {
  var root = document.documentElement;
  try {
    var saved = localStorage.getItem('sita-doc-theme');
    if (saved) root.setAttribute('data-theme', saved);
  } catch (e) {}
  var btn = document.getElementById('themeToggle');
  btn.addEventListener('click', function () {
    var next = root.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
    root.setAttribute('data-theme', next);
    try { localStorage.setItem('sita-doc-theme', next); } catch (e) {}
  });

  // Plain English modals
  var lastFocus = null;

  function open(n, trigger) {
    var m = document.getElementById('modal-' + n);
    if (!m) return;
    lastFocus = trigger || null;
    m.hidden = false;
    document.body.classList.add('modal-open');
    var x = m.querySelector('.modal-x');
    if (x) x.focus();
  }

  function close(m) {
    if (!m) return;
    m.hidden = true;
    document.body.classList.remove('modal-open');
    if (lastFocus) { lastFocus.focus(); lastFocus = null; }
  }

  document.addEventListener('click', function (e) {
    var trigger = e.target.closest('.plain-btn');
    if (trigger) { open(trigger.getAttribute('data-avp'), trigger); return; }
    if (e.target.closest('.modal [data-close]')) {
      close(e.target.closest('.modal'));
    }
  });

  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    var open_ = document.querySelector('.modal:not([hidden])');
    if (open_) close(open_);
  });
})();
"""


def main() -> None:
    with open(SRC, encoding="utf-8") as f:
        md = f.read()

    try:
        with open(BLUE_SRC, encoding="utf-8") as bf:
            blue_content = bf.read()
            # Extract from PART II onwards if present, or entire content
            part_ii_match = re.search(r"(# PART II\b[\s\S]*)", blue_content)
            if part_ii_match:
                blue_md = part_ii_match.group(1)
            else:
                blue_md = blue_content.strip()
            md = md.rstrip() + "\n\n---\n\n" + blue_md
    except FileNotFoundError:
        pass

    body, toc, avp_slugs = render(md)

    # The markdown and LAYMAN must describe the same set of propositions.
    # Silently dropping either one would ship a document with an untriggered
    # modal or a trigger with no explanation, so this fails the build instead.
    missing = sorted(set(avp_slugs) ^ set(LAYMAN))
    if missing:
        raise SystemExit(
            "LAYMAN is out of step with the markdown. "
            f"AVP {missing} present in one source and not the other. "
            "Add or remove the LAYMAN entry to match."
        )

    html = f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SITA x AIMI â€” Novel AI Value Propositions</title>
<style>{CSS}</style>
</head>
<body>
<header>
  <div>
    <h1>SITA &times; AIMI â€” Novel AI Value Propositions</h1>
    <div class="sub">Twelve value propositions beyond current reporting and beyond the committed
      AI programme, plus an assessment of the proposed blue-team AI capability set</div>
    <div class="meta">AVP-R1 &middot; prepared 12 October 2026 &middot; baseline
      <code>eca4852</code> &middot; status: proposal, no code committed</div>
  </div>
  <button id="themeToggle" title="Toggle dark / light mode">&#127769; Theme</button>
</header>
{toc}
{body}
{build_modals(avp_slugs)}
<footer>AVP-R1 &middot; rendered from
  <a href="AIMI_INTELLIGENCE_VALUE_PROPOSITIONS.md">AIMI_INTELLIGENCE_VALUE_PROPOSITIONS.md</a>
  &middot; companion to <a href="AI_INTEGRATION_PLAN_MASTER.html">the master AI integration plan</a>
  &middot; findings marked &ldquo;probed live&rdquo; were verified by direct MCP call on 12 October 2026</footer>
<script>{JS}</script>
</body>
</html>
"""
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"saved: {OUT} ({len(html):,} bytes) Â· {len(LAYMAN)} plain-English modals")


if __name__ == "__main__":
    main()
