"""Renders an explain-doc map file into one HTML page for the Artifact tool.

Usage: python3 render_page.py <map.json> > page.html
       python3 render_page.py --text <map.json> > page.txt   (plain text, for the cold read)
"""
import html
import json
import re
import sys

CSS = """
:root{--bg:#f6f7f9;--panel:#fff;--fg:#1d2430;--muted:#5b6575;--line:#dde1e8;--accent:#2f5d8a;--accent-soft:#e6eef7;
--warn:#9a6400;--warn-bg:#fbf0d9;--tip-bg:#1d2430;--tip-fg:#f6f7f9;--code-bg:#eef1f5;
--display:"IBM Plex Sans Condensed","Arial Narrow",system-ui,sans-serif;--body:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;--mono:"IBM Plex Mono",ui-monospace,Menlo,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#12161c;--panel:#1a2029;--fg:#e4e8ee;--muted:#98a2b3;--line:#2b3340;--accent:#8db8e3;--accent-soft:#1f2c3b;--warn:#f0c063;--warn-bg:#3a2e14;--tip-bg:#e4e8ee;--tip-fg:#12161c;--code-bg:#232b36;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#12161c;--panel:#1a2029;--fg:#e4e8ee;--muted:#98a2b3;--line:#2b3340;--accent:#8db8e3;--accent-soft:#1f2c3b;--warn:#f0c063;--warn-bg:#3a2e14;--tip-bg:#e4e8ee;--tip-fg:#12161c;--code-bg:#232b36;color-scheme:dark}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--fg);font:15px/1.55 var(--body)}
.wrap{max-width:900px;margin:0 auto;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:28px 64px}
h1,h2,h3{font-family:var(--display);font-weight:600;text-wrap:balance;margin:0}
h1{font-size:30px}h2{font-size:22px;margin-top:40px}h3{font-size:17px}
p{margin:0}
.lede{color:var(--muted);max-width:70ch;margin-top:8px}
.big{max-width:70ch;margin-top:10px;font-size:16px}
.example{max-width:70ch;margin-top:12px;background:var(--accent-soft);border-radius:6px;padding:12px 14px}
.stages{list-style:none;margin:14px 0 0;padding:0}
.stage{display:grid;grid-template-columns:36px 1fr;gap:14px;position:relative;padding-bottom:22px}
.stage:not(:last-child)::before{content:"";position:absolute;left:17px;top:36px;bottom:0;width:2px;background:var(--line)}
.n{width:36px;height:36px;border-radius:50%;background:var(--accent);color:var(--bg);font:600 16px var(--display);display:grid;place-items:center}
.sb{min-width:0;display:grid;gap:6px;padding-top:5px}
.cap{font-size:13px;color:var(--muted);margin-top:8px}
.tbl{overflow-x:auto;margin-top:8px}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{text-align:left;vertical-align:top;padding:7px 9px;border-bottom:1px solid var(--line)}
th{font-weight:600;color:var(--muted);font-size:13px}
.strip{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin-top:12px}
.st{border:1.5px solid var(--accent);border-radius:6px;padding:6px 14px;font-weight:600}
.ar{color:var(--muted)}
.sec{border-top:1px solid var(--line);padding:14px 0;display:grid;gap:6px}
.sh{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}
.ln{font:500 12px var(--mono);background:var(--accent-soft);color:var(--accent);padding:2px 7px;border-radius:4px;white-space:nowrap}
ul,ol{margin:2px 0 0;padding-left:20px;display:grid;gap:4px}
.wrong li{padding-left:2px}
.lab{font:500 11px var(--mono);color:var(--muted);border:1px solid var(--line);border-radius:3px;padding:0 4px;margin-left:6px;white-space:nowrap}
.legend{columns:2 300px;column-gap:28px;margin-top:10px}
.legend div{break-inside:avoid;padding:5px 0;border-bottom:1px solid var(--line);font-size:14px}
code{font:13px var(--mono);background:var(--code-bg);padding:1px 4px;border-radius:3px;overflow-wrap:anywhere}
.tip{border-bottom:1px dotted var(--accent);cursor:help;position:relative}
.tip:hover::after,.tip:focus::after{content:attr(data-tip);position:absolute;left:0;top:calc(100% + 6px);z-index:20;width:max-content;max-width:min(280px,80vw);background:var(--tip-bg);color:var(--tip-fg);font:400 13px/1.4 var(--body);padding:7px 9px;border-radius:5px}
.tip:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.src{font-size:13px;color:var(--muted);margin-top:6px}
.src a{color:var(--accent)}
.status{max-width:70ch;margin-top:12px;border-left:3px solid var(--warn);background:var(--warn-bg);padding:8px 12px;border-radius:0 6px 6px 0}
"""

