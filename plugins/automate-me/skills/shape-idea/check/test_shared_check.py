"""Run: python3 check/test_shared_check.py [item1 ... item9]

Every value goes through one shared check, so a fix reaches every slot. Each item below is one rule of that check.
With no argument every item runs. With names, only those run. The property items use a fixed seed and stay fast.
"""
import contextlib
import io
import os
import random
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(SKILLS, "outcome", "check"))
sys.path.insert(0, os.path.join(SKILLS, "shared"))
from check_brief import ask_lines, check as brief_check  # noqa: E402
from check_decisions import main as check_main  # noqa: E402
from check_writing import check_writing  # noqa: E402
from map_decisions import main as map_main  # noqa: E402

CHECK = os.path.join(HERE, "check_decisions.py")
MAP = os.path.join(SKILLS, "outcome", "check", "map_decisions.py")
SEED = 8
FAILS, RAN = [], []

GOOD = """# Decisions: bake sale poster

## Decided

- goal: a poster for the school bake sale
- done: the poster hangs on the hall board by Friday
- output: one printed poster with the date and the price list
- verify: a parent reads the date and three prices from across the hall
- constraints: one page, black and white
- the sale is in the gym

## Open

- Should the poster show the cake photos?

## Parked

- a second poster for the library

## Handoff

- next: /automate-me:outcome
- stop: done
- turns: 2
- writing: pass
- map: goal goes to Goal. done goes to Done. output goes to Output. constraints goes to Constraints. verify goes to Verification. Tools, Agents and roles, and Evals stay unknown.
"""
OUT = "- output: one printed poster with the date and the price list"
LAST = "- the sale is in the gym"
OPEN = "- Should the poster show the cake photos?"
PARK = "- a second poster for the library"


def swap(old, new, text=GOOD):
    assert old in text, old
    return text.replace(old, new, 1)


def write(text, confirmed=None):
    folder = tempfile.mkdtemp()
    path = os.path.join(folder, "decisions.md")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    if confirmed is not None:
        with open(os.path.join(folder, "confirmed.md"), "w", encoding="utf-8") as handle:
            handle.write(confirmed)
    return path


def run(entry, path):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = entry(path)
    return code, out.getvalue()


def items(said):
    """{slot, value, Why, Ask, Suggest} for each CHECK WITH ME item."""
    found = []
    if "CHECK WITH ME (" not in said:
        return found
    for line in said.split("CHECK WITH ME (", 1)[1].splitlines()[1:]:
        head = re.match(r'^- (?P<slot>[^:]+): "(?P<value>.*)"$', line)
        field = re.match(r"^  (Why|Ask|Suggest): (.*)$", line)
        if head:
            found.append({"slot": head["slot"], "value": head["value"]})
        elif field and found:
            found[-1][field.group(1)] = field.group(2)
    return found


def brief_exit(brief):
    if any(fails for _, fails in brief_check(brief)):
        return 1
    return 2 if ask_lines(brief) else 0


def flow(text, confirmed=None):
    """(checker exit, mapper exit, CHECK WITH ME items, brief or '')."""
    path = write(text, confirmed)
    code, said = run(check_main, path)
    mcode, brief = run(map_main, path)
    return code, mcode, items(said), brief if mcode == 0 else "", said


def yes_all(found):
    return "".join(f"- {item['slot']}: {item['value']} | yes\n" for item in found)


def expect(name, ok, why=""):
    RAN.append(name)
    if not ok:
        FAILS.append(f"{name}: {why}")


def listed_then_clear(name, text, slot, value):
    """Exit 2 from both scripts with the item; after a yes for every item, exit 0 and a brief that passes."""
    code, mcode, found, brief, said = flow(text)
    mine = [item for item in found if (item["slot"], item["value"]) == (slot, value)]
    expect(f"{name}: listed", (code, mcode) == (2, 2) and len(mine) == 1,
           f"exits {code}, {mcode}, items {[(i['slot'], i['value']) for i in found]}\n{said[-700:]}")
    code, mcode, _, brief, said = flow(text, yes_all(found))
    expect(f"{name}: a yes clears it", (code, mcode) == (0, 0), f"exits {code}, {mcode}\n{said[-700:]}")
    expect(f"{name}: the brief passes", code == 0 and brief and brief_exit(brief) == 0, brief[-700:])


def item1():
    """A placeholder word joined to a word by punctuation is listed, never passed."""
    for value in ("a card/TBD", "poster-TBD", "flyer,TBD", "a menu (TBD)", "price: TBD"):
        listed_then_clear(f"item1 {value}", swap(OUT, f"- output: {value}"), "Output", value)


def item2():
    """Literal `[Insert card]` under write first: is listed, and a yes lets a passing brief through."""
    value = "a sign by the till that says [Insert card]"
    listed_then_clear("item2 write first", swap(LAST, f"{LAST}\n- write first: {value}"), "Tools", value)


