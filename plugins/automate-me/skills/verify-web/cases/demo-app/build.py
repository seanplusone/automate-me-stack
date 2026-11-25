#!/usr/bin/env python3
"""Stand-in compile step for demo-app. Copies app.py and seed.json into build/."""
import os
import shutil
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    delay = float(os.environ.get("DEMO_BUILD_SECONDS", "3"))
    if delay > 0:
        time.sleep(delay)

    out = os.path.join(HERE, "build")
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    for name in ("app.py", "seed.json"):
        shutil.copy2(os.path.join(HERE, name), os.path.join(out, name))

    counter = os.environ.get("DEMO_BUILD_COUNTER")
    if counter:
        parent = os.path.dirname(os.path.abspath(counter))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(counter, "a") as f:
            f.write("built\n")

    print(f"built {out}")


if __name__ == "__main__":
    main()
