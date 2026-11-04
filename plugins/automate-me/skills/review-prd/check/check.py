"""Deterministic checks for review-prd output. Never reads key.md.

Usage:
  python3 check.py map             <prd.md> <map.txt>
  python3 check.py scenarios       <gaps.txt> <rules-dir> [map.txt]
  python3 check.py check-scenarios <prd.md> <gaps.txt> <rules-dir> [map.txt]
  python3 check.py pm-list         <open-questions.md> <rules-dir> [jargon.txt]
  python3 check.py sort            <prd.md> <questions.txt> <open-questions.md>
  python3 check.py premise         <premise.txt> <open-questions.md>
  python3 check.py terms           <prd.md> <terms.txt> [open-questions.md]
  python3 check.py gaps            <prd.md> <gaps.txt>
  python3 check.py writing         <open-questions.md>
  python3 check.py open-questions  <open-questions.md> [prd-labels.txt]
  python3 check.py fresh           <prd.md as read> <prd.md fetched now>

-h prints this and exits 0. A missing argument or unknown command prints it and exits 2.
"""
import inspect
import json
import re
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "shared"))
from check_writing import check_writing  # noqa: E402


def norm(s):
    s = s.strip().strip('"').strip("'").strip()
    return re.sub(r"\s+", " ", s)


def in_prd(quote, prd):
    q = norm(quote)
    return q == "not stated" or q in prd


def check_map(prd_path, map_path):
    prd = norm(open(prd_path).read())
    fails = []
    branch = None
    placed = {}
    for line in open(map_path):
        raw = line.rstrip("\n")
        s = raw.strip()
        if not s or s.startswith("COUNTS"):
            continue
        if s.startswith("BRANCH:"):
            branch = s[len("BRANCH:"):].strip()
            continue
        if s.rstrip(":") in ("UNPLACED", "CONTEXT", "OUT OF SCOPE"):
            branch = s.rstrip(":")
            continue
        m = re.match(r"^(GOAL|R\d+|U\d+):\s*(.*)$", s)
        quote = m.group(2) if m else s
        if not in_prd(quote, prd):
            fails.append(f"quote not in PRD: {s[:70]}")
        if m and m.group(1).startswith("R"):
            placed.setdefault(m.group(1), []).append(branch)
    for r, bs in placed.items():
        if len(bs) != 1:
            fails.append(f"{r} placed {len(bs)} times: {bs}")
    fails += order_and_coverage(prd_path, map_path)
    report(f"map: {len(placed)} points placed", fails)


def sentences(text):
    return [s for s in re.split(r"(?<=[.?!])\s+", norm(text)) if s]


def order_and_coverage(prd_path, map_path):
    fails = []
    prd = norm(open(prd_path).read())
    quotes = []
    rs = []
    for line in open(map_path):
        s = line.strip()
        m = re.match(r"^(GOAL|R\d+|U\d+):\s*(.*)$", s)
        if m:
            quotes.append(m.group(2))
            if m.group(1).startswith("R"):
                rs.append((int(m.group(1)[1:]), norm(m.group(2))))
        elif s and not s.startswith(("BRANCH:", "COUNTS")) and s.rstrip(":") not in ("UNPLACED", "CONTEXT", "OUT OF SCOPE"):
            quotes.append(s)
    rs.sort()
    positions = [prd.find(q) for _, q in rs]
    if positions != sorted(positions):
        fails.append("R numbers are not in PRD order")
    mapped = norm(" ".join(quotes))
    for raw in open(prd_path):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = re.sub(r"^(\d+\.|-)\s+", "", line)
        for sent in sentences(line):
            if sent not in mapped:
                fails.append(f"PRD sentence not placed: {sent[:60]}")
    return fails


def load_rules(rules_path):
    """rules_path is a rules directory, or one rules file. A file holds one rule or {"sets": [...]}."""
    paths = [rules_path]
    if os.path.isdir(rules_path):
        paths = sorted(os.path.join(rules_path, f) for f in os.listdir(rules_path) if f.endswith(".json"))
    rules = []
    for p in paths:
        data = json.load(open(p))
        rules.extend(data["sets"] if "sets" in data else [data])
    return rules


def map_shape(map_path):
    """System branches in map order, and whether the Between branch has any point."""
    systems, between_points, branch = [], 0, None
    if not map_path:
        return systems, False
    for line in open(map_path):
        s = line.strip()
        if s.startswith("BRANCH:"):
            branch = s[len("BRANCH:"):].strip()
            if branch not in ("Between", "Result"):
                systems.append(branch)
        elif s.rstrip(":") in ("UNPLACED", "CONTEXT", "OUT OF SCOPE"):
            branch = None
        elif branch == "Between" and re.match(r"^R\d+:", s):
            between_points += 1
    return systems, between_points > 0


