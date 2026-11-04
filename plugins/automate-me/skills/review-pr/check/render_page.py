"""Renders a checked drafts.md as the review page, so every review page follows the same rules.

Usage: python3 check/render_page.py <drafts.md> > page.html
Publish the result with capabilities {"sample": {}} so the Ask Claude boxes work.
"""
import html
import json
import re
import sys

from check_drafts import read
from summary import groups

# Red holds the PR, yellow approves it with comments to read or waits on an answer, green approves it clean.
VERDICT_BADGE = [
    (re.compile(r"^approve after (.+)$"), "Approve after fixes", "warn", "Approve once {}"),
    (re.compile(r"^needs answer: (.+)$"), "Needs an answer", "warn", "Waits on an answer: {}"),
    (re.compile(r"^hold: (.+)$"), "Hold", "hold", "Held because it {}"),
    (re.compile(r"^scope: (.+)$"), "Scope only", "scope", "Read only where it meets the others: {}"),
    (re.compile(r"^approve$"), "Approve", "ok", ""),
]
TAG_CLASS = {"blocking": "block", "should fix": "fix", "question": "q", "nit": "nit"}


def inline(text):
    """Escapes text and turns `code` spans into <code> and markdown links into <a>."""
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", html.escape(text))
    return re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', out)


def sentence(text):
    return text[:1].upper() + text[1:] + ("" if text.endswith((".", "?")) else ".")


def badge(pr):
    verdict = pr["verdict"]
    if verdict == "approve" and any(f["match"] for f in pr["findings"]):
        return "Approve with comments", "warn", ""
    for pattern, label, kind, phrase in VERDICT_BADGE:
        m = pattern.match(verdict)
        if m:
            return label, kind, sentence(phrase.format(m.group(1))) if m.groups() else ""
    return verdict, "scope", ""


def grouped(findings):
    """One entry per comment text, listing every line it is posted on, in first-seen order."""
    out = {}
    for f in findings:
        m = f["match"]
        if not m:
            continue
        text = " ".join(f["comment"])
        g = out.setdefault(text, {"tag": m.group(1), "text": text, "lines": [], "plain": "", "evidence": "", "sites": "", "steps": []})
        g["lines"].append((m.group(2), m.group(3)))
        g["plain"] = g["plain"] or " ".join(f["plain"])
        g["evidence"] = g["evidence"] or " ".join(f["evidence"])
        g["sites"] = g["sites"] or " ".join(f["sites"])
        g["steps"] = g["steps"] or f["steps"]
    return list(out.values())


def mermaid_label(text):
    """Text for a quoted Mermaid label: no backticks, and the characters Mermaid reads as syntax as entity codes."""
    text = text.replace("`", "").replace("#", "#35;")
    return text.replace('"', "#quot;").replace("<", "#lt;").replace(">", "#gt;")


def flowchart(steps):
    """A top-down Mermaid flowchart with one quoted node per step, measured solid and inferred dashed."""
    lines = ["flowchart TD"]
    lines += [f'  s{i}["{i}. {mermaid_label(text)}"]:::{label}' for i, (label, text) in enumerate(steps, 1)]
    lines += [f"  s{i} --> s{i + 1}" for i in range(1, len(steps))]
    lines += ["  classDef measured stroke-width:2px", "  classDef inferred stroke-width:2px,stroke-dasharray:5 4"]
    return "\n".join(lines)


def explain_html(steps):
    """The collapsed Explain panel: the flowchart, a legend, and the same steps as a list that reads without Mermaid."""
    items = "".join(f'<li><span class="chip {label}">{label}</span> {inline(text)}</li>' for label, text in steps)
    return (f'<details class="explain"><summary>Explain</summary>'
            f'<pre class="mermaid">{html.escape(flowchart(steps))}</pre>'
            f'<p class="legend">Solid: measured. Dashed: inferred.</p><ol>{items}</ol></details>')


