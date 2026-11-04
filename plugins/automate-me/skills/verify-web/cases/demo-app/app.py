#!/usr/bin/env python3
"""Demo shop for verify-web's eval: sign in, list orders, refund one. Python stdlib only.

  python3 app.py --port 8000 [--data-dir run/data] [--pid-file run/app.pid]

Logins (demo only, not secrets): admin / demo-admin-pass, viewer / demo-viewer-pass (read-only).
GET /__version prints "$DEMO_TREE" ("<branch> <sha>"), so the doctor can tell which tree is served.
The refund call waits REFUND_DELAY seconds, standing in for a payment provider.
"""
import argparse
import html
import json
import os
import secrets
import threading
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
USERS = {"admin": ("demo-admin-pass", "admin"), "viewer": ("demo-viewer-pass", "readonly")}
REFUND_DELAY = float(os.environ.get("REFUND_DELAY", "0.4"))
SESSIONS = {}
LOCK = threading.Lock()
DATA = {"dir": None}

PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>{title}</title></head>
<body><header>{nav}</header><main><h1>{title}</h1>{body}</main></body></html>"""

ORDERS_JS = """<script>
async function refund(btn) {
  const id = btn.dataset.order;
  const r = await fetch('/orders/' + id + '/refund', {method: 'POST'});
  const body = await r.json();
  document.getElementById('msg').textContent = body.message;
  document.getElementById('status-' + id).textContent = body.status;
  document.getElementById('refunded-' + id).textContent = body.refunded;
}
</script>"""


def money(cents):
    return f"${cents / 100:.2f}"


def orders_path():
    return os.path.join(DATA["dir"], "orders.json")


def refunds_path():
    return os.path.join(DATA["dir"], "refunds.jsonl")


def seed():
    os.makedirs(DATA["dir"], exist_ok=True)
    with open(os.path.join(HERE, "seed.json")) as f:
        orders = json.load(f)
    with open(orders_path(), "w") as f:
        json.dump(orders, f, indent=1)
    open(refunds_path(), "w").close()


def load_orders():
    with open(orders_path()) as f:
        return json.load(f)


def save_orders(orders):
    with open(orders_path(), "w") as f:
        json.dump(orders, f, indent=1)


def refunds_for(order_id):
    with open(refunds_path()) as f:
        rows = [json.loads(l) for l in f if l.strip()]
    return [r for r in rows if r["order_id"] == order_id]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def user(self):
        c = SimpleCookie(self.headers.get("Cookie", ""))
        return SESSIONS.get(c["sid"].value) if "sid" in c else None

    def send(self, code, body, ctype="text/html; charset=utf-8", headers=()):
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        for k, v in headers:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def page(self, title, body, code=200):
        u = self.user()
        nav = (f'Signed in as <span id="who">{html.escape(u["name"])}</span> ({u["role"]}) '
               f'<a href="/orders">Orders</a> <form method="post" action="/logout" style="display:inline">'
               f'<button>Sign out</button></form>') if u else '<a href="/login">Sign in</a>'
        self.send(code, PAGE.format(title=html.escape(title), nav=nav, body=body))

    def redirect(self, to, headers=()):
        self.send(302, "", headers=[("Location", to), *headers])

    def form(self):
        n = int(self.headers.get("Content-Length") or 0)
        return {k: v[0] for k, v in parse_qs(self.rfile.read(n).decode()).items()}

    def do_GET(self):
        p = self.path.split("?")[0]
        if p == "/health":
            return self.send(200, "ok", "text/plain")
        if p == "/__version":
            return self.send(200, os.environ.get("DEMO_TREE", "unknown unknown") + "\n", "text/plain")
        if p == "/login":
            return self.page("Sign in", '<form method="post" action="/login">'
                             '<label>Username <input name="username"></label> '
                             '<label>Password <input name="password" type="password"></label> '
                             '<button type="submit">Sign in</button></form>')
        u = self.user()
        if not u:
            return self.redirect("/login")
        if p in ("/", "/orders"):
            return self.orders_page(u)
        if p.startswith("/orders/"):
            return self.order_page(p.split("/")[2])
        if p.startswith("/api/orders/") and p.endswith("/refunds"):
            oid = int(p.split("/")[3])
            return self.send(200, json.dumps(refunds_for(oid)), "application/json")
        self.page("Not found", "<p>No such page.</p>", 404)

    def orders_page(self, u):
        rows = []
        for o in load_orders():
            oid = o["id"]
            can = u["role"] == "admin" and o["status"] != "refunded"
            btn = (f'<button data-order="{oid}" onclick="refund(this)">Refund</button>' if can else "")
            rows.append(f'<tr><td><a href="/orders/{oid}">{oid}</a></td><td>{html.escape(o["customer"])}</td>'
                        f'<td>{money(o["amount_cents"])}</td><td id="status-{oid}">{o["status"]}</td>'
                        f'<td id="refunded-{oid}">{money(o["refunded_cents"])}</td><td>{btn}</td></tr>')
        reset = ('<form method="post" action="/admin/reset"><button>Reset demo data</button></form>'
                 if u["role"] == "admin" else "")
        body = ('<p id="msg" role="status"></p><table><thead><tr><th>Order</th><th>Customer</th><th>Amount</th>'
                '<th>Status</th><th>Refunded</th><th></th></tr></thead><tbody>' + "".join(rows) +
                "</tbody></table>" + reset + ORDERS_JS)
        self.page("Orders", body)

    def order_page(self, oid):
        try:
            o = next(x for x in load_orders() if x["id"] == int(oid))
        except (StopIteration, ValueError):
            return self.page("Not found", "<p>No such order.</p>", 404)
        items = "".join(f'<li>{money(r["amount_cents"])} at {r["at"]} by {html.escape(r["by"])}</li>'
                        for r in refunds_for(o["id"])) or "<li>None</li>"
        self.page(f"Order {o['id']}", f'<p>{html.escape(o["customer"])}, {money(o["amount_cents"])}, '
                  f'status {o["status"]}</p><h2>Refunds</h2><ul id="refunds">{items}</ul>')

    def do_POST(self):
        p = self.path.split("?")[0]
        if p == "/login":
            f = self.form()
            known = USERS.get(f.get("username", ""))
            if not known or known[0] != f.get("password"):
                return self.page("Sign in", '<p role="alert">Wrong username or password.</p>'
                                 '<p><a href="/login">Try again</a></p>', 401)
            sid = secrets.token_hex(16)
            SESSIONS[sid] = {"name": f["username"], "role": known[1]}
            return self.redirect("/orders", [("Set-Cookie", f"sid={sid}; HttpOnly; Path=/")])
        u = self.user()
        if not u:
            return self.send(401, json.dumps({"message": "Sign in first"}), "application/json")
        if p == "/logout":
            SESSIONS.pop(SimpleCookie(self.headers.get("Cookie", ""))["sid"].value, None)
            return self.redirect("/login")
        if u["role"] != "admin":
            return self.send(403, json.dumps({"message": "Read-only users cannot change orders"}), "application/json")
        if p == "/admin/reset":
            with LOCK:
                seed()
            return self.redirect("/orders")
        if p.startswith("/orders/") and p.endswith("/refund"):
            return self.refund(int(p.split("/")[2]), u)
        self.send(404, json.dumps({"message": "not found"}), "application/json")

    def refund(self, oid, u):
        with LOCK:
            o = next((x for x in load_orders() if x["id"] == oid), None)
        if o is None:
            return self.send(404, json.dumps({"message": "No such order"}), "application/json")
        if o["status"] == "refunded":
            return self.send(409, json.dumps({"message": f"Order {oid} is already refunded", "status": o["status"],
                                              "refunded": money(o["refunded_cents"])}), "application/json")
        time.sleep(REFUND_DELAY)  # the payment provider call
        with LOCK:
            orders = load_orders()
            o = next(x for x in orders if x["id"] == oid)
            o["refunded_cents"] += o["amount_cents"]
            o["status"] = "refunded"
            save_orders(orders)
            with open(refunds_path(), "a") as f:
                f.write(json.dumps({"order_id": oid, "amount_cents": o["amount_cents"], "by": u["name"],
                                    "at": time.strftime("%Y-%m-%d %H:%M:%S")}) + "\n")
        self.send(200, json.dumps({"message": f"Refunded {money(o['amount_cents'])} on order {oid}",
                                   "status": o["status"], "refunded": money(o["refunded_cents"])}), "application/json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--data-dir", default=os.path.join(HERE, "run", "data"))
    ap.add_argument("--pid-file")
    a = ap.parse_args()
    DATA["dir"] = os.path.abspath(a.data_dir)
    if not os.path.exists(orders_path()):
        seed()
    if a.pid_file:
        os.makedirs(os.path.dirname(os.path.abspath(a.pid_file)), exist_ok=True)
        with open(a.pid_file, "w") as f:
            f.write(str(os.getpid()))
    server = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    print(f"demo app on http://127.0.0.1:{a.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
