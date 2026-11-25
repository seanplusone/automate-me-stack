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
    await page.getByLabel('Username').fill('admin');
    await page.getByLabel('Password').fill('demo-admin-pass');
    await page.getByRole('button', { name: 'Sign in' }).click();
    await page.waitForURL('**/orders');

    await Promise.all([
      page.waitForEvent('load'),
      page.getByRole('button', { name: 'Reset demo data' }).click(),
    ]);

    const rows = await page.locator('tbody tr').count();
    assert.strictEqual(rows, 3, `expected 3 order rows, got ${rows}`);

    const row1001 = page.locator('tbody tr', { has: page.locator('a[href="/orders/1001"]') });
    const amount = (await row1001.locator('td').nth(2).textContent() || '').trim();
    assert.strictEqual(amount, '$42.00', `expected order 1001 amount $42.00, got ${amount}`);

    await page.screenshot({ path: path.join(evidenceDir, 'orders-after.png') });
  } catch (err) {
    console.error(err && err.message ? err.message : String(err));
    failed = true;
  } finally {
    if (browser) await browser.close();
  }
  if (failed) process.exit(1);
})();