def item3():
    """Evals in should pass / should fail wording with a code-quoted N/A is listed, and a yes lets it through."""
    value = "`N/A` should pass, a blank form should fail."
    listed_then_clear("item3 phrase evals", swap(LAST, f"{LAST}\n- evals: {value}"), "Evals", value)


def item4():
    """An Open line is a question when it ends in a question mark. A mark in the middle only is listed."""
    value = "Should the sale close at noon? Ask the head teacher on Friday."
    listed_then_clear("item4 open mid mark", swap(OPEN, f"- {value}"), "Unknowns", value)
    for value in ("**Should the poster show the cake photos?**", "Should it say 'Sold out?' or 'Gone'?",
                  "ケーキの写真を載せる？"):
        code, mcode, found, _, said = flow(swap(OPEN, f"- {value}"))
        expect(f"item4 open ends in a mark: {value}", (code, mcode) == (0, 0) and not found, said[-500:])
    rule = "An Open line is a question when it ends in a question mark"
    for doc in ("SKILL.md", "README.md"):
        with open(os.path.join(SKILLS, "shape-idea", doc), encoding="utf-8") as handle:
            body = handle.read()
        expect(f"item4 {doc} states the rule", rule in body and "Any question mark makes it a question" not in body,
               f"{doc} lacks {rule!r} or keeps the old rule")


def item5():
    """One Evals line gives one item. When its cases are missing, that advice wins."""
    for value in ("maybe show the sign [Insert card]", "maybe a form with a date", "a form/TBD"):
        code, _, found, _, said = flow(swap(LAST, f"{LAST}\n- evals: {value}"))
        evals = [item for item in found if item["slot"] == "Evals"]
        expect(f"item5 one evals item: {value}",
               code == 2 and len(evals) == 1 and evals[0]["value"] == value
               and "pass" in evals[0].get("Why", "") and "confirm" not in evals[0].get("Suggest", "confirm"),
               f"exit {code}, items {evals}\n{said[-600:]}")


ROUTES = {
    "output": lambda v: swap(OUT, f"- output: {v}"),
    "done line": lambda v: swap(LAST, f"{LAST}\n- {v}"),
    "tools": lambda v: swap(LAST, f"{LAST}\n- tools: {v}"),
    "agents": lambda v: swap(LAST, f"{LAST}\n- agents: {v}"),
    "write first": lambda v: swap(LAST, f"{LAST}\n- write first: {v}"),
    "decide": lambda v: swap(LAST, f"{LAST}\n- decide: {v}"),
    "out of scope": lambda v: swap(LAST, f"{LAST}\n- out of scope: {v}"),
    "evals case": lambda v: swap(LAST, f"{LAST}\n- evals: pass: {v}; fail: a blank form"),
    "parked limit": lambda v: swap(PARK, f"{PARK}\n- out of scope: {v}"),
}
TEXT_ROUTES = {
    "parked": lambda v: swap(PARK, f"{PARK}\n- {v}"),
    "open": lambda v: swap(OPEN, f"{OPEN}\n- {v}"),
}
BASES = ["a card", "the poster", "a flyer for the fair", "one price list"]
SHAPES = [
    "{b}/TBD", "{b}-TBD", "{b},TBD", "{b} (TBD)", "TBD/{b}", "{b}/N/A", "{b}, to be decided",
    "{b} [Insert card]", "[Insert card] on {b}", "[insert the name]", "{b} [insert]",
    '{b} that says "Ready?"', "{b} with 'Sold out' on it", "`N/A`", "{b} with `TBD` on it", "`[Insert card]` on {b}",
    "{b}？", "{b}؟", "{b}? for the hall", "maybe {b}", "{b}, not sure", "probably {b}", "{b}: unknown", "unknown",
    "{b} that looks clean", "{b} on <Enter>", "<goal>", "none", "ok", "TBD", "N/A", "{b}",
    "todo: maybe", "todo: {b}", "how: {b}", "investigate: {b}", "default to {b}",
    # Long values stay under the writing check's sentence limit in every slot, so only the shared check decides.
    "{b} with a big red heading, the date, the hall number and the price of each cake",
    "Show [Insert the red card in the first slot and the blue card next to the till].",
    "{b} with a note [Insert the price of each cake and the name of each baker], maybe",
    # Backticks the writing check and the brief check read in different ways. A Why must not echo the word inside.
    "{b} ` [Insert ensure] ``",
]


def values():
    rng = random.Random(SEED)
    out = []
    for shape in SHAPES:
        out += sorted({shape.format(b=rng.choice(BASES)) for _ in range(2)})
    return out