def finding_html(pr, g):
    lines = "".join(f'<li><a class="loc" href="{html.escape(u)}">{html.escape(s)}</a></li>' for s, u in g["lines"])
    where = "Posted on this line" if len(g["lines"]) == 1 else f"Posted on these {len(g['lines'])} lines"
    if g["lines"][0][0] == "PR":
        where = "Posted on the PR"
    plain = f'<div class="plain"><p class="box-label">What this means</p><p>{inline(g["plain"])}</p></div>' if g["plain"] else ""
    explain = explain_html(g["steps"]) if g["steps"] else ""
    proof = ""
    if g["evidence"] or g["sites"]:
        ev = f"<p>{inline(g['evidence'])}</p>" if g["evidence"] else ""
        st = ""
        if g["sites"]:
            count, _, cmd = g["sites"].partition("|")
            st = f"<p>Found in {html.escape(count.strip())} places with <code>{html.escape(cmd.strip())}</code></p>"
        proof = f'<details class="proof"><summary>How this was checked</summary>{ev}{st}</details>'
    topic = f"{pr}: {g['tag']} finding on {g['lines'][0][0]}"
    return (
        f'<article class="finding" data-topic="{html.escape(topic)}">'
        f'<div class="meta"><span class="tag {TAG_CLASS.get(g["tag"], "nit")}">{html.escape(g["tag"])}</span></div>'
        f"{plain}{explain}"
        f'<div class="box"><p class="box-label">Comment to post</p><p class="post" data-raw="{html.escape(g["text"])}">{inline(g["text"])}</p>'
        f'<button class="copy" type="button">Copy</button></div>'
        f'<div class="lines"><span>{where}</span><ul>{lines}</ul></div>'
        f"{proof}</article>"
    )


def body_html(pr, body):
    return (
        f'<article class="finding" data-topic="{html.escape(pr)}: review body">'
        f'<div class="meta"><span class="tag body">review body</span><span class="muted">posted as the review text, not on a line</span></div>'
        f'<div class="box"><p class="box-label">Comment to post</p><p class="post" data-raw="{html.escape(body)}">{inline(body)}</p>'
        f'<button class="copy" type="button">Copy</button></div></article>'
    )


def short_name(pr):
    owner_repo, _, num = pr["pr"].partition("#")
    return f'{owner_repo.split("/")[-1]}#{num}'


def panel_id(pr):
    """A bare token, because the artifact link passes only a plain #anchor through to the page."""
    return "pr-" + re.sub(r"[^A-Za-z0-9]+", "-", short_name(pr)).strip("-")


def pr_html(pr):
    owner_repo, _, num = pr["pr"].partition("#")
    url = f"https://github.com/{owner_repo}/pull/{num}"
    label, kind, reason = badge(pr)
    about = f'<p class="about">{inline(pr["about"])}</p>' if pr["about"] else ""
    changes = f'<p class="changes">{html.escape(pr["changes"])}</p>' if pr["changes"] else ""
    reason_html = f'<p class="reason">{inline(reason)}</p>' if reason else ""
    cards = "".join(finding_html(pr["pr"], g) for g in grouped(pr["findings"]))
    if pr["body"]:
        cards += body_html(pr["pr"], pr["body"])
    return (
        f'<section class="panel" id="{panel_id(pr)}"><div class="pr-head"><h2><a href="{url}">{html.escape(short_name(pr))}</a></h2>'
        f'<span class="badge {kind}">{label}</span>{about}{changes}{reason_html}</div>{cards}</section>'
    )


def tag_counts(pr):
    counts = {}
    for g in grouped(pr["findings"]):
        counts[g["tag"]] = counts.get(g["tag"], 0) + 1
    plural = {"question": "questions", "nit": "nits"}
    return ", ".join(f"{n} {plural.get(tag, tag) if n > 1 else tag}" for tag, n in sorted(counts.items(), key=lambda kv: list(TAG_CLASS).index(kv[0]) if kv[0] in TAG_CLASS else 9)) or "No line comments"


def tabs_html(prs):
    """With more than one PR, an overview plus one tab per PR, so each review reads on its own."""
    buttons = '<button type="button" role="tab" aria-controls="overview" data-panel="overview">Overview</button>' + "".join(
        f'<button type="button" role="tab" aria-controls="{panel_id(p)}" data-panel="{panel_id(p)}"><span class="dot {badge(p)[1]}"></span>{html.escape(short_name(p))}</button>'
        for p in prs)
    rows = "".join(
        f'<li><a class="go" href="#{panel_id(p)}" data-panel="{panel_id(p)}">{html.escape(short_name(p))}</a>'
        f'<span class="badge {badge(p)[1]}">{badge(p)[0]}</span>'
        f'<span class="muted">{html.escape(tag_counts(p))}</span>'
        + (f'<p class="about">{inline(p["about"])}</p>' if p["about"] else "") + "</li>"
        for p in prs)
    return (f'<nav class="tabs" role="tablist" aria-label="Pull requests">{buttons}</nav>'
            f'<div class="panel overview" id="overview"><h2>Overview</h2><ul class="prs">{rows}</ul></div>')


