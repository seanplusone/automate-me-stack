"""Deterministic checks for write-edd output. Read only. Never runs the project.

Usage:
  python3 check_edd.py blast    <repo[,repo...]> <blast.txt>
  python3 check_edd.py current  <repo[,repo...]> <current.txt>
  python3 check_edd.py delta    <delta.txt> <map.txt> <gaps.txt> <pm-answers.md> <arch.txt> <current.txt> [<blast.txt or evidence file> ...]
  python3 check_edd.py sections <edd.md> <layout.json>
  python3 check_edd.py coverage <edd.md> <map.txt> <gaps.txt> <pm-answers.md> <layout.json> <blast, arch or delta file> [...]
  python3 check_edd.py hazards  <edd.md> <layout.json>
  python3 check_edd.py names    <repo[,repo...]> <file> [<file> ...]
  python3 check_edd.py spikes   <edd.md> <evidence dir> <layout.json>
  python3 check_edd.py evidence <evidence dir>
  python3 check_edd.py diagrams <edd.md> <delta.txt> <layout.json>
  python3 check_edd.py merge    <out dir> <slice dir> [<slice dir> ...]
  python3 check_edd.py writing  <file>

<layout.json> is the run's own layout when the input dir has one, else rules/edd-sections.json.
Each check prints PASS or FAIL and exits 1 on FAIL.
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "shared"))
from check_blast import check_blast  # noqa: E402
from check_writing import FAILED, check_writing, report  # noqa: E402


def section_text(edd, name):
    m = re.search(rf"^#+\s*(?:\d+\.\s*)?{re.escape(name)}\b.*?$(.*?)(?=^##\s|\Z)", edd, re.M | re.S)
    return m.group(1) if m else None


DEFAULT_ROLES = {"hazards": "Known hazards", "decisions": "Decisions blocking build start", "prd_record": "Summary"}
BUILT_IN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rules", "edd-sections.json")


def load_layout(path):
    """A layout may leave out the evidence rules and diagram kinds. Those fall back to the built-in layout."""
    rules = json.load(open(path))
    base = json.load(open(BUILT_IN))
    for k in ("evidence_patterns", "min_level", "level_needs_run", "diagrams"):
        rules.setdefault(k, base[k])
    rules["roles"] = {**DEFAULT_ROLES, **rules.get("roles", {})}
    return rules


def tables_in(body):
    """Every markdown table in a section body, as (header cells, data rows). Rows stay as raw lines."""
    out, block = [], []
    for line in body.split("\n") + [""]:
        if line.strip().startswith("|"):
            block.append(line)
            continue
        if block:
            sep = len(block) > 1 and re.match(r"^\|?[\s:|-]+\|?$", block[1].strip())
            out.append(([c.strip() for c in block[0].strip().strip("|").split("|")], block[2 if sep else 1:]))
        block = []
    return out


def find_table(body, columns):
    """The first table in the section whose header holds every column, or None."""
    return next((t for t in tables_in(body) if all(c in t[0] for c in columns)), None)


def check_sections(edd_path, rules_path):
    edd = open(edd_path).read()
    rules = load_layout(rules_path)
    fails = []
    for h in rules["header"]:
        if not re.search(rf"^\**{re.escape(h)}:?\**:?", edd, re.M):
            fails.append(f"header missing: {h}")
    last = -1
    for name in rules["sections"]:
        m = re.search(rf"^##\s*(?:\d+\.\s*)?{re.escape(name)}\b", edd, re.M)
        if not m:
            fails.append(f"section missing: {name}")
        elif m.start() < last:
            fails.append(f"section out of order: {name}")
        else:
            last = m.start()
    for name, spec in rules["tables"].items():
        sets = [spec] if spec and isinstance(spec[0], str) else spec
        heads = [h for h, _ in tables_in(section_text(edd, name) or "")]
        for i, cols in enumerate(sets):
            best = max(heads, key=lambda h: len([c for c in cols if c in h]), default=[])
            tag = f" (table {i + 1})" if len(sets) > 1 else ""
            for c in cols:
                if c not in best:
                    fails.append(f"table '{name}' missing column: {c}{tag}")
    report(f"sections: {len(rules['sections'])} expected", fails)


def cited(edd, token):
    """A token counts as cited in brackets, like [R3], or inside a table row."""
    t = re.escape(token)
    if re.search(rf"\[[^\]]*\b{t}\b[^\]]*\]", edd):
        return True
    return any(l.strip().startswith("|") and re.search(rf"\b{t}\b", l) for l in edd.split("\n"))


ID_LINE = re.compile(r"^(?:(?:HOOK|SCOPE|WRITER|READER)\s+(BR\d+)|ARCH\s+(A\d+)|DELTA\s+(D\d+)|ENABLE\s+(E\d+)):")
CORRECTION = re.compile(r"^CORRECTION (C\d+):\s*(.*)$")
CORRECTION_STATUS = ("OPEN", "ACCEPTED", "REJECTED")


def field(parts, name):
    for p in parts:
        if p.startswith(name + " "):
            return p[len(name) + 1:].strip()
    return None


def corrections(answers_path):
    """(id, [statement, code, posted, status]) for each CORRECTION line. The statement may hold a pipe."""
    out = []
    for line in open(answers_path):
        m = CORRECTION.match(line.strip())
        if m:
            out.append((m.group(1), [p.strip() for p in m.group(2).rsplit("|", 3)]))
    return out


def read_fields(path):
    """{FIELD: value} for one evidence file. A value runs until the next line that starts a new FIELD:.
    ID keeps its first token and LEVEL its leading digit, so "SPIKE2 (PROJ-2)" and "3 (walked it)" read as SPIKE2 and 3."""
    fields, key = {}, None
    for line in open(path, errors="replace"):
        s = line.strip()
        m = re.match(r"^([A-Z]+):\s*(.*)$", s)
        if m:
            key = m.group(1) if m.group(1) not in fields else None
            if key:
                fields[key] = m.group(2).strip()
        elif key and s:
            fields[key] = f"{fields[key]} {s}".strip()
    if fields.get("ID"):
        fields["ID"] = fields["ID"].split()[0]
    if re.match(r"\d", fields.get("LEVEL", "")):
        fields["LEVEL"] = fields["LEVEL"][0]
    return fields


def spike_files(paths):
    """{SPIKE id: {FIELD: value}} for every evidence file among paths."""
    out = {}
    for p in paths:
        if os.path.isfile(p):
            fields = read_fields(p)
            if re.match(r"^SPIKE\d+$", fields.get("ID", "")):
                out[fields["ID"]] = fields
    return out


def check_coverage(edd_path, map_path, gaps_path, answers_path, layout_path, *id_paths):
    """Every R, Engineer GAP, PENDING GAP, CORRECTION, BR, ARCH, DELTA and ENABLE id must be cited in the EDD.
    A pending answer and a planned spike each get a decisions row that lists every change resting on them."""
    edd = open(edd_path).read()
    role = load_layout(layout_path)["roles"]
    want = []
    for line in open(map_path):
        m = re.match(r"^\s*(R\d+):", line)
        if m:
            want.append(m.group(1))
    for line in open(gaps_path):
        m = re.match(r"^GAP (\d+):\s*\S+\s*\|[^|]*\|\s*Engineer\s*\|", line)
        if m:
            want.append(f"GAP {m.group(1)}")
    pending = sorted(ids_in(answers_path, r"^PENDING GAP (\d+):"), key=int)
    want += [f"GAP {g}" for g in pending]
    id_paths = [p for p in id_paths if os.path.isfile(p)]
    assumes = {}
    for p in id_paths:
        for line in open(p):
            m = re.match(r"^(?:DELTA|ENABLE) ([DE]\d+):\s*(.*)$", line.strip())
            if m:
                a = field([x.strip() for x in m.group(2).split("|")], "ASSUMES")
                if a:
                    assumes.setdefault(a, []).append(m.group(1))
            m = ID_LINE.match(line.strip())
            if m:
                want.append(next(g for g in m.groups() if g))
    planned = {i: f for i, f in spike_files(id_paths).items() if f.get("STATUS") == "PLANNED"}
    cs = corrections(answers_path)
    want = list(dict.fromkeys(want + [c for c, _ in cs]))
    own = {c for c, _ in cs} | {f"GAP {g}" for g in pending}
    missing = [t for t in want if t not in own and not cited(edd, t)]
    fails = [f"not cited: {t}" for t in missing]
    bad = set()
    record = section_text(edd, role["prd_record"]) or ""
    for cid, parts in cs:
        lines = [l for l in record.split("\n") if re.search(rf"\b{cid}\b", l)]
        if not lines:
            fails.append(f"{cid} is not listed in {role['prd_record']}")
            bad.add(cid)
        elif parts[-1] in ("OPEN", "REJECTED") and not any(re.search(r"\bassum", l, re.I) for l in lines):
            fails.append(f"{cid} is {parts[-1]} but its line in {role['prd_record']} does not say what the design assumes")
    decisions = [l for l in (section_text(edd, role["decisions"]) or "").split("\n") if l.strip().startswith("|")]
    groups = {f"GAP {g}": [f"GAP {g}"] for g in pending}
    for sid, f in sorted(planned.items()):
        key = f.get("ANSWERS")
        if key in groups:
            groups[key].append(sid)
        else:
            groups[sid] = [sid]
    for tokens in groups.values():
        name = " and ".join(tokens)
        rows = [r for r in decisions if any(re.search(rf"\b{t}\b", r) for t in tokens)]
        absent = [t for t in tokens if not any(re.search(rf"\b{t}\b", r) for r in rows)]
        for t in absent:
            fails.append(f"no row in {role['decisions']} cites {t}")
            bad.add(t)
        if absent:
            continue
        if any(t.startswith("SPIKE") for t in tokens) and not any(re.search(r"\bspike\b", r, re.I) for r in rows):
            fails.append(f"the {role['decisions']} row for {name} does not say it is a spike")
        have = set(re.findall(r"\b[DE]\d+\b", " ".join(rows)))
        for t in tokens:
            for d in assumes.get(t, []):
                if d not in have:
                    fails.append(f"the {role['decisions']} row for {name} does not list {d}, which ASSUMES {t}")
    report(f"coverage: {len(want) - len(missing) - len(bad & set(want))}/{len(want)} cited", fails)


def check_hazards(edd_path, rules_path):
    edd = open(edd_path).read()
    rules = load_layout(rules_path)
    pats = [re.compile(p) for p in rules["evidence_patterns"]]
    table = find_table(section_text(edd, rules["roles"]["hazards"]) or "", ["Evidence", "Level"])
    if not table:
        report("hazards: 0 rows", ["no hazards table"])
        return
    cols, rows = table
    ev, lv = cols.index("Evidence"), cols.index("Level")
    need_run = rules.get("level_needs_run", {})
    fails = []
    n = 0
    for r in rows:
        cells = [c.strip() for c in r.strip().strip("|").split("|")]
        n += 1
        if ev >= len(cells) or not any(p.search(cells[ev]) for p in pats):
            fails.append(f"hazard {cells[0]} has no evidence")
            continue
        if lv >= len(cells) or not re.match(r"^[1-5]$", cells[lv]):
            fails.append(f"hazard {cells[0]} needs a level from 1 to 5")
            continue
        if int(cells[lv]) < rules.get("min_level", 2):
            fails.append(f"hazard {cells[0]} is level {cells[lv]}, below the minimum")
        if cells[lv] in need_run and not any(k in cells[ev] for k in need_run[cells[lv]]):
            fails.append(f"hazard {cells[0]} claims level {cells[lv]} without a PROBE or SPIKE")
    report(f"hazards: {n} rows", fails)


def evidence_files(evidence_dir):
    """Read every PROBE and SPIKE file into {id: {FIELD: value}}."""
    out = {}
    for name in sorted(os.listdir(evidence_dir)):
        if name.endswith(".md"):
            fields = read_fields(os.path.join(evidence_dir, name))
            if re.match(r"^(PROBE|SPIKE)\d+$", fields.get("ID", "")):
                out[fields["ID"]] = fields
    return out


PRODUCTION = re.compile(r"\b(production|prod|customer)\b", re.I)
_ITEM = r"(?:(?:a|an|any)\s+)?(?:production|prod|customer)s?\b"
NEGATED = re.compile(rf"\b(?:no|never|not)\s+{_ITEM}(?:\s*(?:,|or|and)\s*{_ITEM})*", re.I)


def names_production(where):
    """True when WHERE still names production or a customer once phrases like "never a customer org" are dropped."""
    return bool(PRODUCTION.search(NEGATED.sub(" ", where)))


def check_evidence_file(sid, f):
    """The rules for one PROBE or SPIKE file, shared by `spikes` and `evidence`."""
    fails = []
    status = f.get("STATUS", "")
    where = f.get("WHERE", "")
    person = f.get("RUNNER", "").lower() == "person"
    guard_ok = not names_production(where) or (person and re.search(r"read[- ]only", where, re.I))
    if status == "RAN":
        for k in ("METHOD", "WHERE", "RESULT", "ANSWER"):
            if not f.get(k):
                fails.append(f"{sid} ran but has no {k}")
        if f.get("LEVEL") not in ("2", "3", "4", "5"):
            fails.append(f"{sid} ran but LEVEL is not 2 to 5: {f.get('LEVEL')}")
        if not guard_ok:
            fails.append(f"{sid} ran against production or a customer: {where}")
    elif status == "PLANNED":
        for k in ("QUESTION", "METHOD", "WHERE"):
            if not f.get(k):
                fails.append(f"{sid} is planned but has no {k}")
        for k in ("RESULT", "ANSWER", "LEVEL"):
            if f.get(k):
                fails.append(f"{sid} is planned but has a {k}")
        if f.get("ANSWERS") and not re.match(r"^GAP \d+$", f["ANSWERS"]):
            fails.append(f"{sid} ANSWERS must be GAP <n>: {f['ANSWERS']}")
        if not guard_ok:
            fails.append(f"{sid} would run against production or a customer: {where}")
    elif status == "BLOCKED":
        if len(f.get("BLOCKED", "")) < 10:
            fails.append(f"{sid} is blocked with no reason")
        if f.get("ANSWER"):
            fails.append(f"{sid} is blocked but has an ANSWER")
    else:
        fails.append(f"{sid} STATUS must be RAN, PLANNED or BLOCKED: {status}")
    return fails


def tally(files):
    """The tail of a PASS or FAIL line: planned and person-run counts, when there are any."""
    planned = sum(1 for f in files if f.get("STATUS") == "PLANNED")
    person = sum(1 for f in files if f.get("RUNNER", "").lower() == "person")
    return (f", {planned} planned" if planned else "") + (f", {person} person-run" if person else "")


def check_evidence(evidence_dir):
    """The per-file rules on every PROBE and SPIKE file in a directory, with no EDD."""
    files = evidence_files(evidence_dir)
    fails = [m for sid, f in files.items() for m in check_evidence_file(sid, f)]
    ran = sum(1 for f in files.values() if f.get("STATUS") == "RAN")
    report(f"evidence: {len(files)} files, {ran} ran{tally(files.values())}", fails)


def check_spikes(edd_path, evidence_dir, rules_path):
    """Every SPIKE the EDD cites has a file that either ran or says why it is blocked.
    A planned spike has no answer yet. A hazard reaches level 4 or 5 only through a PROBE or SPIKE that ran at that level or higher."""
    edd = open(edd_path).read()
    rules = load_layout(rules_path)
    files = evidence_files(evidence_dir)
    fails = []
    cited_ids = sorted(set(re.findall(r"\b(?:PROBE|SPIKE)\d+\b", edd)))
    for sid in cited_ids:
        if sid not in files:
            fails.append(f"{sid} is cited but has no evidence file")
        else:
            fails += check_evidence_file(sid, files[sid])
    ran = {i: int(f["LEVEL"]) for i, f in files.items() if f.get("STATUS") == "RAN" and f.get("LEVEL", "").isdigit()}
    ran |= {i: 0 for i, f in files.items() if f.get("STATUS") == "RAN" and i not in ran}
    table = find_table(section_text(edd, rules["roles"]["hazards"]) or "", ["Evidence", "Level"])
    if table:
        cols, rows = table
        ev, lv = cols.index("Evidence"), cols.index("Level")
        for r in rows:
            cells = [c.strip() for c in r.strip().strip("|").split("|")]
            if max(ev, lv) >= len(cells) or cells[lv] not in rules.get("level_needs_run", {}):
                continue
            ran_cited = [ran[i] for i in set(re.findall(r"\b(?:PROBE|SPIKE)\d+\b", cells[ev])) if i in ran]
            if not ran_cited:
                fails.append(f"hazard {cells[0]} claims level {cells[lv]} but cites no PROBE or SPIKE that ran")
            elif max(ran_cited) < int(cells[lv]):
                fails.append(f"hazard {cells[0]} claims level {cells[lv]} but the PROBEs and SPIKEs it cites ran at level {max(ran_cited)} at most")
    cited_files = [files[i] for i in cited_ids if i in files]
    report(f"spikes: {len(cited_ids)} cited, {len(set(ran) & set(cited_ids))} ran{tally(cited_files)}", fails)


MERMAID = re.compile(r"^```mermaid\s*\n(.*?)^```", re.M | re.S)


def check_diagrams(edd_path, delta_path, rules_path):
    """The diagrams sit in their section, one of each kind, and are built from the delta list:
    every DELTA and ENABLE id appears in a diagram, and every D or E id in a diagram is real."""
    edd = open(edd_path).read()
    rules = load_layout(rules_path)["diagrams"]
    body = section_text(edd, rules["section"]) or ""
    blocks = [b for b in MERMAID.findall(body)]
    fails = []
    kinds = [b.strip().split()[0] if b.strip() else "" for b in blocks]
    for k in rules["kinds"]:
        if k not in kinds:
            fails.append(f"no {k} diagram in {rules['section']}")
    want = ids_in(delta_path, r"^(?:DELTA|ENABLE) ([DE]\d+):")
    drawn = set()
    for b in blocks:
        drawn |= set(re.findall(r"\b[DE]\d+\b", b))
        if b.strip().startswith("sequenceDiagram"):
            declared = set(re.findall(r"^\s*(?:participant|actor)\s+(\w+)", b, re.M))
            used = {p for pair in re.findall(r"^\s*(\w+)\s*-{1,2}[>x)]{1,2}\+?-?\s*(\w+)\s*:", b, re.M) for p in pair}
            for p in sorted(used - declared):
                fails.append(f"sequence diagram uses undeclared participant: {p}")
    for i in sorted(want - drawn):
        fails.append(f"{i} is in the delta list but in no diagram")
    for i in sorted(drawn - want):
        fails.append(f"{i} is in a diagram but not in the delta list")
    report(f"diagrams: {len(blocks)} found, {len(want & drawn)}/{len(want)} delta ids drawn", fails)


def ids_in(path, pattern):
    out = set()
    for line in open(path):
        m = re.match(pattern, line.strip())
        if m:
            out.add(m.group(1))
    return out


def check_delta(delta_path, map_path, gaps_path, answers_path, arch_path, current_path, *evidence_paths):
    """Every DELTA has a real BECAUSE and CURRENT, sits under a real ARCH. Every ENABLE has evidence. Every ARCH serves a real id.
    An ASSUMES names a PENDING GAP or a planned or blocked spike. Every CORRECTION is well formed and cites file:line."""
    rs = ids_in(map_path, r"^(R\d+):")
    gaps = {f"GAP {g}" for g in ids_in(gaps_path, r"^GAP (\d+):")}
    answered = {f"ANSWER GAP {g}" for g in ids_in(answers_path, r"^ANSWER GAP (\d+):")}
    pending = {f"GAP {g}" for g in ids_in(answers_path, r"^PENDING GAP (\d+):")}
    answered_gaps = {f"GAP {g}" for g in ids_in(answers_path, r"^ANSWER GAP (\d+):")}
    spikes = {i: f.get("STATUS") for i, f in spike_files(evidence_paths).items()}
    reasons = rs | gaps | answered
    archs = ids_in(arch_path, r"^ARCH (A\d+):")
    steps = ids_in(current_path, r"^STEP (CS\d+):")
    evidence = set(steps)
    for p in evidence_paths:
        evidence |= ids_in(p, r"^(?:HOOK|SCOPE|WRITER|READER)\s+(BR\d+):")
        evidence |= ids_in(p, r"^ID:\s*((?:PROBE|SPIKE)\d+)")
    fails = []
    used_archs = set()
    n = 0

    seen = set()
    for cid, parts in corrections(answers_path):
        if cid in seen:
            fails.append(f"{cid} is listed twice")
        seen.add(cid)
        if len(parts) != 4:
            fails.append(f"{cid} needs: statement | code with file:line | posted <date> | OPEN, ACCEPTED or REJECTED")
            continue
        if not re.search(r"[^\s|]+:\d+", parts[1]):
            fails.append(f"{cid} has no file:line for what the code does")
        if not parts[2].startswith("posted "):
            fails.append(f"{cid} needs 'posted <date>': {parts[2][:30]}")
        if parts[3] not in CORRECTION_STATUS:
            fails.append(f"{cid} status must be OPEN, ACCEPTED or REJECTED: {parts[3]}")
    for line in open(arch_path):
        m = re.match(r"^ARCH (A\d+):\s*(.*)$", line.strip())
        if m:
            serves = field([p.strip() for p in m.group(2).split("|")], "SERVES") or ""
            ids = re.findall(r"R\d+|GAP \d+", serves)
            if not ids or not all(i in reasons for i in ids):
                fails.append(f"{m.group(1)} SERVES has no real R or GAP id: {serves[:50]}")
    for line in open(delta_path):
        s = line.strip()
        m = re.match(r"^(DELTA|ENABLE) ([DE]\d+):\s*(.*)$", s)
        if not m:
            continue
        n += 1
        kind, did = m.group(1), m.group(2)
        parts = [p.strip() for p in m.group(3).split("|")]
        under = field(parts, "UNDER")
        if under not in archs:
            fails.append(f"{did} is not UNDER a real ARCH: {under}")
        else:
            used_archs.add(under)
        assumed = field(parts, "ASSUMES")
        if assumed:
            if assumed in answered_gaps:
                fails.append(f"{did} ASSUMES {assumed}, which is answered, drop ASSUMES")
            elif assumed in spikes:
                if spikes[assumed] == "RAN":
                    fails.append(f"{did} ASSUMES {assumed}, which ran, drop ASSUMES")
                elif spikes[assumed] not in ("PLANNED", "BLOCKED"):
                    fails.append(f"{did} ASSUMES {assumed}, which has no PLANNED or BLOCKED status")
            elif assumed not in pending:
                fails.append(f"{did} ASSUMES is not a PENDING GAP or a planned or blocked spike: {assumed}")
        if kind == "DELTA":
            because = field(parts, "BECAUSE")
            current = field(parts, "CURRENT")
            if because not in reasons:
                fails.append(f"{did} BECAUSE is not a real R, GAP or ANSWER id: {because}")
            if current != "NONE" and current not in steps:
                fails.append(f"{did} CURRENT is not a traced CS step or NONE: {current}")
        else:
            enables = field(parts, "ENABLES")
            needed = field(parts, "NEEDED BECAUSE")
            if enables not in rs:
                fails.append(f"{did} ENABLES is not a real R id: {enables}")
            if needed not in evidence:
                fails.append(f"{did} NEEDED BECAUSE is not a real BR, CS, PROBE or SPIKE id: {needed}")
    for a in sorted(archs - used_archs):
        fails.append(f"{a} has no DELTA or ENABLE under it")
    report(f"delta: {n} changes checked", fails)


NAME = re.compile(r"`([A-Z][A-Za-z0-9_]*[a-z][A-Za-z0-9_]*)(?:::([A-Za-z_][A-Za-z0-9_]*))?(?:\(\))?`(\s*\(new\))?")


def grep(roots, pattern):
    for repo in roots.split(","):
        r = subprocess.run(["git", "-C", repo, "grep", "-qE", pattern, "--", "*.php"], capture_output=True)
        if r.returncode == 0:
            return True
    return False


def names_in_code(line, made):
    """Names used inside a fenced code block: new X(), X::y(), $v->y() where $v = new X, artisan commands."""
    out = []
    for m in re.finditer(r"(\$\w+)\s*=\s*new\s+([A-Z]\w*)\s*\(", line):
        made[m.group(1)] = m.group(2)
    for m in re.finditer(r"new\s+([A-Z]\w*)\s*\(", line):
        out.append((m.group(1), None))
    for m in re.finditer(r"\b([A-Z]\w*)::([a-zA-Z_]\w*)\s*\(", line):
        out.append((m.group(1), m.group(2)))
    for m in re.finditer(r"(\$\w+)->([a-zA-Z_]\w*)\s*\(", line):
        if m.group(1) in made:
            out.append((made[m.group(1)], m.group(2)))
    for m in re.finditer(r"(?:artisan\s+|command\(\s*')([a-z][\w-]*(?::[\w-]+)+)", line):
        out.append(("command", m.group(1)))
    return out


def name_exists(repo, cls, meth):
    if cls == "command":
        return grep(repo, rf"signature[[:space:]]*=[[:space:]]*['\"]{re.escape(meth)}([^A-Za-z0-9_]|$)")
    ok = grep(repo, rf"(class|interface|trait)[[:space:]]+{cls}([^A-Za-z0-9_]|$)")
    if ok and meth:
        ok = grep(repo, rf"function[[:space:]]+&?{meth}[[:space:]]*\(")
    return ok


def check_names(repo, *paths):
    """Every class, method and command a doc names must exist in one of the repos, unless marked (new).
    repo is a comma-separated list. "Not found" means not in those repos, nothing more.
    vendor/ and sibling apps are often not checked out, so read each miss by hand before calling it wrong."""
    fails = []
    seen = {}
    for p in paths:
        fenced = False
        made = {}
        for n, line in enumerate(open(p, errors="replace"), 1):
            if line.strip().startswith("```"):
                fenced = not fenced
                made = {}
                continue
            found = []
            if fenced:
                found = names_in_code(line, made)
            else:
                found = [(m.group(1), m.group(2)) for m in NAME.finditer(line) if not m.group(3)]
            for cls, meth in found:
                if (cls, meth) in seen:
                    continue
                seen[(cls, meth)] = name_exists(repo, cls, meth)
                if not seen[(cls, meth)]:
                    label = meth if cls == "command" else (f"{cls}::{meth}" if meth else cls)
                    fails.append(f"{os.path.basename(p)}:{n} not found: {label}")
    report(f"names: {len(seen)} checked in {repo}", fails)


SLICE_FILES = ("map.txt", "gaps.txt", "pm-answers.md")
SLICE_IDS = {"R": re.compile(r"\bR(\d+)\b"), "U": re.compile(r"\bU(\d+)\b"), "GAP ": re.compile(r"\bGAP (\d+)\b")}
CORRECTION_ID = re.compile(r"\bC(\d+)\b")


def slice_name(path):
    """The slice dir's name. review-prd writes into out/, so a dir named out takes its parent's name."""
    path = os.path.abspath(path)
    name = os.path.basename(path)
    return os.path.basename(os.path.dirname(path)) if name == "out" else name


def renumber(text, k, answers):
    """Slice k (1-based) gets ids k*100+n. Every reference to an R, U, GAP or (in answers) C id moves with it."""
    pats = dict(SLICE_IDS)
    if answers:
        pats["C"] = CORRECTION_ID
    for prefix, pat in pats.items():
        text = pat.sub(lambda m: f"{prefix}{k * 100 + int(m.group(1))}", text)
    return text


def merge(out_dir, *slice_dirs):
    """Combine the review-prd outputs of several PRD slices into one set of inputs for a single EDD."""
    fails = []
    names = [slice_name(d) for d in slice_dirs]
    for n in sorted({n for n in names if names.count(n) > 1}):
        fails.append(f"two slices are named {n}")
    texts = []
    for k, (d, name) in enumerate(zip(slice_dirs, names), 1):
        row = {}
        for f in SLICE_FILES:
            path = os.path.join(d, f)
            if not os.path.isfile(path):
                hint = ". Write it from templates/pm-answers.md" if f == "pm-answers.md" else ""
                fails.append(f"slice {name} is missing {f}{hint}")
                continue
            row[f] = open(path, errors="replace").read()
            pats = list(SLICE_IDS.values()) + ([CORRECTION_ID] if f == "pm-answers.md" else [])
            for pat in pats:
                for m in pat.finditer(row[f]):
                    if int(m.group(1)) >= 100:
                        fails.append(f"slice {name} {f} has id {m.group(0)}, 100 or above")
        texts.append(row)
    if not fails:
        os.makedirs(out_dir, exist_ok=True)
        for f in SLICE_FILES:
            body = "".join(f"# SLICE {k} | {name}\n{renumber(row[f], k, f == 'pm-answers.md').rstrip()}\n\n"
                           for k, (name, row) in enumerate(zip(names, texts), 1))
            open(os.path.join(out_dir, f), "w").write(body)
        with open(os.path.join(out_dir, "slices.txt"), "w") as fh:
            for k, (d, name) in enumerate(zip(slice_dirs, names), 1):
                fh.write(f"SLICE {k} | {name} | R{k}01-R{k}99 | {os.path.abspath(d)}\n")
    report(f"merge: {len(slice_dirs)} slices into {out_dir}", fails)


if __name__ == "__main__":
    cmd, *args = sys.argv[1:]
    {
        "blast": check_blast,
        "current": check_blast,
        "delta": check_delta,
        "sections": check_sections,
        "coverage": check_coverage,
        "hazards": check_hazards,
        "names": check_names,
        "spikes": check_spikes,
        "evidence": check_evidence,
        "diagrams": check_diagrams,
        "merge": merge,
        "writing": check_writing,
    }[cmd](*args)
    sys.exit(1 if FAILED else 0)