FONTS = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Sans+Condensed:wght@600&family=IBM+Plex+Mono:wght@400;500&display=swap">'


class Rich:
    """Escapes prose and puts a hover definition on the first use of each legend term in a block."""

    def __init__(self, legend, text=False):
        self.text = text
        self.page_seen = set()
        self.legend = {k.lower(): v for k, v in legend.items()}
        keys = sorted(legend, key=len, reverse=True)
        alt = "|".join(re.escape(k) for k in keys)
        self.rx = re.compile(r"(`[^`]+`)" + (r"|(?<![\w-])((" + alt + r")(?:s|es|d|ed|ing)?)(?![\w-])" if keys else ""), re.I)

    def __call__(self, text, seen=None):
        seen = self.page_seen if self.text else (set() if seen is None else seen)
        esc = (lambda s: s) if self.text else html.escape
        out, last = [], 0
        for m in self.rx.finditer(text or ""):
            out.append(esc(text[last:m.start()]))
            if m.group(1):
                out.append(m.group(1) if self.text else "<code>" + html.escape(m.group(1)[1:-1]) + "</code>")
            else:
                w, key = m.group(2), m.group(3).lower()
                if key in seen:
                    out.append(esc(w))
                else:
                    seen.add(key)
                    tip = html.escape(self.legend[key])
                    out.append(f'[{w}: {self.legend[key]}]' if self.text else f'<span class="tip" tabindex="0" data-tip="{tip}">{html.escape(w)}</span>')
            last = m.end()
        out.append(esc((text or "")[last:]))
        return "".join(out)


def table(t, r):
    head = "".join(f"<th>{html.escape(h)}</th>" for h in t["head"])
    rows = "".join("<tr>" + "".join(f"<td>{r(c)}</td>" for c in row) + "</tr>" for row in t.get("rows", []))
    return f'<div class="tbl"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'


def render(m):
    r = Rich(m.get("legend", {}))
    src = m.get("source", {})
    src_text = " ".join(x for x in [src.get("path", ""), src.get("version", "")] if x)
    src_html = html.escape(src_text)
    if src.get("link"):
        src_html = f'<a href="{html.escape(src["link"])}" target="_blank" rel="noopener">{src_html or "source"}</a>'
    o = [f"<title>{html.escape(m['title'])}</title>", '<meta name="claude:viewport-fit-sides" content="cover">', FONTS, f"<style>{CSS}</style>", '<div class="wrap">']
    o.append(f"<h1>{html.escape(m['title'])}</h1><p class=\"src\">Explained from {src_html}. Dotted words show a definition on hover or tap.</p>")
    if m.get("status"):
        o.append(f'<p class="status"><b>Status today.</b> {r(m["status"])}</p>')
    o.append("<h2>Big picture</h2>")
    if m.get("example"):
        o.append(f'<p class="example">{r(m["example"])}</p>')
    o.append(f'<p class="big">{r(m["big_picture"])}</p>')

    if m.get("decisions"):
        o.append('<h2>What a reviewer has to decide</h2>')
        rows = [[d["question"], d.get("why", ""), d["lines"]] for d in m["decisions"]]
        o.append(table({"head": ["Decision", "Why it matters", "Lines"], "rows": rows}, r))

    f = m["flow"]
    o.append(f"<h2>{html.escape(f.get('title', 'How it works'))}</h2>")
    if f.get("intro"):
        o.append(f'<p class="lede">{r(f["intro"])}</p>')
    o.append('<ol class="stages">')
    for i, s in enumerate(f["stages"], 1):
        seen = set()
        body = f"<h3>{html.escape(s['name'])}</h3><p>{r(s['text'], seen)}</p>"
        if s.get("table"):
            body += table(s["table"], lambda c: r(c, seen))
        if s.get("note"):
            body += f'<p class="cap">{r(s["note"], seen)}</p>'
        o.append(f'<li class="stage"><div class="n">{i}</div><div class="sb">{body}</div></li>')
    o.append("</ol>")
    if f.get("source_lines"):
        o.append(f'<p class="cap">Source lines {html.escape(f["source_lines"])}.</p>')

    states = m.get("states") or []
    for s in states if isinstance(states, list) else [states]:
        strip = '<span class="ar">&rarr;</span>'.join(f'<span class="st">{html.escape(n)}</span>' for n in s["names"])
        o.append(f'<h2>{html.escape(s.get("title", "States"))}</h2><div class="strip">{strip}</div>')
        o.append(table({"head": ["Change", "Who or what does it"], "rows": s.get("rows", [])}, r))
        if s.get("note"):
            o.append(f'<p class="cap">{r(s["note"])}</p>')

    o.append("<h2>Each section</h2>")
    for s in m["sections"]:
        seen = set()
        pts = "".join(f"<li>{r(p, seen)}</li>" for p in s.get("points", []))
        where = f'lines {s["lines"]}' if s.get("lines") else ", ".join(s.get("files", []))
        o.append(f'<div class="sec"><div class="sh"><h3>{html.escape(s["name"])}</h3><span class="ln">{html.escape(where)}</span></div><p>{r(s["summary"], seen)}</p>{"<ul>" + pts + "</ul>" if pts else ""}</div>')

    for t in m.get("tables", []):
        o.append(f"<h2>{html.escape(t['title'])}</h2>")
        if t.get("intro"):
            o.append(f'<p class="lede">{r(t["intro"])}</p>')
        o.append(table(t, r))

    if m.get("wrong"):
        o.append('<h2>Looked wrong while reading</h2><ol class="wrong">')
        for w in m["wrong"]:
            o.append(f'<li>{r(w["text"])} <span class="ln">{html.escape("lines " + str(w["lines"]) if w.get("lines") else ", ".join(w.get("files", [])))}</span><span class="lab">{html.escape(w["label"])}</span></li>')
        o.append("</ol>")

    leg = "".join(f"<div><b>{html.escape(k)}</b>. {html.escape(v)}</div>" for k, v in sorted(m["legend"].items(), key=lambda kv: kv[0].lower()))
    o.append(f'<h2>Legend</h2><div class="legend">{leg}</div></div>')
    return "\n".join(o)


