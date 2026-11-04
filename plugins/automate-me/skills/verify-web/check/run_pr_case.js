#!/usr/bin/env node
// Proves cases/demo-app/pr-1 is a valid case: the PR claims a double-click refunds once, and on the
// PR head it still refunds twice. Drives base and head in a real browser, with the same seed data.
// It also drives a correct fix (button disabled before the request), which must refund once, so the
// double-click scenario can tell a real fix from the planted bug.
//
//   node check/run_pr_case.js [--evidence <dir>]
//
// Needs the `playwright` npm package and a Chromium it can launch. Exits 0 when the case holds.
const { chromium } = require('playwright');
const { spawn, execFileSync } = require('child_process');
const fs = require('fs');
const net = require('net');
const os = require('os');
const path = require('path');

const CASE = path.join(__dirname, '..', 'cases', 'demo-app');
const argEv = process.argv.indexOf('--evidence');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'verify-web-pr1-'));
const evidence = argEv > 0 ? process.argv[argEv + 1] : path.join(tmp, 'evidence');
fs.mkdirSync(evidence, { recursive: true });

function freePort() {
  return new Promise((resolve) => {
    const s = net.createServer();
    s.listen(0, '127.0.0.1', () => { const p = s.address().port; s.close(() => resolve(p)); });
  });
}

function copyTree(name, patch) {
  const dir = path.join(tmp, name);
  fs.mkdirSync(dir);
  for (const f of ['app.py', 'seed.json']) fs.copyFileSync(path.join(CASE, f), path.join(dir, f));
  if (patch) execFileSync('git', ['apply', path.join(CASE, 'pr-1', 'fix.patch')], { cwd: dir });
  return dir;
}

function correctFix() {
  const dir = copyTree('fixed', false);
  const f = path.join(dir, 'app.py');
  const fetchLine = "  const r = await fetch('/orders/' + id + '/refund', {method: 'POST'});\n";
  const src = fs.readFileSync(f, 'utf8');
  if (!src.includes(fetchLine)) throw new Error('app.py changed; update correctFix()');
  fs.writeFileSync(f, src.replace(fetchLine, "  btn.disabled = true;\n" + fetchLine));
  return dir;
}

async function startApp(dir, tree) {
  const port = await freePort();
  const proc = spawn('python3', ['app.py', '--port', String(port), '--data-dir', path.join(dir, 'data')],
    { cwd: dir, env: { ...process.env, DEMO_TREE: tree }, stdio: 'ignore' });
  const url = `http://127.0.0.1:${port}`;
  for (let i = 0; i < 50; i++) {
    try { if ((await fetch(url + '/health')).ok) return { proc, url }; } catch (e) { /* not up yet */ }
    await new Promise((r) => setTimeout(r, 100));
  }
  proc.kill();
  throw new Error(`app in ${dir} did not start`);
}

async function drive(browser, side, url) {
  const context = await browser.newContext();
  const page = await context.newPage();
  const out = { side, tree: (await (await fetch(url + '/__version')).text()).trim() };
  await page.goto(url + '/login');
  await page.getByLabel('Username').fill('admin');
  await page.getByLabel('Password').fill('demo-admin-pass');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.waitForURL('**/orders');

  // Scenario 1: one click on order 1001.
  const one = page.locator('button[data-order="1001"]');
  await one.click();
  await page.waitForFunction(() => document.getElementById('status-1001').textContent === 'refunded');
  out.singleDisabled = await one.isDisabled();
  out.singleRefunds = (await (await context.request.get(url + '/api/orders/1001/refunds')).json()).length;
  await page.screenshot({ path: path.join(evidence, `s1-${side}-after.png`) });

  // Scenario 2: double-click on order 1002, then check the ledger a second way.
  await page.locator('button[data-order="1002"]').dblclick();
  await page.waitForTimeout(1500);
  out.doubleRefunds = (await (await context.request.get(url + '/api/orders/1002/refunds')).json()).length;
  out.doubleScreen = await page.locator('#refunded-1002').textContent();
  await page.screenshot({ path: path.join(evidence, `s2-${side}-after.png`) });
  await page.goto(url + '/orders/1002');
  out.doubleListed = await page.locator('#refunds li').count();
  await page.screenshot({ path: path.join(evidence, `s2-${side}-order-page.png`) });
  await context.close();
  return out;
}

(async () => {
  const apps = [];
  let failed = false;
  try {
    const base = await startApp(copyTree('base', false), 'main 0000000aaaaaaa');
    apps.push(base);
    const head = await startApp(copyTree('head', true), 'fix/refund-double-click 1111111bbbbbbb');
    apps.push(head);
    const fixed = await startApp(correctFix(), 'control 2222222ccccccc');
    apps.push(fixed);
    const browser = await chromium.launch();
    const results = [];
    for (const [side, app] of [['base', base], ['head', head], ['fixed', fixed]]) results.push(await drive(browser, side, app.url));
    await browser.close();
    fs.writeFileSync(path.join(evidence, 'results.json'), JSON.stringify(results, null, 1));
    const [b, h, c] = results;
    const checks = [
      ['base: one click leaves the button enabled', b.singleDisabled === false],
      ['head: one click disables the button (claim VERIFIED)', h.singleDisabled === true],
      ['base and head: one click makes one refund', b.singleRefunds === 1 && h.singleRefunds === 1],
      ['base: a double-click makes two refunds (the bug)', b.doubleRefunds === 2],
      ['head: a double-click still makes two refunds (claim CONTRADICTED)', h.doubleRefunds === 2 && h.doubleListed === 2],
      ['control: a correct fix makes one refund on a double-click', c.doubleRefunds === 1 && c.doubleListed === 1],
    ];
    for (const [name, ok] of checks) {
      console.log(`${ok ? 'PASS' : 'FAIL'} ${name}`);
      failed = failed || !ok;
    }
    console.log(JSON.stringify(results));
    if (argEv > 0) console.log(`evidence: ${evidence}`);
  } catch (e) {
    console.log(`FAIL ${e.message}`);
    failed = true;
  } finally {
    for (const a of apps) a.proc.kill();
    fs.rmSync(tmp, { recursive: true, force: true });
  }
  console.log(failed ? 'CASE: INVALID' : 'CASE: VALID');
  process.exit(failed ? 1 : 0);
})();