def summary_html(prs):
    """The summary message as rich text, so a copy keeps its bold headings and links when pasted into a chat tool."""
    rows = groups(prs)
    if not rows:
        return ""
    rich = "".join(f"<p><b>{name}</b></p><ul>" + "".join(
        f'<li><a href="{url}">{label}</a>'
        + (f", needs an answer: {html.escape(ask)}" if ask else "") + "</li>"
        for url, label, ask in items) + "</ul>" for name, items in rows)
    plain = "\n\n".join(name + "\n" + "\n".join(
        f"• {label} {url}" + (f", needs an answer: {ask}" if ask else "") for url, label, ask in items) for name, items in rows)
    return (f'<div class="summary"><div class="box"><p class="box-label">Summary message</p>'
            f'<div class="summary-msg" data-plain="{html.escape(plain)}">{rich}</div>'
            f'<button class="copy-rich" type="button">Copy</button></div></div>')


def render(path):
    doc = read(path)
    title = doc["title"].removeprefix("PR review:").strip() or "PR review"
    summary = " ".join(doc["summary"])
    sections = summary_html(doc["prs"]) + (tabs_html(doc["prs"]) if len(doc["prs"]) > 1 else "") + "".join(pr_html(p) for p in doc["prs"])
    refuter = html.escape(doc["refuter"]) if doc["refuter"] else ""
    return (TEMPLATE
            .replace("%TITLE%", html.escape(sentence(title).rstrip(".")))
            .replace("%SUMMARY%", inline(summary))
            .replace("%SECTIONS%", sections)
            .replace("%REFUTER%", refuter)
            .replace("%BACKGROUND%", json.dumps(summary).replace("</", "<\\/")))