def render_text(m):
    """The page as plain text, for the cold read: headings, tables as rows, definitions inline."""
    r = Rich(m.get("legend", {}), text=True)
    o = [f"# {m['title']}", ""] + ([f"Status today. {r(m['status'])}", ""] if m.get("status") else []) + ["## Big picture"]
    if m.get("example"):
        o.append(r(m["example"]))
    o.append(r(m["big_picture"]))
    if m.get("decisions"):
        o += ["", "## What a reviewer has to decide"] + [f"- {r(d['question'])} {r(d.get('why', ''))} (lines {d['lines']})" for d in m["decisions"]]
    o += ["", f"## {m['flow'].get('title', 'How it works')}"]
    if m["flow"].get("intro"):
        o.append(r(m["flow"]["intro"]))
    for i, s in enumerate(m["flow"]["stages"], 1):
        seen = set()
        o += ["", f"### Stage {i}. {s['name']}", r(s["text"], seen)]
        if s.get("table"):
            o.append(" | ".join(s["table"]["head"]))
            o += [" | ".join(r(c, seen) for c in row) for row in s["table"].get("rows", [])]
        if s.get("note"):
            o.append(r(s["note"], seen))
    states = m.get("states") or []
    for s in states if isinstance(states, list) else [states]:
        o += ["", f"## {s.get('title', 'States')}", " then ".join(s["names"])]
        o += [f"{a}: {r(b)}" for a, b in s.get("rows", [])]
        if s.get("note"):
            o.append(r(s["note"]))
    o += ["", "## Each section"]
    for s in m["sections"]:
        seen = set()
        where = f"lines {s['lines']}" if s.get("lines") else ", ".join(s.get("files", []))
        o += ["", f"### {s['name']} ({where})", r(s["summary"], seen)] + [f"- {r(p, seen)}" for p in s.get("points", [])]
    for t in m.get("tables", []):
        o += ["", f"## {t['title']}"] + ([r(t["intro"])] if t.get("intro") else []) + [" | ".join(t["head"])]
        o += [" | ".join(r(c) for c in row) for row in t.get("rows", [])]
    if m.get("wrong"):
        o += ["", "## Looked wrong while reading"] + [f"{i}. {r(w['text'])} ({'lines ' + str(w['lines']) if w.get('lines') else ', '.join(w.get('files', []))}, {w['label']})" for i, w in enumerate(m["wrong"], 1)]
    return "\n".join(o) + "\n"


if __name__ == "__main__":
    args = sys.argv[1:]
    m = json.load(open([a for a in args if not a.startswith("--")][0], encoding="utf-8"))
    sys.stdout.write(render_text(m) if "--text" in args else render(m))
