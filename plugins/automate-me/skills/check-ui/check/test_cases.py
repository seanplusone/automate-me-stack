import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
MEASURE = os.path.join(HERE, "measure.mjs")
CASES = os.path.join(SKILL, "cases")
SCHEMA = json.load(open(os.path.join(HERE, "report.schema.json")))
RULES = ["G1", "G2", "G3", "G4", "G9"]
ENV_ERROR = re.compile(
    r"Playwright is not installed|Executable doesn't exist|browserType\.launch|Failed to launch|"
    r"error while loading shared libraries|libnss|libgbm|libasound|chrome-headless-shell",
    re.I,
)

passed = 0
failed = 0


def check(name, ok, detail=""):
    global passed, failed
    print(f"{'PASS' if ok else 'FAIL'} {name}")
    if ok:
        passed += 1
        return
    failed += 1
    if detail:
        print("    " + detail.replace("\n", "\n    "))


def type_ok(instance, kind):
    kinds = kind if isinstance(kind, list) else [kind]
    for item in kinds:
        if item == "object" and isinstance(instance, dict):
            return True
        if item == "array" and isinstance(instance, list):
            return True
        if item == "string" and isinstance(instance, str):
            return True
        if item == "boolean" and isinstance(instance, bool):
            return True
        if item == "null" and instance is None:
            return True
        if item == "integer" and isinstance(instance, int) and not isinstance(instance, bool):
            return True
        if item == "number" and isinstance(instance, (int, float)) and not isinstance(instance, bool):
            return True
    return False


def validate(instance, schema, path="$"):
    errors = []
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path} not in {schema['enum']}")
    kind = schema.get("type")
    if isinstance(kind, list):
        if not type_ok(instance, kind):
            errors.append(f"{path} bad type")
        return errors
    if kind == "object":
        if not isinstance(instance, dict):
            return errors + [f"{path} not object"]
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path}.{key} missing")
        extra = schema.get("additionalProperties", True)
        if extra is False:
            for key in instance:
                if key not in props:
                    errors.append(f"{path}.{key} extra")
        elif isinstance(extra, dict):
            for key in instance:
                if key not in props:
                    errors.extend(validate(instance[key], extra, f"{path}.{key}"))
        for key, sub in props.items():
            if key in instance:
                errors.extend(validate(instance[key], sub, f"{path}.{key}"))
    elif kind == "array":
        if not isinstance(instance, list):
            return errors + [f"{path} not array"]
        if len(instance) < schema.get("minItems", 0):
            errors.append(f"{path} shorter than {schema['minItems']}")
        for i, item in enumerate(instance):
            errors.extend(validate(item, schema.get("items", {}), f"{path}[{i}]"))
    elif kind == "string":
        if not isinstance(instance, str):
            errors.append(f"{path} not string")
        elif len(instance) < schema.get("minLength", 0):
            errors.append(f"{path} too short")
    elif kind == "integer":
        if isinstance(instance, bool) or not isinstance(instance, int):
            errors.append(f"{path} not integer")
        elif instance < schema.get("minimum", instance):
            errors.append(f"{path} below minimum")
    elif kind == "number":
        if isinstance(instance, bool) or not isinstance(instance, (int, float)):
            errors.append(f"{path} not number")
    return errors


def run(args, timeout=90):
    return subprocess.run(["node", MEASURE, *args], capture_output=True, text=True, timeout=timeout)


def report_of(result):
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def rows(report, status=None):
    if not report:
        return []
    found = []
    for width in report["widths"]:
        for rule in width["rules"]:
            if status is None or rule["status"] == status:
                found.append((width["width"], rule))
    return found


def fail_ids(report):
    return {rule["id"] for _, rule in rows(report, "fail")}


def statuses(report, width, rule_id):
    return {rule["status"] for w, rule in rows(report) if w == width and rule["id"] == rule_id}


def detail(result, report):
    lines = [f"exit {result.returncode}"]
    if result.stderr.strip():
        lines.append(result.stderr.strip())
    if report:
        for width, rule in rows(report):
            if rule["status"] != "pass":
                lines.append(f"{width} {rule['id']} {rule['status']} {rule['element']} {rule['message']}")
    elif result.stdout.strip():
        lines.append(result.stdout[:2000])
    return "\n".join(lines)


def schema_ok(report):
    return validate(report, SCHEMA) == []


def assert_schema(name, report):
    errors = validate(report, SCHEMA) if report else ["no JSON"]
    check(f"{name} matches the schema", errors == [], "\n".join(errors))


