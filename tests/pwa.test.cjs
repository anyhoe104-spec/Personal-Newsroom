const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

test('offline banner updates immediately and an online probe restores it', async () => {
  const events = {}, banner = { hidden: true };
  const navigator = { onLine: true };
  const context = {
    navigator,
    window: { addEventListener: (name, fn) => { events[name] = fn; } },
    document: { getElementById: id => id === 'offline' ? banner : { addEventListener() {} } },
    fetch: async () => ({ headers: { get: () => null } }),
  };
  vm.runInNewContext(fs.readFileSync(require.resolve('../public/pwa.js'), 'utf8'), context);
  await Promise.resolve();
  assert.equal(banner.hidden, true);
  navigator.onLine = false;
  events.offline();
  assert.equal(banner.hidden, false);
  navigator.onLine = true;
  await events.online();
  assert.equal(banner.hidden, true);
});
