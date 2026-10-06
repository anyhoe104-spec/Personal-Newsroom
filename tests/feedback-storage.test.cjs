const assert = require('node:assert/strict');
const { test } = require('node:test');
const L = require('../public/learning.js');
const vote = { id: 'article-1', category: 'business', title: '記事', value: 'like', at: '2026-09-08', source: 'source-a', keywords: ['経営'] };
function boot(value, legacy = false) {
  const writes = [], values = { [legacy ? L.LEGACY : L.KEY]: value };
  const memory = { getItem: k => values[k] ?? null, setItem: (k, v) => { writes.push([k, v]); values[k] = v; } };
  const store = L.createStore(memory);
  assert.deepEqual(writes, [], 'startup must preserve original storage');
  return { store, writes, memory };
}
test('valid legacy votes retain metadata without writing during startup', () => {
  const { store } = boot(JSON.stringify({ business: [vote] }), true);
  assert.equal(store.error, '');
  for (const field of ['id', 'value', 'at', 'source', 'keywords']) assert.deepEqual(store.state.feedback.business[0][field], vote[field]);
});
test('missing storage starts empty without writing', () => {
  assert.equal(boot(null).store.error, '');
});
test('malformed JSON preserves recoverable bytes and blocks accidental overwrite', () => {
  const { store, memory, writes } = boot('{broken');
  assert.equal(store.error, 'storage');
  assert.throws(() => store.vote(vote, 'bad'));
  assert.equal(memory.getItem(L.KEY), '{broken');
  assert.deepEqual(writes, []);
});
test('invalid top-level values report recovery error without overwriting', () => {
  for (const raw of ['null', '42', 'true', '"text"', '[]']) assert.equal(boot(raw).store.error, 'storage');
});
test('invalid category payload preserves the original until explicit recovery', () => {
  const raw = JSON.stringify({ business: {}, food: [{ ...vote, category: 'food' }] });
  const { store, memory } = boot(raw, true);
  assert.equal(store.error, 'storage');
  assert.equal(memory.getItem(L.LEGACY), raw);
  store.import({ food: [{ ...vote, category: 'food' }] });
  assert.equal(store.state.feedback.food.length, 1);
  assert.equal(memory.getItem(L.LEGACY), raw);
});
test('invalid votes cannot silently replace an existing valid vote', () => {
  const { store, writes } = boot(JSON.stringify({ business: [vote] }), true);
  for (const invalid of [null, {}, { ...vote, value: 'other' }]) assert.throws(() => store.import({ business: [invalid] }));
  assert.equal(store.state.feedback.business[0].value, 'like');
  assert.deepEqual(writes, []);
});
test('denied reads and quota failures leave storage and in-memory feedback intact', () => {
  const denied = L.createStore({ getItem() { throw Error('denied'); }, setItem() { assert.fail('write'); } });
  assert.equal(denied.error, 'storage');
  const { store, memory } = boot(JSON.stringify({ business: [vote] }), true);
  const before = store.export();
  memory.setItem = () => { throw Error('quota'); };
  assert.throws(() => store.vote(vote, 'bad'));
  assert.equal(store.export(), before);
});