def expected_scenarios(gaps_path, rules_path, map_path=None):
    ops = set()
    for line in open(gaps_path):
        m = re.match(r"^TAG:\s*R\d+\s*\|\s*(\w+)\s*\|", line.strip())
        if m:
            ops.add(m.group(1).lower())
    systems, between = map_shape(map_path)
    out = []
    for rule in load_rules(rules_path):
        if rule["type"] == "tag-coverage":
            for op in rule["expected"]:
                if op not in ops:
                    out.append((rule["name"], rule["scenario"].format(op=op)))
        elif rule["type"] == "prd-questions":
            for q in rule["questions"]:
                out.append((rule["name"], q))
        elif rule["type"] == "shape-questions":
            t = rule["trigger"]
            if len(systems) < t.get("min_system_branches", 2):
                continue
            if t.get("between_has_points") and not between:
                continue
            a, b = systems[0], systems[1]
            for frm, to in ((a, b), (b, a)):
                for q in rule.get("each_direction", []):
                    out.append((rule["name"], q.format(**{"from": frm, "to": to, "A": a, "B": b})))
            for q in rule.get("once", []):
                out.append((rule["name"], q.format(A=a, B=b)))
    return out


def list_scenarios(gaps_path, rules_path, map_path=None):
    if not any(line.strip().startswith("TAG:") for line in open(gaps_path)):
        report("scenarios", [f"no TAG lines in {gaps_path}; run prd-gaps step 2 first, or every operation reads as missing"])
        sys.exit(1)
    for i, (name, text) in enumerate(expected_scenarios(gaps_path, rules_path, map_path), 1):
        print(f"SCENARIO {i}: {name} | {text} | <quote or not stated>")


def check_scenarios(prd_path, gaps_path, rules_path, map_path=None):
    prd = norm(open(prd_path).read())
    fails = []
    found = {}
    for line in open(gaps_path):
        s = line.strip()
        if s.startswith("SCENARIO"):
            parts = [p.strip() for p in s.split(":", 1)[1].split("|")]
            if len(parts) != 3:
                fails.append(f"scenario needs 3 fields: {s[:70]}")
                continue
            found[(parts[0], parts[1])] = parts[2]
            if not in_prd(parts[2], prd):
                fails.append(f"scenario quote not in PRD: {s[:70]}")
    expected = expected_scenarios(gaps_path, rules_path, map_path)
    for key in expected:
        if key not in found:
            fails.append(f"scenario missing: {key[0]} | {key[1]}")
    for key in found:
        if key not in expected:
            fails.append(f"scenario not from a rule: {key[0]} | {key[1]}")
    report(f"scenarios: {len(expected)} expected", fails)


def block_questions(path):
    """(number, text) for every bold-numbered question in the paste-in block."""
    out = []
    for raw in open(path):
        m = QUESTION_LINE.match(raw.strip())
        if m:
            out.append((int(m.group(1)), m.group(2)))
    return out


def ask_key(q):
    """The question's last sentence, the ask, so a row matches its question in the block with or without the situation."""
    asks = re.findall(r"[^.?!]*\?", norm(q))
    return question_key(asks[-1] if asks else q)


MAX_ASKS = 3
MAX_WORDS = 45
MEETING = 25


def check_pm_list(block_path, rules_path, jargon_path=None):
    """Each question is one situation with at most three asks and at most MAX_WORDS words, none repeats,
    none uses a jargon-list word, and the purpose question comes first when it is asked.
    Past one review meeting's worth it warns."""
    asked = block_questions(block_path)
    jargon = []
    if jargon_path:
        jargon = [w.strip().lower() for w in open(jargon_path) if w.strip() and not w.startswith("#")]
    fails = []
    purpose = next((r["questions"][0] for r in load_rules(rules_path) if r.get("name") == "prd-basics"), None)
    keys = [ask_key(q) for _, q in asked]
    if purpose and question_key(purpose) in keys and keys[0] != question_key(purpose):
        fails.append(f"the purpose question is asked but not first: {asked[0][1][:60]}")
    seen = {}
    for (n, q), key in zip(asked, keys):
        if key in seen:
            fails.append(f"Q{n} asks the same as Q{seen[key]}")
        seen.setdefault(key, n)
        if not 1 <= q.count("?") <= MAX_ASKS:
            fails.append(f"Q{n} has {q.count('?')} question marks, needs 1 to {MAX_ASKS}")
        words = len(q.split())
        if words > MAX_WORDS:
            fails.append(f"Q{n} has {words} words, at most {MAX_WORDS}: cut the background, not the ask")
        for w in jargon:
            if re.search(rf"\b{re.escape(w)}\b", q.lower()):
                fails.append(f"Q{n} uses jargon: {w}")
    report(f"pm-list: {len(asked)} questions", fails)
    if len(asked) > MEETING:
        print(f"WARN {len(asked)} questions, more than one review meeting ({MEETING}): merge questions about the same "
              "situation and drop any that fail the test; never cut by rank")


