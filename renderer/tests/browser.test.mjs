// Optional Playwright smoke test. Start tools/serve_renderer.py first.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require = createRequire(import.meta.url);
const {chromium} = require(`${process.env.PLAYWRIGHT_MODULE_PATH || 'playwright'}`);

test('工作台可以打开并显示官方 catalog 样例', async t => {
  const browser = await chromium.launch({headless: true, executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH});
  t.after(() => browser.close());
  const page = await browser.newPage();
  await page.goto(process.env.A2UI_RENDERER_URL || 'http://127.0.0.1:8765');
  await page.locator('#instant').click();
  await page.waitForTimeout(100);
  assert.equal(await page.locator('#status').textContent(), '已完成');
  assert.ok(await page.locator('[data-component-id="root"]').count());
});

test('组件画廊覆盖已开放组件并呈现 Extended 交互控件', async t => {
  const browser = await chromium.launch({headless: true, executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH});
  t.after(() => browser.close());
  const page = await browser.newPage();
  await page.goto(process.env.A2UI_RENDERER_URL || 'http://127.0.0.1:8765');
  await page.locator('#sample').selectOption('component-gallery');
  await page.locator('#load-sample').click();
  await page.locator('#instant').click();
  for (const id of ['progress', 'button', 'input', 'toggle', 'radio', 'checkbox', 'checkbox-group', 'select', 'list', 'stack', 'grid', 'nav', 'tabs', 'tab-one', 'web', 'if']) {
    assert.equal(await page.locator(`[data-component-id="${id}"]`).count(), 1, id);
  }
  await page.getByRole('tab', {name: '视图二'}).click();
  assert.equal(await page.locator('[data-component-id="tab-two"]').count(), 1);
});

test('表单联动使用最新值并生成确认 query', async t => {
  const browser = await chromium.launch({headless: true, executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH});
  t.after(() => browser.close());
  const page = await browser.newPage();
  await page.goto(process.env.A2UI_RENDERER_URL || 'http://127.0.0.1:8765');
  await page.locator('#sample').selectOption('form-ingredients');
  await page.locator('#load-sample').click();
  await page.locator('#instant').click();
  await page.getByLabel('用餐人数').fill('6');
  await page.getByLabel('每人食材用量').fill('200');
  await page.getByLabel('口味偏好').selectOption('0');
  await page.getByRole('button', {name: '确认并整理采购清单'}).click();
  await page.locator('.query-entry pre').waitFor();
  const query = await page.locator('.query-entry pre').textContent();
  assert.match(query, /聚会人数6/);
  assert.match(query, /食材总量1200/);
});

test('链接 FunctionCall 只回调参数，不导航', async t => {
  const browser = await chromium.launch({headless: true, executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH});
  t.after(() => browser.close());
  const page = await browser.newPage();
  await page.addInitScript(() => { window.xyA2uiHost = {onFunctionCall: detail => { window.lastFunctionCall = detail; }}; });
  await page.goto(process.env.A2UI_RENDERER_URL || 'http://127.0.0.1:8765');
  await page.locator('#sample').selectOption('function-call-link');
  await page.locator('#load-sample').click();
  await page.locator('#instant').click();
  await page.getByRole('button', {name: '打开官方文档'}).click();
  await page.waitForFunction(() => window.lastFunctionCall?.functionCall?.call === 'openSuperlink');
  assert.match(page.url(), /127\.0\.0\.1/);
});
