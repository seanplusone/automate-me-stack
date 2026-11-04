"""Run: python3 shared/skills/design-options/check/test_score_judge.py"""
import contextlib
import io
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from score_judge import score  # noqa: E402

CASE = os.path.join(HERE, "..", "cases", "preset-field")
KEY = os.path.join(CASE, "key.md")
FAILS = []
RUN = []

NEW_KIND = """ARCH A1: show a fixed list of three priorities | PRECEDENT builder/presets/YesNoPreset.php:6 | STANDARD NONE | USE reuse | WHY a preset fills a select
SHAPE A1: FAILS | step 3, a configured select; add a preset like builder/presets/YesNoPreset.php:6 | src/Fields/PriorityField.php:5
"""
PRESET = """SHAPE A1: HOLDS | mirrors the YesNo preset | builder/presets/PriorityPreset.php:3
"""
LEAKS = """SHAPE A1: HOLDS | the preset mirrors its sibling | builder/presets/PriorityPreset.php:3
SHAPE A2: FAILS | step 5, the renderer learns a preset name; fill a select style setting instead | src/Render/SelectRenderer.php:7
"""


def expect(name, scenario, output, want, needle=None):
    RUN.append(name)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write(output)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        got = score(KEY, scenario, f.name, CASE)
    if got != want or (needle and needle not in out.getvalue()):
        FAILS.append(f"{name}: wanted {want} {needle or ''}, got {got}\n{out.getvalue()}")


expect("new-kind passes with a step 3 FAILS citing the preset", "new-kind", NEW_KIND, 0)
expect("new-kind fails when judged HOLDS", "new-kind", PRESET.replace("PriorityPreset.php:3", "YesNoPreset.php:3"), 1, "K1 wants FAILS at step 3")
expect("new-kind fails at the wrong step", "new-kind", NEW_KIND.replace("step 3", "step 5"), 1, "K1 wants FAILS at step 3")
expect("new-kind fails citing only the new field", "new-kind",
       "SHAPE A1: FAILS | step 3 | src/Fields/PriorityField.php:5\n", 1, "K1 wants FAILS")
expect("preset passes when every shape holds", "preset", PRESET, 0)
expect("a citation may name the repo folder", "preset", PRESET.replace("builder/", "repo/builder/"), 0)
expect("preset fails on any FAILS", "preset", PRESET + "SHAPE A2: FAILS | step 5 | builder/presets/Preset.php:14\n", 1, "K2 wants HOLDS")
expect("preset-leaks passes with a step 5 FAILS on the renderer", "preset-leaks", LEAKS, 0)
expect("preset-leaks fails when all hold", "preset-leaks", LEAKS.replace("FAILS | step 5", "HOLDS | step 5"), 1, "K3 wants FAILS at step 5")
expect("a line past the end of a file fails", "preset", PRESET.replace(":3", ":99"), 1, "not in the repo or the diff")
expect("a file in neither repo nor diff fails", "preset", PRESET.replace("PriorityPreset", "PriorityPresett"), 1, "not in the repo or the diff")
expect("a loose file name in the reason is not a citation", "preset", PRESET.replace("mirrors the YesNo preset", "mirrors YesNoPreset.php:6"), 0)
expect("no SHAPE lines fails", "preset", "ARCH A1: x\n", 1, "no SHAPE lines")

print("\n".join(FAILS) or f"{len(RUN)}/{len(RUN)} passed")
sys.exit(1 if FAILS else 0)