def outcome(text):
    """'error', 'check' or 'ok' for one decisions text, and the printed items."""
    code, said = run(check_main, write(text))
    return {0: "ok", 1: "error", 2: "check"}.get(code, f"exit {code}"), items(said)


def ends_in_question(value):
    return value.rstrip("*_`'\" .)").endswith(("?", "？", "؟"))


def item9():
    """The same text gets the same verdict in every slot it can appear in."""
    start = __import__("time").time()
    for value in values():
        got = {route: outcome(make(value))[0] for route, make in ROUTES.items()}
        expect(f"item9 one verdict in every decided slot: {value!r}", len(set(got.values())) == 1, str(got))
        text = {route: outcome(make(value))[0] for route, make in TEXT_ROUTES.items()}
        answer = got["output"]
        # A Parked line is not a decision, so only the text checks apply: an error there is an error everywhere,
        # and a listed text is listed everywhere.
        expect(f"item9 parked text agrees: {value!r}",
               text["parked"] == answer or (text["parked"] == "ok" and answer == "check"), f"{text} {got}")
        want = text["parked"] if ends_in_question(value) else "error" if text["parked"] == "error" else "check"
        expect(f"item9 open agrees: {value!r}", text["open"] == want, f"{text} {got}")
        if answer == "check":
            for route, make in ROUTES.items():
                code, mcode, found, brief, said = flow(make(value))
                code, mcode, _, brief, said = flow(make(value), yes_all(found))
                expect(f"item9 a yes clears it in {route}: {value!r}",
                       (code, mcode) == (0, 0) and brief_exit(brief) == 0 or route == "evals case" and code == 2,
                       f"exits {code}, {mcode}\n{said[-500:]}\n{brief[-500:]}")
    expect("item9 runs fast", __import__("time").time() - start < 120, "over 120 seconds")


def item6():
    """Every Why, Ask and Suggest passes the shared writing check, also for long values."""
    lines = []
    for value in values():
        for make in list(ROUTES.values()) + list(TEXT_ROUTES.values()):
            for item in outcome(make(value))[1]:
                RAN.append(f"item6 fields: {item['slot']}: {item['value'][:30]}")
                if not all(item.get(name) for name in ("Why", "Ask", "Suggest")):
                    FAILS.append(f"item6 item has no Why, Ask or Suggest: {item}")
                    continue
                questions = re.findall(r"[^?]+\?", item["Ask"])
                if not 1 <= len(questions) <= 3 or "".join(questions).strip() != item["Ask"].strip():
                    FAILS.append(f"item6 Ask is not 1 to 3 questions: {item['Ask']!r}")
                if len(re.findall(r"[.?!](?=\s|$)", item["Why"])) != 1 or len(item["Why"].split()) > 20:
                    FAILS.append(f"item6 Why is not one short sentence: {item['Why']!r}")
                lines += [item["Why"], item["Ask"], item["Suggest"]]
    path = os.path.join(tempfile.mkdtemp(), "fields.md")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n\n".join(lines) + "\n")
    with contextlib.redirect_stdout(io.StringIO()) as said:
        fails = check_writing(path)
    expect("item6 every field passes the writing check", lines and not fails,
           f"{len(lines)} lines, {fails[:5]}\n" + "\n".join(lines[:3]))


def item7():
    """A confirmed.md that is a directory is a usage error, found or named."""
    path = write(GOOD)
    folder = os.path.dirname(path)
    os.mkdir(os.path.join(folder, "confirmed.md"))
    for script in (CHECK, MAP):
        got = []
        for args in ([path], [path, "--confirmed", os.path.join(folder, "confirmed.md")]):
            done = subprocess.run([sys.executable, script, *args], capture_output=True, text=True, encoding="utf-8")
            got.append((done.returncode, done.stdout, done.stderr))
        name = os.path.basename(script)
        expect(f"item7 {name} exits 3 both ways", [g[0] for g in got] == [3, 3], str(got))
        expect(f"item7 {name} one stderr line, the same both ways",
               all(g[1] == "" and g[2].count("\n") == 1 and g[2].startswith("usage:") for g in got)
               and got[0][2] == got[1][2], str(got))


