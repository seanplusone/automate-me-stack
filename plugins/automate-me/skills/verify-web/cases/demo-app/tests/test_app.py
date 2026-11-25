"""Unit tests for demo-app."""
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

import app  # noqa: E402


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        return fp

    http_error_301 = http_error_303 = http_error_307 = http_error_308 = http_error_302


class DemoAppTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="demo-app-test-")
        self.orig_dir = app.DATA["dir"]
        self.orig_delay = app.REFUND_DELAY
        app.DATA["dir"] = self.tmp
        app.SESSIONS.clear()

    def tearDown(self):
        app.DATA["dir"] = self.orig_dir
        app.REFUND_DELAY = self.orig_delay
        app.SESSIONS.clear()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_money_whole_dollars(self):
        self.assertEqual(app.money(0), "$0.00")
        self.assertEqual(app.money(4200), "$42.00")
        self.assertEqual(app.money(15000), "$150.00")

    def test_money_with_cents(self):
        self.assertEqual(app.money(1999), "$19.99")
        self.assertEqual(app.money(5), "$0.05")

    def test_paths_follow_data_dir(self):
        self.assertEqual(app.orders_path(), os.path.join(self.tmp, "orders.json"))
        self.assertEqual(app.refunds_path(), os.path.join(self.tmp, "refunds.jsonl"))

    def test_seed_writes_orders_and_empty_refunds(self):
        app.seed()
        self.assertTrue(os.path.isfile(app.orders_path()))
        self.assertTrue(os.path.isfile(app.refunds_path()))
        orders = app.load_orders()
        self.assertEqual(len(orders), 3)
        self.assertEqual([o["id"] for o in orders], [1001, 1002, 1003])
        with open(app.refunds_path()) as f:
            self.assertEqual(f.read(), "")

    def test_seed_resets_modified_state(self):
        app.seed()
        orders = app.load_orders()
        orders[0]["status"] = "refunded"
        app.save_orders(orders)
        with open(app.refunds_path(), "w") as f:
            f.write(json.dumps({"order_id": 1001, "amount_cents": 4200}) + "\n")

        app.seed()
        self.assertEqual(app.load_orders()[0]["status"], "paid")
        self.assertEqual(app.refunds_for(1001), [])

    def test_save_and_load_orders_roundtrip(self):
        sample = [{"id": 2001, "customer": "Test Co", "amount_cents": 500, "refunded_cents": 0, "status": "paid"}]
        app.save_orders(sample)
        self.assertEqual(app.load_orders(), sample)

    def test_refunds_for_filters_by_order_id(self):
        rows = [
            {"order_id": 1001, "amount_cents": 4200, "by": "admin"},
            {"order_id": 1002, "amount_cents": 1999, "by": "admin"},
            {"order_id": 1001, "amount_cents": 100, "by": "admin"},
        ]
        with open(app.refunds_path(), "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
            f.write("\n")

        got_1001 = app.refunds_for(1001)
        self.assertEqual(len(got_1001), 2)
        self.assertTrue(all(r["order_id"] == 1001 for r in got_1001))
        self.assertEqual(len(app.refunds_for(1002)), 1)

    def test_refunds_for_unknown_order_returns_empty(self):
        app.seed()
        self.assertEqual(app.refunds_for(9999), [])

    def test_http_login_and_refund_order(self):
        app.seed()
        app.REFUND_DELAY = 0
        server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{port}"
        opener = urllib.request.build_opener(NoRedirect())
        try:
            with opener.open(f"{base}/health", timeout=5) as resp:
                self.assertEqual(resp.status, 200)
                self.assertEqual(resp.read().decode(), "ok")

            form = urllib.parse.urlencode({"username": "admin", "password": "demo-admin-pass"}).encode()
            login_req = urllib.request.Request(f"{base}/login", data=form, method="POST")
            with opener.open(login_req, timeout=5) as resp:
                self.assertEqual(resp.status, 302)
                set_cookie = resp.headers.get("Set-Cookie", "")
            self.assertIn("sid=", set_cookie)
            sid_cookie = set_cookie.split(";", 1)[0]

            refund_req = urllib.request.Request(
                f"{base}/orders/1001/refund",
                data=b"",
                headers={"Cookie": sid_cookie},
                method="POST",
            )
            with opener.open(refund_req, timeout=5) as resp:
                self.assertEqual(resp.status, 200)
                body = json.loads(resp.read().decode())
            self.assertEqual(body["status"], "refunded")
            self.assertEqual(body["refunded"], "$42.00")

            api_req = urllib.request.Request(
                f"{base}/api/orders/1001/refunds",
                headers={"Cookie": sid_cookie},
                method="GET",
            )
            with opener.open(api_req, timeout=5) as resp:
                self.assertEqual(resp.status, 200)
                refunds = json.loads(resp.read().decode())
            self.assertEqual(len(refunds), 1)
            self.assertEqual(refunds[0]["order_id"], 1001)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
