// Run with Playwright installed: node tests/browser-smoke.cjs
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '../public');
(async () => {
  const server = require('node:http').createServer((req, res) => {
    const name = req.url === '/' ? 'index.html' : req.url.slice(1);
    const file = path.resolve(root, name);
    if (!file.startsWith(root + path.sep)) { res.writeHead(403); res.end(); return; }
    try {
      res.setHeader('Content-Type', name.endsWith('.js') ? 'text/javascript' : name.endsWith('.css') ? 'text/css' : name.endsWith('.png') ? 'image/png' : name.endsWith('.svg') ? 'image/svg+xml' : name.endsWith('.webmanifest') ? 'application/manifest+json' : 'text/html');
      res.end(fs.readFileSync(file));
    } catch { res.writeHead(404); res.end(); }
  });
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  const browser = await chromium.launch({ executablePath: process.env.QA_CHROMIUM || undefined, headless: true,
    args: ['--no-sandbox', '--no-zygote', '--use-gl=angle', '--use-angle=swiftshader'] });
  try {
    const context = await browser.newContext({ viewport: { width: 390, height: 844 }, acceptDownloads: true });
    const page = await context.newPage(), errors = []; page.on('pageerror', e => errors.push(e.message));
    const url = `http://127.0.0.1:${server.address().port}/`;
    await page.goto(url); await page.waitForSelector('.card');
    const count = await page.locator('.card').count(); assert.ok(count > 0);
    for (const width of [320, 390, 768, 1280]) {
      await page.setViewportSize({ width, height: 844 });
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, `overflow at ${width}`);
    }
    await page.setViewportSize({ width: 390, height: 844 });
    await page.locator('.like:not(:disabled)').first().click();
    assert.match(await page.locator('#learningCount').innerText(), /1/);
    await page.reload(); assert.equal(await page.locator('.like.selected').count(), 1);
    await page.locator('.like.selected').click(); assert.equal(await page.locator('.like.selected').count(), 0);
    await page.locator('.like:not(:disabled)').first().click();
    await page.locator('.save:not(:disabled)').first().click();
    await page.locator('[data-view="saved"]').click(); assert.equal(await page.locator('.card').count(), 1);
    await page.locator('[data-view="history"]').click(); assert.equal(await page.locator('.card').count(), 1);
    await page.locator('[data-view="today"]').click();
    await page.locator('#search').fill('no-match-184829'); assert.equal(await page.locator('.card').count(), 0);
    await page.getByRole('button', { name: '検索条件をクリア' }).click(); assert.equal(await page.locator('.card').count(), count);
    await page.locator('[data-view="insights"]').click();
    await page.locator('.tag-form input').first().fill('商品開発'); await page.locator('.tag-form button').first().click();
    assert.match(await page.locator('.tag-remove').first().innerText(), /商品開発/);
    await page.locator('#openSettings').click(); await page.locator('#theme').selectOption('dark');
    assert.equal(await page.locator('html').getAttribute('data-theme'), 'dark');
    await page.locator('#compactToggle').check(); await page.locator('#learningToggle').uncheck();
    const backup = await page.evaluate(() => localStorage.getItem('personal-newsroom-state-v2'));
    const download = page.waitForEvent('download'); await page.locator('#downloadBackup').click(); assert.equal((await download).suggestedFilename(), 'newsroom-backup.json');
    await page.locator('#importBackup').setInputFiles({ name: 'bad.json', mimeType: 'application/json', buffer: Buffer.from('{bad') });
    assert.equal(await page.evaluate(() => localStorage.getItem('personal-newsroom-state-v2')), backup);
    page.once('dialog', d => d.accept()); await page.locator('#resetData').click();
    await page.locator('#importBackup').setInputFiles({ name: 'backup.json', mimeType: 'application/json', buffer: Buffer.from(backup) });
    assert.match(await page.locator('#settingsStatus').innerText(), /統合/);
    await page.locator('#closeSettings').click(); await page.locator('[data-view="saved"]').click(); assert.equal(await page.locator('.card').count(), 1);
    await page.locator('[data-view="today"]').click();
    await page.evaluate(() => navigator.serviceWorker.ready); await page.reload();
    await context.setOffline(true); await page.reload(); assert.ok(await page.locator('.card').count() > 0); assert.equal(await page.evaluate(() => fetch('./uncached-probe').then(() => 'network', () => 'offline')), 'offline'); await page.waitForFunction(() => !document.getElementById('offline').hidden);
    await context.setOffline(false);
    // Corrupted persistence must not break the page or be silently overwritten.
    await page.evaluate(() => localStorage.setItem('personal-newsroom-state-v2', '{broken')); await page.reload();
    assert.ok(await page.locator('.card').count() > 0); await page.locator('.like:not(:disabled)').first().click();
    assert.equal(await page.evaluate(() => localStorage.getItem('personal-newsroom-state-v2')), '{broken');
    assert.deepEqual(errors, []);
    if (process.env.QA_OUTPUT) {
      fs.mkdirSync(process.env.QA_OUTPUT, { recursive: true });
      await page.evaluate(() => localStorage.removeItem('personal-newsroom-state-v2')); await page.reload();
      if (process.env.QA_FONT_DIR) {
        const dir = process.env.QA_FONT_DIR;
        const css = fs.readFileSync(path.join(dir, '400.css'), 'utf8').replace(/url\(\.\/([^)]*)\)/g, (_, file) => 'url(data:font/woff2;base64,' + fs.readFileSync(path.join(dir, file)).toString('base64') + ')');
        await page.addStyleTag({ content: css }); await page.evaluate(() => document.fonts.ready);
      }
      await page.screenshot({ path: path.join(process.env.QA_OUTPUT, 'mobile.png') });
      await page.setViewportSize({ width: 1280, height: 900 }); await page.screenshot({ path: path.join(process.env.QA_OUTPUT, 'desktop.png') });
    }
    console.log('PASS: mobile/desktop, votes, reload, saved/history, search, tags, settings, backup/import, offline, corrupt storage; no page errors');
  } finally { await browser.close(); server.close(); }
})().catch(e => { console.error(e); process.exit(1); });
