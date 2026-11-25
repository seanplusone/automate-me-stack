const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const baseUrl = (process.env.BASE_URL || '').replace(/\/$/, '');
const evidenceDir = process.env.EVIDENCE_DIR || path.join(__dirname, '..', 'run', 'evidence');
const headless = process.env.HEADLESS !== '0';

(async () => {
  assert.ok(baseUrl, 'BASE_URL is required');
  fs.mkdirSync(evidenceDir, { recursive: true });

  let browser;
  let failed = false;
  try {
    browser = await chromium.launch({ headless });
    const context = await browser.newContext();
    const page = await context.newPage();

    await page.goto(baseUrl + '/login');
    await page.getByLabel('Username').fill('viewer');
    await page.getByLabel('Password').fill('demo-viewer-pass');
    await page.getByRole('button', { name: 'Sign in' }).click();
    await page.waitForURL('**/orders');

    assert.strictEqual(new URL(page.url()).pathname, '/orders', `expected /orders, got ${page.url()}`);

    const who = (await page.locator('#who').textContent() || '').trim();
    assert.strictEqual(who, 'viewer', `expected #who to be viewer, got ${who}`);

    const buttons = await page.locator('button[data-order]').count();
    assert.strictEqual(buttons, 0, `expected no refund buttons for viewer, got ${buttons}`);

    await page.screenshot({ path: path.join(evidenceDir, 'login-after.png') });
  } catch (err) {
    console.error(err && err.message ? err.message : String(err));
    failed = true;
  } finally {
    if (browser) await browser.close();
  }
  if (failed) process.exit(1);
})();