def other_rules_pass(report, banned):
    bad = []
    for width in (390, 1280):
        for rule_id in RULES:
            if rule_id == banned:
                continue
            got = statuses(report, width, rule_id)
            if got != {"pass"}:
                bad.append(f"{width} {rule_id} {got or 'missing'}")
    return bad


clean = os.path.join(CASES, "clean", "index.html")

result = run([])
check("missing --url exits 2", result.returncode == 2 and "verdict" not in result.stdout, result.stderr)

result = run(["--url", clean, "--widths", "wide"])
check("bad width exits 2", result.returncode == 2 and '"verdict"' not in result.stdout, result.stderr)

result = run(["--url", os.path.join(CASES, "missing.html")])
check("missing file exits 2", result.returncode == 2 and '"verdict"' not in result.stdout, result.stderr)

with tempfile.TemporaryDirectory() as tmp:
    out = os.path.join(tmp, "report.json")
    result = run(["--url", os.path.join(CASES, "missing.html"), "--out", out])
    check("a usage error writes no report", result.returncode == 2 and not os.path.exists(out), result.stderr)
    bad = os.path.join(tmp, "bad.json")
    with open(bad, "w") as fh:
        fh.write("{")
    result = run(["--url", clean, "--config", bad])
    check("broken config exits 2", result.returncode == 2 and '"verdict"' not in result.stdout, result.stderr)
    unknown = os.path.join(tmp, "unknown.json")
    with open(unknown, "w") as fh:
        json.dump({"color": "red"}, fh)
    result = run(["--url", clean, "--config", unknown])
    check("unknown config key exits 2", result.returncode == 2 and "unknown config key" in result.stderr, result.stderr)

result = run(["--help"])
check("help exits 0 and is not a report", result.returncode == 0 and "verdict" not in result.stdout, result.stdout)


def skip_browser(why):
    print(f"SKIP browser cases: {why}")
    print("Install from plugins/automate-me/skills/check-ui: npm install && npx playwright install chromium")


probe = run(["--url", clean, "--widths", "390,1280"])
browser_ran = True
if probe.returncode == 2 and ENV_ERROR.search(probe.stderr or ""):
    browser_ran = False
    skip_browser(probe.stderr.strip().splitlines()[0] if probe.stderr.strip() else "browser unavailable")