SORT_TAGS = {"PM", "DESIGN-DOC", "ANSWERED", "DROP"}


def check_sort(prd_path, questions_path, block_path):
    """Every question is tagged, every PM reason names what we would guess,
    every ANSWERED cites the PRD, and the block asks only PM questions."""
    prd = norm(open(prd_path).read())
    fails, tags = [], {}
    for line in open(questions_path):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = [p.strip() for p in s.split("|")]
        if len(parts) != 4 or parts[0] not in SORT_TAGS:
            fails.append(f"needs <tag> | <question> | <intent> | <reason>: {s[:70]}")
            continue
        tag, question, intent, reason = parts
        if not intent or not reason:
            fails.append(f"{tag} row needs an intent and a reason: {question[:60]}")
        if tag == "PM" and not reason.lower().startswith("we would guess"):
            fails.append(f"PM reason must start 'We would guess' and name what a user or customer would notice: {question[:60]}")
        if tag == "ANSWERED" and not all(norm(q) != "not stated" and in_prd(q, prd) for q in reason.split(" + ")):
            fails.append(f"ANSWERED reason is not a PRD quote, or quotes joined by ' + ': {question[:60]}")
        tags[ask_key(question)] = tag
    for n, q in block_questions(block_path):
        tag = tags.get(ask_key(q))
        if tag != "PM":
            fails.append(f"Q{n} is in the block but tagged {tag or 'nothing'}")
    report(f"sort: {len(tags)} questions, {sum(t == 'PM' for t in tags.values())} PM", fails)


def check_carry(gaps_path, questions_path, carried_path):
    """Every PM or Unclear wording gap reaches a row in questions.txt, even if that row is a DROP."""
    rows = set()
    for line in open(questions_path):
        parts = [x.strip() for x in line.split("|")]
        if len(parts) == 4 and parts[0] in SORT_TAGS:
            rows.add(ask_key(parts[1]))
    carried = {}
    for line in open(carried_path):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        m = re.match(r"^GAP (\d+) \| (.+)$", s)
        if m:
            carried.setdefault(m.group(1), []).append(m.group(2))
    fails, n = [], 0
    for line in open(gaps_path):
        m = re.match(r"^GAP (\d+):(.*)$", line.strip())
        if not m:
            continue
        parts = [x.strip() for x in m.group(2).split("|")]
        if len(parts) != 4 or parts[2] not in ("PM", "Unclear wording"):
            continue
        n += 1
        targets = carried.get(m.group(1))
        if not targets:
            fails.append(f"GAP {m.group(1)} ({parts[2]}) reaches no row in {questions_path}: {parts[1][:60]}")
        for q in targets or []:
            if ask_key(q) not in rows:
                fails.append(f"GAP {m.group(1)} points at a question not in {questions_path}: {q[:60]}")
    report(f"carry: {n} PM or Unclear wording gaps", fails)


def question_key(q):
    return re.sub(r"[^a-z0-9 ]", "", norm(q).lower())


def check_premise(premise_path, block_path):
    """Every question in the block went through the product check, and none rests on an ambiguous noun."""
    fails, rows = [], {}
    for line in open(premise_path):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = [p.strip() for p in s.split("|")]
        if len(parts) != 3 or not all(parts):
            fails.append(f"needs <question> | <noun or claim> | <evidence>: {s[:70]}")
            continue
        rows.setdefault(ask_key(parts[0]), []).append((parts[1], parts[2]))
    asked = block_questions(block_path)
    for n, q in asked:
        found = rows.get(ask_key(q))
        if not found:
            fails.append(f"Q{n} has no rows in {premise_path}; run step 8 on it")
            continue
        for noun, evidence in found:
            if evidence.lower().startswith("ambiguous"):
                fails.append(f"Q{n} relies on an ambiguous noun: {noun}")
    report(f"premise: {len(asked)} questions checked", fails)


