const { test } = require('node:test');
const assert = require('node:assert/strict');
const L = require('../public/learning.js');
function storage(seed = {}) { return { getItem: k => seed[k] || null, setItem: (k, v) => { seed[k] = v; } }; }
const a = { id: 'a', category: 'egg', title: '冷凍技術と商品開発', source: 'Food', score: 50, url: 'https://example.org/a' };
test('vote persists, toggles, reverses and does not compound on rerank', () => {
  const memory = storage(), s = L.createStore(memory);
  s.vote(a, 'like', ['冷凍技術']);
  assert.equal(L.createStore(memory).state.feedback.egg.length, 1);
  const score = L.rank([a], s.state)[0].priority;
  assert.ok(score > 50);
  assert.equal(L.rank([a], s.state)[0].priority, score);
  s.vote(a, 'bad'); assert.ok(L.rank([a], s.state)[0].priority < 50);
  s.vote(a, 'bad'); assert.equal(L.rank([a], s.state)[0].priority, 50);
});
test('category isolation, learning pause, and samples cannot train', () => {
  const s = L.createStore(storage()); s.vote(a, 'like');
  assert.equal(L.rank([{ ...a, category: 'food' }], s.state)[0].priority, 50);
  s.update(n => { n.settings.learning = false; });
  assert.equal(L.rank([a], s.state)[0].priority, 50);
  s.vote({ ...a, id: 'sample', source_type: 'fallback' }, 'like');
  assert.equal(s.state.feedback.egg.length, 1);
});
test('corrupt storage and quota failure do not destroy data or report a saved vote', () => {
  const broken = storage({ [L.KEY]: '{bad' }); const s = L.createStore(broken);
  assert.equal(s.error, 'storage'); assert.equal(broken.getItem(L.KEY), '{bad');
  const denied = L.createStore({ getItem() { return null; }, setItem() { throw Error('quota'); } });
  assert.throws(() => denied.vote(a, 'like')); assert.deepEqual(denied.state.feedback, {});
});
test('legacy migration and import are deduplicated with newest vote winning', () => {
  const old = { egg: [{ ...a, value: 'like', at: '2026-01-01T00:00:00Z', keywords: ['冷凍'] }] };
  const s = L.createStore(storage({ [L.LEGACY]: JSON.stringify(old) }));
  s.import(old); s.import(old); assert.equal(s.state.feedback.egg.length, 1);
  s.vote(a, 'bad'); s.import(old); assert.equal(s.state.feedback.egg[0].value, 'bad');
  s.save(a); s.update(n => { n.settings.theme = 'dark'; }); const restored = L.createStore(storage()); restored.import(JSON.parse(s.export()));
  assert.equal(restored.state.saved['egg:a'].title, a.title); assert.equal(restored.state.settings.theme, 'dark');
});
test('invalid import is atomic, malicious URLs and future votes are rejected', () => {
  const s = L.createStore(storage()); s.vote(a, 'like'); const before = s.export();
  assert.throws(() => s.import({ egg: [{ ...a, value: 'bad', at: '2099-01-01' }] }));
  assert.throws(() => s.import({ version: 99 })); assert.equal(s.export(), before);
  assert.equal(L.safeURL('javascript:alert(1)'), ''); assert.equal(L.safeURL('https://u:p@example.org'), '');
  assert.equal(L.safeURL('https://example.org/'), 'https://example.org/');
});
test('manual tags influence matching articles, samples always sort last', () => {
  const s = L.createStore(storage()); s.update(n => { n.tags.egg = ['冷凍技術']; });
  const result = L.rank([{ ...a, id: 'sample', source_type: 'fallback', score: 999 }, a], s.state);
  assert.equal(result[0].id, 'a'); assert.ok(result[0].matched.includes('冷凍技術'));
});
test('two tabs merge sequential edits; corrupt storage requires explicit recovery', () => {
  const memory = storage(), tab1 = L.createStore(memory), tab2 = L.createStore(memory);
  tab1.vote(a, 'like'); tab2.save(a);
  assert.equal(L.createStore(memory).state.feedback.egg.length, 1);
  const broken = L.createStore(storage({ [L.KEY]: '{bad' }));
  assert.throws(() => broken.vote(a, 'like'));
  broken.import(JSON.parse(tab2.export())); assert.equal(broken.error, '');
  assert.equal(broken.state.feedback.egg.length, 1);
});
