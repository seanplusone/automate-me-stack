"""Run: python3 hooks/test_check_read_size_hook.py"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "check_read_size_hook.py")


def hook(payload):
    data = payload if isinstance(payload, str) else json.dumps(payload)
    env = {k: v for k, v in os.environ.items() if k != "READ_SIZE_THRESHOLD"}
    p = subprocess.run([sys.executable, HOOK], input=data, capture_output=True, text=True, env=env)
    return p.returncode, p.stdout, p.stderr


class Hook(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.big = os.path.join(self.d, "big.txt")
        self.small = os.path.join(self.d, "small.txt")
        open(self.big, "w").write("x\n" * 400)
        open(self.small, "w").write("x\n" * 3)

    def tearDown(self):
        shutil.rmtree(self.d)

    def read(self, **ti):
        return hook({"tool_name": "Read", "tool_input": ti, "cwd": self.d})

    def test_read_small_allowed(self):
        self.assertEqual(self.read(file_path=self.small), (0, "", ""))

    def test_read_big_blocked_with_reason(self):
        code, _, err = self.read(file_path=self.big)
        self.assertEqual(code, 2)
        self.assertEqual(len(err.strip().splitlines()), 1)
        self.assertIn(self.big, err)
        self.assertIn("limit", err)

    def test_read_path_key_and_relative(self):
        self.assertEqual(self.read(path="big.txt")[0], 2)

    def test_read_with_limit_allowed(self):
        self.assertEqual(self.read(file_path=self.big, offset=10, limit=50)[0], 0)

    def test_read_offset_only_blocked(self):
        self.assertEqual(self.read(file_path=self.big, offset=10)[0], 2)

    def test_bad_limit_does_not_bypass(self):
        self.assertEqual(self.read(file_path=self.big, limit=0)[0], 2)
        self.assertEqual(self.read(file_path=self.big, limit="lots")[0], 2)

    def test_bash_big_blocked(self):
        code, _, err = hook({"tool_name": "Bash", "tool_input": {"command": "cat big.txt | wc -l"}, "cwd": self.d})
        self.assertEqual(code, 2)
        self.assertIn("big.txt", err)

    def test_bash_small_allowed(self):
        self.assertEqual(hook({"tool_name": "Bash", "tool_input": {"command": "cat small.txt"}, "cwd": self.d}), (0, "", ""))

    def test_other_tool_allowed(self):
        self.assertEqual(hook({"tool_name": "Write", "tool_input": {"file_path": self.big}})[0], 0)

    def test_bad_input_fails_open(self):
        for data in ("", "not json", "[]", json.dumps({"tool_name": "Read"}), json.dumps({"tool_name": "Read", "tool_input": "x"}),
                     json.dumps({"tool_name": "Bash", "tool_input": {"command": 5}})):
            self.assertEqual(hook(data)[0], 0, data)

    def test_hooks_json_shape(self):
        cfg = json.load(open(os.path.join(os.path.dirname(HOOK), "hooks.json")))
        entry = cfg["hooks"]["PreToolUse"][0]
        self.assertEqual(entry["matcher"], "Read|Bash")
        self.assertIn("${CLAUDE_PLUGIN_ROOT}/hooks/check_read_size_hook.py", entry["hooks"][0]["command"])


if __name__ == "__main__":
    unittest.main()