def term_count(term, text):
    return len(re.findall(rf"\b{re.escape(term)}s?\b", text, re.I))


def check_terms(prd_path, terms_path, block_path=None):
    """Each term in terms.txt is the PRD's most common name for its thing,
    and the block's questions use none of the other names."""
    if not os.path.exists(terms_path):
        report("terms", [f"{terms_path} missing; write it before drafting"])
        return
    prd = open(prd_path).read()
    fails, counts, others = [], {}, []
    for line in open(terms_path):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = [p.strip() for p in s.split("|")]
        if len(parts) != 3 or not parts[0] or not parts[1]:
            fails.append(f"needs <what> | <the PRD's term> | <other names, comma separated>: {s[:70]}")
            continue
        what, term, names = parts
        n = term_count(term, prd)
        counts[what.lower()] = f"{term} {n}"
        if n == 0:
            fails.append(f"{what}: the PRD never says {term}")
        for other in (o.strip() for o in names.split(",")):
            if not other or other.lower() == "none":
                continue
            m = term_count(other, prd)
            if m > n:
                fails.append(f"{what}: the PRD says {other} {m} times and {term} {n}")
            others.append((what, term, other))
    for need in ("product", "customer"):
        if need not in counts:
            fails.append(f"no {need} row")
    if block_path:
        for n, text in block_questions(block_path):
            for what, term, other in others:
                if term_count(other, text):
                    fails.append(f"Q{n} says {other}; the PRD calls the {what} {term}")
    report("terms: " + ", ".join(f"{w} {c}" for w, c in counts.items()), fails)


DEFERS = re.compile(r"\bTBD\b|\bto be (decided|determined|confirmed)\b|\bworking assumption\b", re.I)


def check_gaps(prd_path, gaps_path):
    prd = norm(open(prd_path).read())
    fails = []
    n = 0
    owners = {"PM", "Engineer", "Unclear wording"}
    deferred, gap_quotes = [], set()
    for line in open(gaps_path):
        s = line.strip()
        if s.startswith("SCENARIO"):
            parts = [p.strip() for p in s.split(":", 1)[1].split("|")]
            if len(parts) == 3 and DEFERS.search(parts[2]):
                deferred.append(parts[2])
        elif s.startswith("TAG:"):
            parts = [p.strip() for p in s[4:].split("|")]
            if len(parts) != 3 or not in_prd(parts[2], prd):
                fails.append(f"bad tag: {s[:70]}")
        elif s.startswith("GAP"):
            n += 1
            parts = [p.strip() for p in s.split(":", 1)[1].split("|")]
            if len(parts) != 4:
                fails.append(f"gap needs 4 fields: {s[:70]}")
                continue
            if not re.match(r"^(R|U)\d+", parts[0]):
                fails.append(f"gap has no point number: {s[:70]}")
            if parts[2] not in owners:
                fails.append(f"gap owner invalid: {s[:70]}")
            if not in_prd(parts[3], prd):
                fails.append(f"gap quote not in PRD: {s[:70]}")
            gap_quotes.add(norm(parts[3]))
    for quote in deferred:
        if norm(quote) not in gap_quotes:
            fails.append(f"scenario answer puts the decision off but has no gap: {quote[:60]}")
    report(f"gaps: {n} checked", fails)


MAX_GLOSSARY = 6
MAX_BIGGEST = 8
QUESTION_LINE = re.compile(r"^\*\*(\d+)\.\*\*\s+(.*)$")
NOT_FOR_THE_PM = [
    (re.compile(r"^Proposed:|\bProposed:"), "a proposed default"),
    (re.compile(r'Reply "?yes'), "a reply-yes prompt"),
    (re.compile(r"\(\s*[RU]\d+|\b[RU]\d+\b"), "a point number"),
    (re.compile(r"§|\bFR\d+"), "a PRD section or requirement number"),
    (re.compile(r"\b[\w/]+\.(php|py|js|ts|rb|sql)\b|\w:\d+\b"), "a file path or line"),
]


