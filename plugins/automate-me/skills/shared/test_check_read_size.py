"""Run: python3 shared/test_check_read_size.py"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "check_read_size.py")
sys.path.insert(0, HERE)
import check_read_size as crs  # noqa: E402


def run(*args, env=None, cwd=None):
    e = {k: v for k, v in os.environ.items() if k != "READ_SIZE_THRESHOLD"}
    e.update(env or {})
    p = subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True, env=e, cwd=cwd)
    return p.returncode, p.stdout, p.stderr


class Files(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.big = self.write("big.txt", 400)
        self.mid = self.write("mid.txt", 50)
        self.small = self.write("small.txt", 5)

    def tearDown(self):
        shutil.rmtree(self.d)

    def write(self, name, lines):
        path = os.path.join(self.d, name)
        with open(path, "w") as f:
            f.write("line\n" * lines)
        return path


class Cli(Files):
    def test_small_file_allowed_silently(self):
        self.assertEqual(run(self.small), (0, "", ""))

    def test_large_file_blocked_with_one_line_reason(self):
        code, out, err = run(self.big)
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertEqual(len(err.strip().splitlines()), 1)
        self.assertIn(self.big, err)
        self.assertIn("offset and a limit", err)
        self.assertIn("execute_file", err)

    def test_lower_threshold_blocks_mid_file(self):
        self.assertEqual(run(self.mid)[0], 0)
        self.assertEqual(run("--threshold", "20", self.mid)[0], 2)

    def test_offset_and_limit_allowed_on_large_file(self):
        self.assertEqual(run("--offset", "100", "--limit", "50", self.big)[0], 0)

    def test_limit_alone_allowed_on_large_file(self):
        self.assertEqual(run("--limit", "50", self.big)[0], 0)

    def test_offset_without_limit_blocked(self):
        self.assertEqual(run("--offset", "100", self.big)[0], 2)

    def test_missing_file_allowed(self):
        self.assertEqual(run(os.path.join(self.d, "nope.txt")), (0, "", ""))

    def test_env_threshold(self):
        self.assertEqual(run(self.mid, env={"READ_SIZE_THRESHOLD": "20"})[0], 2)
        self.assertEqual(run(self.big, env={"READ_SIZE_THRESHOLD": "1000"})[0], 0)

    def test_flag_threshold_beats_env(self):
        self.assertEqual(run("--threshold", "1000", self.big, env={"READ_SIZE_THRESHOLD": "20"})[0], 0)
        self.assertEqual(run("--threshold", "20", self.mid, env={"READ_SIZE_THRESHOLD": "1000"})[0], 2)

    def test_cat_big_blocked(self):
        code, _, err = run("--command", f"cat {self.big}")
        self.assertEqual(code, 2)
        self.assertIn(self.big, err)
        self.assertIn("cat", err)

    def test_pipe_blocked(self):
        self.assertEqual(run("--command", f"cat {self.big} | wc -l")[0], 2)

    def test_and_blocked(self):
        self.assertEqual(run("--command", f"echo x && cat {self.big}")[0], 2)

    def test_semicolon_blocked(self):
        self.assertEqual(run("--command", f"cat {self.big}; ls")[0], 2)

    def test_or_newline_and_grouping_blocked(self):
        for cmd in (f"false || less {self.big}", f"ls\ntail {self.big}", f"(cd /; head {self.big})",
                    f"{{ cat {self.big}; }}", f"x=$(cat {self.big})"):
            self.assertEqual(run("--command", cmd)[0], 2, cmd)

    def test_reader_flags_and_redirects(self):
        for cmd in (f"cat -n {self.big}", f"cat < {self.big}", f"cat {self.big} 2>/dev/null", f"FOO=1 cat {self.big}"):
            self.assertEqual(run("--command", cmd)[0], 2, cmd)
        self.assertEqual(run("--command", f"cat {self.small} > {self.big}")[0], 0)

    def test_relative_path_uses_cwd(self):
        self.assertEqual(run("--command", "cat big.txt", cwd=self.d)[0], 2)

    def test_cat_small_allowed(self):
        self.assertEqual(run("--command", f"cat {self.small} | wc -l"), (0, "", ""))

    def test_other_tools_not_flagged(self):
        for cmd in (f"rg line {self.big}", f"wc -l {self.big}", f"ls {self.d}", f"echo {self.big}"):
            self.assertEqual(run("--command", cmd)[0], 0, cmd)

    def test_head_tail_with_small_count_allowed(self):
        for cmd in (f"head -n 20 {self.big}", f"tail -20 {self.big}", f"head --lines=20 {self.big}"):
            self.assertEqual(run("--command", cmd)[0], 0, cmd)
        self.assertEqual(run("--command", f"tail -n 1000 {self.big}")[0], 2)

    def test_usage_errors(self):
        for args in ((), ("--threshold", "abc", self.small), ("--threshold", "0", self.small),
                     ("--threshold", "-5", self.small), ("--limit", "0", self.big), ("--limit", "x", self.big),
                     ("--offset", "-1", self.big), ("--command", "cat x", self.small), ("--bogus", self.small),
                     (self.small, self.big), ("--command", "  ")):
            code, out, err = run(*args)
            self.assertEqual(code, 3, args)
            self.assertTrue(err.strip(), args)

    def test_bad_env_threshold_is_usage_error(self):
        self.assertEqual(run(self.small, env={"READ_SIZE_THRESHOLD": "lots"})[0], 3)


class Library(Files):
    def test_count_lines(self):
        self.assertEqual(crs.count_lines(self.big), 400)
        self.assertIsNone(crs.count_lines(os.path.join(self.d, "nope")))

    def test_check_path(self):
        self.assertIsNone(crs.check_path(self.small))
        self.assertIn(self.big, crs.check_path(self.big))
        self.assertIsNone(crs.check_path(self.big, limit=10))
        self.assertIsNotNone(crs.check_path(self.big, offset=10))
        self.assertIsNone(crs.check_path(self.big, threshold=1000))

    def test_check_command(self):
        self.assertIsNotNone(crs.check_command("cat big.txt", cwd=self.d))
        self.assertIsNone(crs.check_command("cat small.txt", cwd=self.d))
        self.assertIsNone(crs.check_command("cat nope.txt", cwd=self.d))
        self.assertIsNone(crs.check_command("wc -l big.txt", cwd=self.d))
        self.assertIsNone(crs.check_command("cat big.txt", threshold=1000, cwd=self.d))

    def test_reason_is_one_line(self):
        r = crs.check_command(f"echo a\ncat {self.big}\nls", cwd=self.d)
        self.assertEqual(len(r.splitlines()), 1)


if __name__ == "__main__":
    unittest.main()
