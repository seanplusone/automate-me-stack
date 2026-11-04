"""Run: python3 check/test_classify.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from classify import label, summary  # noqa: E402

FAILS = []


def expect(name, got, want):
    if got != want:
        FAILS.append(f"{name}: wanted {want!r}, got {got!r}")


expect("hashed js", label("public/build/checkout/index-D1CdT9Mr.js"), "generated")
expect("hashed css", label("a/index-D9sdNZul.css"), "generated")
expect("dash plus 8 lowercase letters is not a hash", label("src/form-settings.js"), "source")
expect("index.js short line", label("public/build/checkout/index.js", 80), "source")
expect("index.js long line", label("public/build/checkout/index.js", 40000), "generated")
expect("line of exactly 1000", label("a/index.js", 1000), "source")
expect("gz", label("public/app.js.gz"), "generated")
expect("map", label("public/app.js.map"), "generated")
expect("png", label("public/logo.png"), "asset")
expect("binary unknown ext", label("data/blob.dat", binary=True), "asset")
expect("woff2", label("fonts/a.woff2"), "asset")
expect("hashed png is generated first", label("img/logo-c9DaY111.png"), "generated")
expect("Test.php", label("app/Foo/BarTest.php"), "test")
expect("tests dir", label("tests/safe/Helper.php"), "test")
expect("nested __tests__", label("src/__tests__/a.ts"), "test")
expect("spec.tsx", label("src/a.spec.tsx"), "test")
expect("test_py", label("lib/test_foo.py"), "test")
expect("_test_py", label("lib/foo_test.py"), "test")
expect("md", label("docs/README.md"), "docs")
expect("txt", label("notes.txt"), "docs")
expect("plain php", label("app/Http/Controllers/FooController.php", 90), "source")
expect("php no read", label("app/Foo.php"), "source")
expect("tests as a filename not a dir", label("src/tests.php"), "source")

files = {"a.php": "source", "b.php": "source", "tests/c.php": "test", "x-AbCd1234.js": "generated"}
expect("summary", summary("o/r#1", files), "o/r#1: 4 files: 2 source, 1 test, 1 generated")
expect("summary order", summary("o/r#2", {"a.png": "asset", "b.md": "docs", "c.php": "source"}), "o/r#2: 3 files: 1 source, 1 asset, 1 docs")
expect("summary none", summary("o/r#3", {}), "o/r#3: 0 files")

if __name__ == "__main__":
    for line in FAILS:
        print(f"FAIL {line}")
    print("done" if not FAILS else f"{len(FAILS)} failed")
    sys.exit(1 if FAILS else 0)