def check_open_questions(path, labels_path=None):
    """The paste-in block follows templates/open-questions.md."""
    lines = [l.rstrip("\n") for l in open(path)]
    body = [l.strip() for l in lines if l.strip()]
    fails = []
    if not body or not re.match(r"^(#{1,3}\s+)?(\*\*)?(Test plan questions|Questions) from engineering \(\S.*\)(\*\*)?$", body[0]):
        fails.append("first line is not '[Test plan q|Q]uestions from engineering (<name>, <Mon YYYY>)'")
    if len(body) < 2 or body[1] != "Please answer under each question.":
        fails.append("second line is not exactly 'Please answer under each question.'")
    glossary = [l for l in body if re.match(r"^- \*\*[^*]+\.\*\*\s", l)]
    has_intro = any(re.match(r"^\w+ terms? used below:$", l) for l in body)
    if glossary and not has_intro:
        fails.append("glossary has no '<n> terms used below:' line")
    if has_intro and not glossary:
        fails.append("'terms used below' line with no terms; drop the line")
    if len(glossary) > MAX_GLOSSARY:
        fails.append(f"glossary has {len(glossary)} terms, at most {MAX_GLOSSARY}")
    if "**Biggest decisions**" not in body:
        fails.append("no '**Biggest decisions**' group")
    smaller = body.index("**Smaller questions, by topic**") if "**Smaller questions, by topic**" in body else len(body)
    questions = []
    for i, l in enumerate(body):
        m = QUESTION_LINE.match(l)
        if m:
            questions.append((int(m.group(1)), m.group(2), i < smaller))
        elif re.match(r"^(- )?(\d+)\.\s", l) or re.match(r"^- \*\*\d+\.\*\*", l):
            fails.append(f"question not numbered as bold text on its own line: {l[:50]}")
    for i, (n, _, _) in enumerate(questions, 1):
        if n != i:
            fails.append(f"numbering breaks at {n}, expected {i}")
            break
    biggest = sum(1 for _, _, big in questions if big)
    if biggest > MAX_BIGGEST:
        fails.append(f"{biggest} biggest decisions, at most {MAX_BIGGEST}")
    labels = []
    if labels_path:
        labels = [w.strip() for w in open(labels_path) if w.strip() and not w.startswith("#")]
    for n, text, _ in questions:
        if "?" not in text:
            fails.append(f"Q{n} asks nothing")
        for pattern, what in NOT_FOR_THE_PM:
            if pattern.search(text):
                fails.append(f"Q{n} has {what}")
        plain = re.sub(r'\(?the PRD calls (it|them) "[^"]+"\)?', "", text, flags=re.I)
        for label in labels:
            if re.search(rf"\b{re.escape(label)}\b", plain, re.I):
                fails.append(f"Q{n} uses the PRD label {label}; use the glossary's plain term")
    if not questions and any(l.strip() == "No questions." for l in body):
        fails = [f for f in fails if not f.startswith(("second line", "no '**Biggest", "no '<n>"))]
    report(f"open-questions: {len(glossary)} terms, {biggest} biggest, {len(questions)} questions", fails)


def prd_sentences(path):
    out = []
    for raw in open(path):
        line = re.sub(r"^(#+|\d+\.|[-*])\s+", "", raw.strip())
        out += sentences(line)
    return out


def check_fresh(read_path, now_path):
    """The PRD fetched now says what the PRD the review read says, sentence by sentence."""
    then, now = prd_sentences(read_path), prd_sentences(now_path)
    fails = [f"removed: {s[:70]}" for s in then if s not in now]
    fails += [f"added: {s[:70]}" for s in now if s not in then]
    report(f"fresh: {len(now)} sentences in the PRD now, {len(fails)} changed", fails)


FAILED = []


def report(label, fails):
    if fails:
        FAILED.append(label)
    print(f"{'FAIL' if fails else 'PASS'} {label}")
    for f in fails:
        print(f"  {f}")


def writing(path):
    """The shared check prints its own result. Its failures also fail this script."""
    if check_writing(path):
        FAILED.append("writing")


COMMANDS = {
    "map": check_map,
    "scenarios": list_scenarios,
    "check-scenarios": check_scenarios,
    "gaps": check_gaps,
    "carry": check_carry,
    "pm-list": check_pm_list,
    "sort": check_sort,
    "premise": check_premise,
    "terms": check_terms,
    "writing": writing,
    "open-questions": check_open_questions,
    "fresh": check_fresh,
}


def main(args):
    if any(a in ("-h", "--help") for a in args):
        print(__doc__.strip())
        return 0
    fn = COMMANDS.get(args[0]) if args else None
    if fn:
        params = inspect.signature(fn).parameters.values()
        need = sum(p.default is p.empty for p in params)
        if need <= len(args) - 1 <= len(params):
            fn(*args[1:])
            return 1 if FAILED else 0
    print(__doc__.strip(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
