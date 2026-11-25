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
  let page;
  let failed = false;
  try {
    browser = await chromium.launch({ headless });
    const context = await browser.newContext();
    page = await context.newPage();

    await page.goto(baseUrl + '/login');
    await page.getByLabel('Username').fill('admin');
    await page.getByLabel('Password').fill('demo-admin-pass');
    await page.getByRole('button', { name: 'Sign in' }).click();
    await page.waitForURL('**/orders');

    await Promise.all([
      page.waitForEvent('load'),
      page.getByRole('button', { name: 'Reset demo data' }).click(),
    ]);

    await page.locator('button[data-order="1001"]').click();
    await page.waitForFunction(
      () => {
        const el = document.getElementById('status-1001');
        return el && el.textContent.trim() === 'refunded';
      },
      null,
      { timeout: 3000 }
    );

    const resp = await context.request.get(baseUrl + '/api/orders/1001/refunds');
    assert.strictEqual(resp.status(), 200, `expected 200 from refunds API, got ${resp.status()}`);
    const refunds = await resp.json();
    assert.strictEqual(refunds.length, 1, `expected 1 refund for order 1001, got ${refunds.length}`);

    await page.screenshot({ path: path.join(evidenceDir, 'refund-after.png') });
  } catch (err) {
    if (page) {
      try {
        await page.screenshot({ path: path.join(evidenceDir, 'refund-failed.png') });
      } catch (_) {
        // ignore screenshot failure during error handling
      }
    }
    console.error(err && err.message ? err.message : String(err));
    failed = true;
  } finally {
    if (browser) await browser.close();
  }
  if (failed) process.exit(1);
})();