else:
    legacy = {"clean", "g1-tall-card", "g2-gaps", "g3-padding", "g4-edge", "g9-scroll"}
    cases = sorted(
        name for name in os.listdir(CASES)
        if os.path.isfile(os.path.join(CASES, name, "index.html")) and os.path.isfile(os.path.join(CASES, name, "key.json"))
    )
    check("legacy cases are still present", legacy <= set(cases), " ".join(cases))
    real = []
    for name in cases:
        folder = os.path.join(CASES, name)
        key = json.load(open(os.path.join(folder, "key.json")))
        expected = key["fail"]
        loose = key.get("loose", False)
        widths = ["--widths", "390,1280"]
        timeout = ["--timeout", str(key["timeout"])] if key.get("timeout") else []
        started = time.time()
        result = probe if name == "clean" and not timeout else run(["--url", os.path.join(folder, "index.html"), *widths, *timeout])
        elapsed = time.time() - started
        report = report_of(result)
        if expected == "inconclusive":
            check(
                f"{name} is inconclusive",
                result.returncode == 2 and '"verdict": "pass"' not in result.stdout and (not report or report.get("verdict") == "inconclusive"),
                detail(result, report),
            )
            if key.get("maxSeconds"):
                check(f"{name} finishes within {key['maxSeconds']}s", elapsed < key["maxSeconds"], f"{elapsed:.1f}s")
            if report:
                assert_schema(name, report)
            continue
        want = 0 if expected is None else 1
        if not key.get("allowReview") and not key.get("review"):
            check(f"{name} exits {want}", result.returncode == want, detail(result, report))
        if not report:
            check(f"{name} prints JSON", False, result.stdout[:500] + result.stderr[:500])
            continue
        assert_schema(name, report)
        if result.returncode == 3:
            crops = report.get("review") or []
            crop_ok = bool(crops) and all(row.get("shot") and os.path.isfile(row["shot"]) and os.path.getsize(row["shot"]) > 32 for row in crops)
            check(f"{name} crops every review row", crop_ok, " ".join((row.get("shot") or "(missing)") for row in crops))
        check(f"{name} widths are 390 and 1280", [w["width"] for w in report["widths"]] == [390, 1280], detail(result, report))
        got = fail_ids(report)
        want_ids = set() if expected is None else {expected}
        messages = " ".join(rule["message"] for _, rule in rows(report))
        if key.get("exemption"):
            named = any(rule.get("measured", {}).get("exemption") == key["exemption"] and rule["status"] == "skip" for _, rule in rows(report))
            check(f"{name} skips for {key['exemption']}", named, messages)
        if key.get("notExempt"):
            check(f"{name} is not exempt", "Exempt:" not in messages, messages)
        if name == "g1-tall-card":
            elements = [rule["element"] for _, rule in rows(report, "fail")]
            check("G1 names the tall plan", elements == ["#tall-plan"] * len(elements) and len(elements) >= 1, " ".join(elements))
        if name == "g3-padding":
            elements = [rule["element"] for _, rule in rows(report, "fail")]
            check("G3 names the loose panel", elements == ["#loose"] * len(elements) and len(elements) >= 1, " ".join(elements))
        if name == "g4-edge":
            elements = [rule["element"] for _, rule in rows(report, "fail")]
            check("G4 names the shifted button", elements == ["#shifted"] * len(elements) and len(elements) >= 1, " ".join(elements))
        if name == "g9-scroll":
            check(
                "G9 fails at 390 and passes at 1280",
                statuses(report, 390, "G9") == {"fail"} and statuses(report, 1280, "G9") == {"pass"},
                detail(result, report),
            )
        if loose:
            if key.get("review"):
                seen = [rule for _, rule in rows(report) if rule["status"] == "review"]
                check(f"{name} needs a look", result.returncode == 3 and report["verdict"] == "review" and seen, detail(result, report))
                continue
            if expected is None:
                allowed = (0, 3) if key.get("allowReview") else (0,)
                check(
                    f"{name} passes",
                    result.returncode in allowed and report["verdict"] in ("pass", "review") and not got and (key.get("allowReview") or report["verdict"] == "pass"),
                    detail(result, report),
                )
                if key.get("real"):
                    real.append(name)
            else:
                check(f"{name} fails {expected}", expected in got and report["verdict"] == "fail", detail(result, report))
            continue
        check(f"{name} fails {expected or 'nothing'}", got == want_ids, detail(result, report))
        if expected is None:
            bad = other_rules_pass(report, None)
            check("clean passes every rule at both widths", bad == [], "\n".join(bad))
            check("clean verdict is pass", report["verdict"] == "pass", report.get("verdict"))
        else:
            bad = other_rules_pass(report, expected)
            check(f"{name} leaves every other rule passing", bad == [], "\n".join(bad))
            check(f"{name} verdict is fail", report["verdict"] == "fail", report["verdict"])
    check("real pages pass", len(real) >= 4, " ".join(real))

    with tempfile.TemporaryDirectory() as tmp:
        strict = os.path.join(tmp, "strict.json")
        with open(strict, "w") as fh:
            json.dump({"betweenOverInside": 4}, fh)
        result = run(["--url", clean, "--widths", "390,1280", "--config", strict, "--out", os.path.join(tmp, "strict-report.json")])
        report = report_of(result)
        check("config can raise the gap ratio", result.returncode == 1 and report and fail_ids(report) == {"G2"}, detail(result, report))
        if report:
            assert_schema("strict config report", report)

        brick = os.path.join(tmp, "bricks.html")
        with open(brick, "w") as fh:
            fh.write("""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Bricks</title>
<style>
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body { font: 16px/24px Arial, sans-serif; }
main { width: 100%; padding: 16px; }
h1, h2, p { margin: 0; }
h1 { font-size: 24px; line-height: 32px; margin-bottom: 8px; }
main > p { margin-bottom: 16px; }
button { display: block; width: fit-content; margin: 0; padding: 8px 12px; font: inherit; line-height: 24px; }
.stack { display: flex; flex-direction: column; gap: 24px; margin: 0 0 16px; }
.group { display: flex; flex-direction: column; gap: 8px; }
.brick { padding: 16px; border: 1px solid #ccc; }
.brick h2 { font-size: 18px; line-height: 24px; margin: 0 0 8px; }
.brick p { margin: 0; line-height: 24px; }
</style></head><body>
<main>
  <h1>Bricks</h1>
  <p>Two stacks of bricks.</p>
  <div class="stack">
    <section class="group">
      <div class="brick"><h2>One</h2><p>A short brick.</p></div>
      <div class="brick" id="tall-brick" style="min-height: 220px"><h2>Two</h2><p>Also short.</p></div>
    </section>
    <section class="group">
      <div class="brick"><h2>Three</h2><p>A note.</p></div>
      <div class="brick"><h2>Four</h2><p>Another note.</p></div>
    </section>
  </div>
  <button type="button">Save bricks</button>
</main></body></html>
""")
        sel = os.path.join(tmp, "bricks.json")
        with open(sel, "w") as fh:
            json.dump({"selectors": {"cards": ".brick"}}, fh)
        result = run(["--url", brick, "--widths", "390,1280", "--config", sel])
        report = report_of(result)
        elements = [rule["element"] for _, rule in rows(report, "fail")] if report else []
        check(
            "config selector marks bricks as cards",
            result.returncode == 1 and report and fail_ids(report) == {"G1"} and elements == ["#tall-brick"] * len(elements) and elements,
            detail(result, report),
        )

        notes = os.path.join(tmp, "notes.html")
        with open(notes, "w") as fh:
            fh.write("""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Notes</title>
<style>
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body { font: 16px/24px Arial, sans-serif; }
main { width: 100%; padding: 16px; }
h1, h2, p { margin: 0; }
h1 { font-size: 24px; line-height: 32px; margin-bottom: 8px; }
main > p { margin-bottom: 16px; }
button { display: block; width: fit-content; margin: 0; padding: 8px 12px; font: inherit; line-height: 24px; }
.stack { display: flex; flex-direction: column; gap: 24px; margin: 0 0 16px; }
.note h2 { font-size: 18px; line-height: 24px; margin: 0 0 8px; }
.note p { margin: 0; line-height: 24px; }
</style></head><body>
<main>
  <h1>Notes</h1>
  <p>Two groups of notes.</p>
  <div class="stack">
    <section data-ui="group" style="display:flex;flex-direction:column;gap:8px">
      <article class="note" data-ui="card" style="padding:16px;border:1px solid #ccc"><h2>Milk</h2><p>One bottle.</p></article>
      <article class="note" data-ui="card" style="padding:16px;border:1px solid #ccc"><h2>Bread</h2><p>One loaf.</p></article>
    </section>
    <section data-ui="group" style="display:flex;flex-direction:column;gap:8px">
      <article class="note" data-ui="card" style="padding:16px;border:1px solid #ccc"><h2>Tea</h2><p>A box.</p></article>
      <article class="note" data-ui="card" style="padding:16px;border:1px solid #ccc"><h2>Soap</h2><p>One bar.</p></article>
    </section>
  </div>
  <button type="button">Save notes</button>
</main></body></html>
""")
        result = run(["--url", notes, "--widths", "390,1280"])
        report = report_of(result)
        bad = other_rules_pass(report, None) if report else ["no report"]
        check("data-ui attributes pass with no card class", result.returncode == 0 and bad == [], detail(result, report) + "\n" + "\n".join(bad))

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"nope")

        def log_message(self, fmt, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = run(["--url", f"http://127.0.0.1:{port}/missing", "--widths", "390", "--timeout", "8000"])
    finally:
        server.shutdown()
    check("HTTP 500 exits 2", result.returncode == 2 and '"verdict": "pass"' not in result.stdout, result.stderr + result.stdout)
    result = run(["--url", "http://127.0.0.1:9/", "--widths", "390", "--timeout", "8000"])
    check("a refused connection exits 2", result.returncode == 2 and '"verdict": "pass"' not in result.stdout, result.stderr + result.stdout)

    with tempfile.TemporaryDirectory() as tmp:
        big = os.path.join(tmp, "index.html")
        cards = "".join(f'<section class="card"><h2>Row {i}</h2><p>{"word " * 30}</p></section>' for i in range(3000))
        with open(big, "w") as fh:
            fh.write(f"<!doctype html><main>{cards}</main>")
        pipe = subprocess.run(
            ["bash", "-lc", f"node {MEASURE} --url {big} --widths 1280 | (sleep 1; cat)"],
            cwd=SKILL, text=True, capture_output=True, timeout=120,
        )
        try:
            body = json.loads(pipe.stdout)
            complete = body.get("verdict") in ("pass", "fail", "review", "inconclusive") and len(pipe.stdout) > 1_000_000
        except json.JSONDecodeError:
            complete = False
        check("a slow reader gets the whole report", pipe.returncode in (0, 1, 3) and complete, f"{pipe.returncode} bytes {len(pipe.stdout)}")
        shots = os.path.join(tmp, "shots")
        os.makedirs(shots)
        shot = run(["--url", os.path.join(CASES, "r2-error-screen", "index.html"), "--out", os.path.join(shots, "report.json"), "--shots", shots, "--widths", "1280"])
        try:
            shot_report = json.loads(shot.stdout)
        except json.JSONDecodeError:
            shot_report = None
        pngs = [os.path.join(shots, name) for name in os.listdir(shots) if name.endswith(".png")]
        check(
            "every review row has a crop",
            shot.returncode == 3 and shot_report and shot_report.get("review") and pngs and all(os.path.getsize(p) > 32 for p in pngs) and all(row.get("shot") for row in shot_report.get("review", [])),
            f"{shot.returncode} png {len(pngs)}",
        )
        class JsonHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path.endswith(".json"):
                    body = b'{"error":"no"}'
                    code, kind = 200, "application/json"
                else:
                    body = b"<html><body><h1>500 Internal Server Error</h1><p>nginx</p></body></html>"
                    code, kind = 500, "text/html"
                self.send_response(code)
                self.send_header("Content-Type", kind)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, fmt, *args):
                return

        json_server = ThreadingHTTPServer(("127.0.0.1", 0), JsonHandler)
        json_port = json_server.server_address[1]
        json_thread = threading.Thread(target=json_server.serve_forever, daemon=True)
        json_thread.start()
        try:
            httpjson = run(["--url", f"http://127.0.0.1:{json_port}/error.json", "--widths", "1280"])
            nginx = run(["--url", f"http://127.0.0.1:{json_port}/", "--widths", "1280"])
        finally:
            json_server.shutdown()
        check("JSON over HTTP is inconclusive", httpjson.returncode == 2 and '"verdict": "pass"' not in httpjson.stdout, httpjson.stdout[-240:])
        check("an nginx 500 is inconclusive", nginx.returncode == 2 and '"verdict": "pass"' not in nginx.stdout, nginx.stdout[-240:])
        json_file = os.path.join(tmp, "error.json")
        with open(json_file, "w") as fh:
            fh.write('{"error":"no"}')
        filed = run(["--url", json_file, "--widths", "1280"])
        check("a JSON file is inconclusive", filed.returncode == 2 and '"verdict": "pass"' not in filed.stdout, filed.stdout[-240:] + filed.stderr[-240:])
        xml_file = os.path.join(tmp, "note.xml")
        with open(xml_file, "w") as fh:
            fh.write("<note><title>Hello</title></note>")
        xml = run(["--url", xml_file, "--widths", "1280"])
        try:
            xml_report = json.loads(xml.stdout)
        except json.JSONDecodeError:
            xml_report = None
        check("an XML file is not HTML", xml.returncode == 2 and xml_report and xml_report.get("verdict") == "inconclusive" and "not HTML" in (xml_report.get("reason") or ""), xml.stdout[-240:] + xml.stderr[-240:])
        class Feed(BaseHTTPRequestHandler):
            def do_GET(self):
                body = b"<feed><item>One</item></feed>"
                self.send_response(200)
                self.send_header("Content-Type", "application/xml")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, fmt, *args):
                return

        feed_server = ThreadingHTTPServer(("127.0.0.1", 0), Feed)
        feed_port = feed_server.server_address[1]
        feed_thread = threading.Thread(target=feed_server.serve_forever, daemon=True)
        feed_thread.start()
        started_feed = time.time()
        try:
            feed = run(["--url", f"http://127.0.0.1:{feed_port}/feed", "--widths", "1280", "--timeout", "8000"])
        finally:
            feed_server.shutdown()
        try:
            feed_report = json.loads(feed.stdout)
        except json.JSONDecodeError:
            feed_report = None
        check(
            "an extensionless XML feed is inconclusive",
            feed.returncode == 2 and feed_report and "not HTML" in (feed_report.get("reason") or "") and time.time() - started_feed < 6,
            f"{feed.returncode} {time.time() - started_feed:.1f}s {feed.stderr[-160:]}",
        )
        huge = os.path.join(tmp, "huge.html")
        with open(huge, "w") as fh:
            fh.write("<!doctype html><main>" + "".join(f"<div>Row {i}</div>" for i in range(20000)) + "</main>")
        slow = run(["--url", huge, "--widths", "1280", "--timeout", "1500"])
        named = "measuring" in (slow.stderr or "") or "scoring" in (slow.stderr or "") or slow.returncode in (0, 1, 3)
        check("a heavy page names a timeout, not navigation", named and "navigation" not in (slow.stderr or ""), (slow.stderr or "")[-300:])

print(f"{passed} passed, {failed} failed, browser {'ran' if browser_ran else 'skipped'}")
sys.exit(1 if failed else 0)