def item8():
    """A replacement answer takes the old value's place, is checked again, and the latest line wins."""
    old = "maybe a poster on the gym door"
    text = swap(OUT, f"- output: {old}")
    new = "a poster on the gym door"
    code, mcode, found, brief, said = flow(text, f"- Output: {old} | {new}\n")
    expect("item8 a replacement clears the item", (code, mcode) == (0, 0), said[-600:])
    expect("item8 the brief holds the new answer", f"- Output: {new}\n" in brief and old not in brief, brief[-600:])
    expect("item8 the brief passes", brief and brief_exit(brief) == 0, brief[-600:])
    code, _, _, brief, said = flow(text, f"- Output: {old} | {new}\n- Output: {old} | yes\n")
    expect("item8 the latest line wins: yes", code == 0 and f"- Output: {old}\n" in brief, said[-600:] + brief[-400:])
    code, _, _, brief, said = flow(text, f"- Output: {old} | yes\n- Output: {old} | {new}\n")
    expect("item8 the latest line wins: replacement", code == 0 and f"- Output: {new}\n" in brief,
           said[-600:] + brief[-400:])
    unsure = "a poster on the gym door, not sure"
    code, _, found, _, said = flow(text, f"- Output: {old} | {unsure}\n")
    expect("item8 a replacement is checked again",
           code == 2 and [(i["slot"], i["value"]) for i in found] == [("Output", unsure)], said[-600:])
    code, _, _, brief, said = flow(text, f"- Output: {old} | {unsure}\n- Output: {unsure} | yes\n")
    expect("item8 a yes clears the replacement", code == 0 and f"- Output: {unsure}\n" in brief, said[-600:])
    code, _, _, _, said = flow(text, f"- Output: {old} | TBD\n")
    expect("item8 a placeholder replacement is format invalid", code == 1, said[-600:])
    code, _, _, brief, said = flow(GOOD, "- Output: something else | a poster\n")
    expect("item8 a stale replacement is a note", code == 0 and "NOTE" in said, said[-600:])
    code, _, _, _, said = flow(swap(LAST, f"{LAST}\n- tools: {old}\n- agents: {old}"), f"- Tools: {old} | {new}\n")
    expect("item8 a replacement names one slot",
           code == 2 and [(i["slot"], i["value"]) for i in items(said)] == [("Agents and roles", old)], said[-600:])
    code, _, _, brief, said = flow(swap(OPEN, "- the cake photos are not settled"),
                                   "- Unknowns: the cake photos are not settled | Should it show the cake photos?\n")
    expect("item8 a replacement for an Open line", code == 0 and "unknown: Should it show the cake photos?" in brief,
           said[-600:] + brief[-400:])

    # Review findings on the replacement path.
    code, _, _, brief, said = flow(swap(LAST, f"{LAST}\n- out of scope: maybe the gym door"),
                                   "- Constraints: out of scope: maybe the gym door | the gym door\n")
    limits = brief.split("- Constraints:", 1)[-1].split("- Tools:", 1)[0]
    expect("item8 a replacement keeps the out of scope label", code == 0 and "out of scope: the gym door" in limits,
           said[-500:] + brief[-600:])
    code, _, _, _, said = flow(swap(OUT, "- output: TBD"), "- Output: TBD | a poster on the gym door\n")
    expect("item8 a replacement never clears a format error", code == 1 and "format error" in said, said[-500:])
    code, _, found, _, said = flow(swap(LAST, f"{LAST}\n- tools: maybe a ribbon\n- write first: probably a ribbon"),
                                   "- Tools: maybe a ribbon | probably a ribbon\n"
                                   "- Tools: probably a ribbon | a printed card\n")
    expect("item8 a replacement reaches every line with that slot and value", code == 0, said[-600:])
    code, _, _, brief, said = flow(swap(OPEN, "- decide: the poster colors are open"),
                                   "- Unknowns: decide: the poster colors are open | Which colors go on the poster?\n")
    expect("item8 an Open replacement keeps its decide label",
           code == 0 and "unknown: Which colors go on the poster?" in brief and "What will you decide" not in brief,
           said[-500:] + brief[-600:])
    code, _, _, brief, said = flow(swap(OUT, "- output: maybe a poster"), "- Output: maybe a poster | a poster | one page\n")
    expect("item8 the first bar splits value and answer", code == 0 and "- Output: a poster | one page\n" in brief,
           said[-500:] + brief[-300:])


def item10():
    """Review findings: a value a label in the brief would change is judged as the brief reads it."""
    value = "todo: maybe"
    got = {route: outcome(make(value))[0] for route, make in ROUTES.items()}
    expect(f"item10 one verdict in every decided slot: {value!r}", len(set(got.values())) == 1, str(got))
    for route, make in ROUTES.items():
        code, mcode, found, _, _ = flow(make(value))
        code, mcode, _, brief, said = flow(make(value), yes_all(found))
        expect(f"item10 a yes clears it in {route}", (code, mcode) == (0, 0) and brief_exit(brief) == 0 or
               route == "evals case" and code == 2, said[-500:])


ITEMS = {f"item{n}": globals()[f"item{n}"] for n in range(1, 11)}

if __name__ == "__main__":
    for name in sys.argv[1:] or ITEMS:
        ITEMS[name]()
    for line in FAILS:
        print(f"FAIL {line}")
    print(f"{len(RAN) - len(FAILS)}/{len(RAN)} passed")
    sys.exit(1 if FAILS else 0)