TEMPLATE = r"""<title>%TITLE%</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root {
  --bg: #f6f7f8; --surface: #ffffff; --fg: #1b2228; --muted: #5f6b75; --line: #d9dee3; --accent: #1f5f8b;
  --ok: #1f7a4d; --ok-bg: #e5f4ec; --hold: #a3261d; --hold-bg: #fbe7e5; --fix: #a35a00; --fix-bg: #fdf1e2;
  --q: #3d5a99; --q-bg: #e9eefa; --plain-bg: #eef3f7; --ask-bg: #fbfcfd; --on-accent: #ffffff;
  --sans: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #12171b; --surface: #1a2127; --fg: #e3e8ec; --muted: #9aa6b0; --line: #2c353d; --accent: #7fb6dd;
  --ok: #7fd1a6; --ok-bg: #16301f; --hold: #f2968c; --hold-bg: #3a1a17; --fix: #f0b46a; --fix-bg: #3a2a15;
  --q: #a9bdf0; --q-bg: #1f2840; --plain-bg: #1c2730; --ask-bg: #161d22; --on-accent: #0d1418; color-scheme: dark } }
:root[data-theme="dark"] {
  --bg: #12171b; --surface: #1a2127; --fg: #e3e8ec; --muted: #9aa6b0; --line: #2c353d; --accent: #7fb6dd;
  --ok: #7fd1a6; --ok-bg: #16301f; --hold: #f2968c; --hold-bg: #3a1a17; --fix: #f0b46a; --fix-bg: #3a2a15;
  --q: #a9bdf0; --q-bg: #1f2840; --plain-bg: #1c2730; --ask-bg: #161d22; --on-accent: #0d1418; color-scheme: dark }
body { background: var(--bg); color: var(--fg); font-family: var(--sans); font-size: 15px; line-height: 1.55; }
.wrap { max-width: 760px; margin: 0 auto; padding-block: 32px 48px; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); display: grid; gap: 28px; }
h1 { font-size: 1.5rem; margin: 0; text-wrap: balance; }
.lede { margin: 0; color: var(--muted); max-width: 65ch; }
a { color: var(--accent); }
code { font-family: var(--mono); font-size: 0.86em; background: var(--plain-bg); padding: 0 3px; border-radius: 3px; overflow-wrap: anywhere; }
section { display: grid; gap: 18px; }
.pr-head { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 12px; border-bottom: 1px solid var(--line); padding-bottom: 10px; }
.pr-head h2 { font-size: 1.15rem; margin: 0; }
.about, .reason, .changes { flex-basis: 100%; margin: 0; max-width: 68ch; }
.about { color: var(--muted); font-size: 0.9rem; }
.changes { color: var(--muted); font-size: 0.78rem; }
.reason { font-size: 0.92rem; }
.badge { font-size: 0.8rem; font-weight: 600; padding: 2px 10px; border-radius: 999px; }
.badge.ok { color: var(--ok); background: var(--ok-bg); }
.badge.hold { color: var(--hold); background: var(--hold-bg); }
.badge.warn { color: var(--fix); background: var(--fix-bg); }
.badge.scope { color: var(--muted); border: 1px solid var(--line); }
.finding { display: grid; gap: 10px; min-width: 0; }
.meta { display: flex; flex-wrap: wrap; gap: 6px 10px; align-items: center; }
.tag { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.06em; font-weight: 600; padding: 2px 8px; border-radius: 4px; }
.tag.block { color: var(--hold); background: var(--hold-bg); }
.tag.fix { color: var(--fix); background: var(--fix-bg); }
.tag.q { color: var(--q); background: var(--q-bg); }
.tag.nit, .tag.body { color: var(--muted); border: 1px solid var(--line); }
.muted { font-size: 0.8rem; color: var(--muted); }
.plain { background: var(--plain-bg); border-radius: 6px; padding: 10px 14px; }
.plain p { margin: 0; max-width: 68ch; }
.box { position: relative; background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 10px 84px 12px 14px; }
.box p { margin: 0; overflow-wrap: anywhere; }
.box-label { font-size: 0.72rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 4px !important; }
.copy { position: absolute; top: 10px; right: 10px; font: 500 0.78rem var(--sans); color: var(--accent); background: transparent; border: 1px solid var(--line); border-radius: 4px; padding: 3px 9px; cursor: pointer; }
.copy:hover { border-color: var(--accent); }
.lines { font-size: 0.82rem; color: var(--muted); }
.lines ul { margin: 2px 0 0; padding-left: 18px; }
.loc { font-family: var(--mono); font-size: 0.8rem; overflow-wrap: anywhere; }
details > summary { cursor: pointer; font-size: 0.82rem; color: var(--muted); }
.proof p { margin: 6px 0 0; font-size: 0.82rem; color: var(--muted); overflow-wrap: anywhere; }
.explain { background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 8px 14px; }
.explain pre.mermaid { margin: 10px 0 0; overflow-x: auto; }
.explain ol { margin: 6px 0 0; padding-left: 22px; font-size: 0.88rem; }
.explain li { margin-bottom: 4px; overflow-wrap: anywhere; }
.legend { margin: 6px 0 0; font-size: 0.78rem; color: var(--muted); }
.chip { font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; padding: 1px 6px; border-radius: 4px; }
.chip.measured { color: var(--ok); background: var(--ok-bg); border: 1px solid var(--ok); }
.chip.inferred { color: var(--muted); border: 1px dashed var(--muted); }
.guide { background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 10px 16px; }
.guide > summary { font-size: 0.95rem; color: var(--fg); font-weight: 600; }
.guide dl { margin: 10px 0 0; display: grid; grid-template-columns: max-content 1fr; gap: 6px 14px; font-size: 0.9rem; }
.guide dt { font-weight: 600; }
.guide dd { margin: 0; }
@media (max-width: 520px) { .guide dl { grid-template-columns: 1fr; } .guide dd { margin-bottom: 6px; } }
button:focus-visible, textarea:focus-visible, summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.ask-toggle { justify-self: start; font: 500 0.82rem var(--sans); color: var(--accent); background: transparent; border: 1px solid var(--line); border-radius: 999px; padding: 4px 12px; cursor: pointer; }
.ask { display: grid; gap: 10px; background: var(--ask-bg); border: 1px solid var(--line); border-radius: 6px; padding: 12px 14px; }
.ask[hidden], .whole[hidden] { display: none; }
.log { display: grid; gap: 10px; }
.turn { margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; max-width: 68ch; }
.turn.you { color: var(--muted); font-size: 0.88rem; }
.turn.you::before { content: "You asked: "; font-weight: 600; }
.ask-row { display: flex; gap: 8px; align-items: flex-end; }
.ask-row textarea { flex: 1; min-width: 0; font: inherit; font-size: 0.92rem; color: var(--fg); background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 8px 10px; resize: vertical; min-height: 40px; }
.ask-row button { font: 600 0.85rem var(--sans); color: var(--on-accent); background: var(--accent); border: 0; border-radius: 6px; padding: 9px 14px; cursor: pointer; }
.ask-row button:disabled { opacity: 0.55; cursor: default; }
.ask-note { margin: 0; font-size: 0.78rem; color: var(--muted); }
.suggest { display: flex; flex-wrap: wrap; gap: 6px; }
.suggest button { font: 0.8rem var(--sans); color: var(--fg); background: var(--surface); border: 1px solid var(--line); border-radius: 999px; padding: 3px 10px; cursor: pointer; }
.whole { display: grid; gap: 10px; border-top: 1px solid var(--line); padding-top: 18px; }
.whole h2 { margin: 0; font-size: 1.1rem; }
.foot { font-size: 0.82rem; color: var(--muted); }
.foot p { margin: 6px 0 0; }
.summary-msg p { margin: 0; }
.summary-msg ul { margin: 2px 0 10px; padding-left: 20px; }
.summary-msg ul:last-child { margin-bottom: 0; }
.copy-rich { position: absolute; top: 10px; right: 10px; font: 500 0.78rem var(--sans); color: var(--accent); background: transparent; border: 1px solid var(--line); border-radius: 4px; padding: 3px 9px; cursor: pointer; }
.tabs { display: flex; gap: 4px; overflow-x: auto; border-bottom: 1px solid var(--line); }
.tabs button { flex: none; display: inline-flex; align-items: center; gap: 6px; font: 500 0.9rem var(--sans); color: var(--muted); background: transparent; border: 0; border-bottom: 2px solid transparent; padding: 8px 12px; cursor: pointer; }
.tabs button[aria-selected="true"] { color: var(--fg); border-bottom-color: var(--accent); }
.tabs button:focus-visible, .go:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.dot { width: 8px; height: 8px; border-radius: 50%; background: var(--muted); }
.dot.ok { background: var(--ok); }
.dot.hold { background: var(--hold); }
.dot.warn { background: var(--fix); }
.overview { display: grid; gap: 12px; }
.overview h2 { margin: 0; font-size: 1.1rem; }
.prs { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.prs li { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 12px; background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 12px 14px; }
.prs .go { font-weight: 600; }
</style>

<div class="wrap">
  <header style="display:grid;gap:8px">
    <h1>%TITLE%</h1>
    <p class="lede">%SUMMARY%</p>
  </header>

  <details class="guide">
    <summary>How to read this page</summary>
    <dl>
      <dt>Badge</dt><dd>The verdict for the PR. The line under it says what has to change first.</dd>
      <dt>Shaded text</dt><dd>What the finding means, in plain words. Only for you; it is never posted.</dd>
      <dt>Comment to post</dt><dd>The comment exactly as it would go on GitHub. Copy copies it with its GitHub formatting.</dd>
      <dt>Blocking</dt><dd>Holds the PR until it is answered.</dd>
      <dt>Should fix</dt><dd>A real problem worth fixing before merge that does not hold the PR.</dd>
      <dt>Question</dt><dd>Something only a person can decide, often a product call.</dd>
      <dt>Explain</dt><dd>The path from trigger to failure, one step per line. Solid steps were measured by running something. Dashed steps were read from the code and reasoned. Never posted.</dd>
      <dt>Lines</dt><dd>Where the comment is posted. A mistake repeated across lines gets the same comment on each.</dd>
      <dt>How this was checked</dt><dd>What was read or run to back the finding, and the command that counts its places.</dd>
      <dt>Ask Claude</dt><dd>Ask a follow-up about a finding. It answers from this page only and cannot open the code; ask in Claude Code for anything that needs the code.</dd>
    </dl>
  </details>

  %SECTIONS%

  <div class="whole" id="whole" data-topic="the whole review">
    <h2>Ask about the whole review</h2>
    <p class="ask-note">A term, why a finding matters, what should merge first.</p>
  </div>

  <details class="foot"><summary>How this review was checked</summary><p>%REFUTER% Fresh agents tried to prove each comment wrong before this page was made; reworded comments were corrected.</p></details>
</div>

<script>
(function () {
  var BACKGROUND = %BACKGROUND%;
  document.querySelectorAll('.copy-rich').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var msg = btn.parentNode.querySelector('.summary-msg');
      var done = function () { btn.textContent = 'Copied'; setTimeout(function () { btn.textContent = 'Copy'; }, 1500); };
      var select = function () {
        var r = document.createRange(); r.selectNodeContents(msg);
        var s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
        btn.textContent = 'Press Cmd+C';
      };
      try {
        var item = new ClipboardItem({
          'text/html': new Blob([msg.innerHTML], { type: 'text/html' }),
          'text/plain': new Blob([msg.getAttribute('data-plain')], { type: 'text/plain' })
        });
        navigator.clipboard.write([item]).then(done, select);
      } catch (e) { select(); }
    });
  });

  document.querySelectorAll('.copy').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var p = btn.parentNode.querySelector('p.post');
      var done = function () { btn.textContent = 'Copied'; setTimeout(function () { btn.textContent = 'Copy'; }, 1500); };
      var fallback = function () {
        var r = document.createRange(); r.selectNodeContents(p);
        var s = window.getSelection(); s.removeAllRanges(); s.addRange(r); btn.textContent = 'Selected';
      };
      try { navigator.clipboard.writeText(p.getAttribute('data-raw')).then(done, fallback); } catch (e) { fallback(); }
    });
  });

  var tabs = document.querySelectorAll('.tabs button');
  if (tabs.length) {
    var panels = document.querySelectorAll('.panel');
    var show = function (id, scroll) {
      panels.forEach(function (p) { p.hidden = p.id !== id; });
      tabs.forEach(function (t) { t.setAttribute('aria-selected', String(t.getAttribute('data-panel') === id)); });
      try { history.replaceState(null, '', location.pathname + location.search + (id === 'overview' ? '' : '#' + id)); } catch (e) {}
      if (scroll) document.querySelector('.tabs').scrollIntoView({ block: 'start' });
    };
    document.querySelectorAll('[data-panel]').forEach(function (el) {
      el.addEventListener('click', function (ev) { ev.preventDefault(); show(el.getAttribute('data-panel'), el.classList.contains('go')); });
    });
    var start = location.hash.slice(1);
    var target = start && document.getElementById(start);
    show(target && target.classList.contains('panel') ? start : 'overview', false);
  }

  function pageText() {
    var out = [];
    document.querySelectorAll('section').forEach(function (sec) {
      var head = sec.querySelector('.pr-head');
      out.push('\n== ' + head.textContent.replace(/\s+/g, ' ').trim());
      sec.querySelectorAll('.finding').forEach(function (f) {
        out.push('\n-- Finding (' + f.querySelector('.tag').textContent + ')');
        var pl = f.querySelector('.plain'); if (pl) out.push('Plain words: ' + pl.textContent);
        out.push('Comment: ' + f.querySelector('p.post').getAttribute('data-raw'));
        var ln = f.querySelector('.lines'); if (ln) out.push(ln.textContent.replace(/\s+/g, ' '));
        var pr = f.querySelector('.proof'); if (pr) out.push(pr.textContent.replace(/\s+/g, ' '));
      });
    });
    return out.join('\n');
  }

  function rules(topic) {
    return 'You are helping the reviewer understand this code review before posting it. ' +
      'The follow-up is about: ' + topic + '.\n' +
      'Answer in plain, short sentences, like a senior engineer explaining to a colleague. Define any jargon you use. ' +
      'Plain text only: no markdown, no headings, no bullet symbols. Under 150 words unless asked for more. ' +
      'You see only the text below, not the code. If the answer needs the code, say so and suggest asking Claude Code. Never invent file contents, line numbers or behavior.\n\n' +
      'Summary: ' + BACKGROUND + '\n\nThe review page:\n' + pageText();
  }

  var SUGGEST = {
    'the whole review': ['What should merge first?', 'Which finding matters most?', 'Explain the terms used'],
    'default': ['Why does this matter?', 'What would the fix look like?', 'Explain the terms']
  };

  function copyFor(code) {
    if (['not_granted', 'sampling_disabled', 'not_declared', 'capability_disabled', 'capability_removed'].indexOf(code) >= 0) return 'Asking Claude is not available in this view.';
    if (code === 'rate_limited') return 'Too many questions at once. Try again in a minute.';
    if (code === 'session_expired') return 'Sign in to claude.ai again, then ask.';
    if (code === 'refused') return 'Claude declined that one. Try rewording it.';
    return 'That did not go through. Try again.';
  }

  function buildAsk(host, topic, sample, open) {
    var turns = [], busy = false;
    var panel = document.createElement('div'); panel.className = 'ask'; panel.hidden = !open;
    var log = document.createElement('div'); log.className = 'log';
    var sugg = document.createElement('div'); sugg.className = 'suggest';
    var row = document.createElement('div'); row.className = 'ask-row';
    var ta = document.createElement('textarea'); ta.rows = 1; ta.placeholder = 'Ask a follow-up...';
    ta.setAttribute('aria-label', 'Question about ' + topic);
    var send = document.createElement('button'); send.type = 'button'; send.textContent = 'Ask';
    var note = document.createElement('p'); note.className = 'ask-note';
    row.append(ta, send); panel.append(log, sugg, row, note);
    (SUGGEST[topic] || SUGGEST['default']).forEach(function (q) {
      var b = document.createElement('button'); b.type = 'button'; b.textContent = q;
      b.addEventListener('click', function () { ta.value = q; ask(); });
      sugg.append(b);
    });
    function ask() {
      var q = ta.value.trim();
      if (!q || busy) return;
      busy = true; send.disabled = true; note.textContent = ''; sugg.hidden = true;
      var you = document.createElement('p'); you.className = 'turn you'; you.textContent = q;
      var ans = document.createElement('p'); ans.className = 'turn'; ans.textContent = 'Thinking...';
      log.append(you, ans); ta.value = '';
      turns.push({ role: 'user', content: q });
      sample([{ role: 'user', content: rules(topic) }].concat(turns.slice(-12)), { cache: false, onText: function (u) { ans.textContent = u.text; } })
        .then(function (r) {
          turns.push({ role: 'assistant', content: r.text });
          if (r.truncated) note.textContent = 'The answer was cut short. Ask for a shorter one.';
        }, function (e) {
          ans.textContent = (e && e.text) ? e.text : '';
          if (!ans.textContent) ans.remove();
          turns.pop();
          if (!e || e.code !== 'cancelled') note.textContent = copyFor(e && e.code);
        })
        .then(function () { busy = false; send.disabled = false; ta.focus(); });
    }
    send.addEventListener('click', ask);
    ta.addEventListener('keydown', function (ev) { if (ev.key === 'Enter' && !ev.shiftKey) { ev.preventDefault(); ask(); } });
    host.append(panel);
    return { panel: panel, ta: ta };
  }

  var whole = document.getElementById('whole');
  var ready = window.claude && typeof window.claude.use === 'function' ? window.claude.use('sample') : Promise.resolve(null);
  ready.then(function (sample) {
    if (!sample) { whole.hidden = true; return; }
    document.querySelectorAll('.finding').forEach(function (f) {
      var t = document.createElement('button'); t.type = 'button'; t.className = 'ask-toggle'; t.textContent = 'Ask Claude about this';
      f.append(t);
      var a = buildAsk(f, f.getAttribute('data-topic'), sample, false);
      t.addEventListener('click', function () {
        a.panel.hidden = !a.panel.hidden;
        t.textContent = a.panel.hidden ? 'Ask Claude about this' : 'Hide questions';
        if (!a.panel.hidden) a.ta.focus();
      });
    });
    buildAsk(whole, whole.getAttribute('data-topic'), sample, true);
  }, function () { whole.hidden = true; });
})();
</script>
"""

if __name__ == "__main__":
    from cli import usage_or_exit
    usage_or_exit(__doc__, sys.argv, 1)
    sys.stdout.write(render(sys.argv[1]))
