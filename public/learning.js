/* Local, category-scoped learning. No credentials or personal votes leave this device. */
(function (root) {
  'use strict';
  const KEY = 'personal-newsroom-state-v2';
  const LEGACY = 'personal-newsroom-feedback-v1';
  const categories = ['business', 'food', 'ai_dev', 'egg'];
  const empty = () => ({ version: 2, feedback: {}, saved: {}, read: {}, tags: {}, settings: { learning: true, theme: 'system', compact: false } });
  const object = x => x && typeof x === 'object' && !Array.isArray(x);
  const text = x => typeof x === 'string' ? x.slice(0, 2000) : '';
  const words = x => Array.isArray(x) ? [...new Set(x.filter(v => typeof v === 'string' && v.length >= 2 && v.length <= 50))].slice(0, 30) : [];
  const clamp = (n, max) => Math.max(-max, Math.min(max, n));
  function safeURL(value) {
    try { const u = new URL(value); return ['https:', 'http:'].includes(u.protocol) && !u.username && !u.password ? u.href : ''; }
    catch { return ''; }
  }
  function sample(a) { return a.source_type === 'fallback' || /example\.com|fallback sample/i.test(`${a.url} ${a.source}`); }
  function article(a) {
    if (!object(a) || !text(a.id) || !categories.includes(a.category)) throw Error('invalid');
    return { id: text(a.id), category: a.category, title: text(a.title), source: text(a.source),
      url: safeURL(a.url), published_at: text(a.published_at), translated_title: text(a.translated_title),
      summary: Array.isArray(a.summary) ? a.summary.slice(0, 3).map(text) : [], impact: text(a.impact),
      keywords: words(a.keywords), source_type: text(a.source_type), score: Number.isFinite(a.score) ? a.score : 0 };
  }
  const idKey = a => `${a.category}:${a.id}`;
  function validDate(x) { return typeof x === 'string' && Number.isFinite(Date.parse(x)) && Date.parse(x) <= Date.now() + 300000; }
  function normalize(input) {
    if (!object(input)) throw Error('invalid');
    const state = empty();
    if (input.version !== undefined && input.version !== 2) throw Error('version');
    const feedback = input.version === 2 ? input.feedback : input;
    if (!object(feedback) || Object.keys(feedback).some(k => !categories.includes(k))) throw Error('invalid');
    for (const category of categories) {
      const rows = feedback[category] || [];
      if (!Array.isArray(rows) || rows.length > 10000) throw Error('limit');
      const votes = new Map();
      for (const row of rows) {
        if (!object(row) || !['like', 'bad', 'none'].includes(row.value) || !validDate(row.at)) throw Error('invalid');
        const a = article({ ...row, category });
        const vote = { ...a, value: row.value, at: row.at };
        if (!votes.has(a.id) || votes.get(a.id).at < vote.at) votes.set(a.id, vote);
      }
      state.feedback[category] = [...votes.values()];
    }
    for (const field of ['saved', 'read']) {
      if (input[field] === undefined) continue;
      if (!object(input[field]) || Object.keys(input[field]).length > 10000) throw Error('invalid');
      for (const [key, value] of Object.entries(input[field])) {
        if (field === 'saved') { const a = article(value); if (key !== idKey(a)) throw Error('invalid'); state.saved[key] = a; }
        else { if (!/^(business|food|ai_dev|egg):.+/.test(key) || !validDate(value)) throw Error('invalid'); state.read[key] = value; }
      }
    }
    for (const category of categories) {
      const tags = input.tags?.[category] || [];
      if (!Array.isArray(tags) || tags.length > 30 || tags.some(v => typeof v !== 'string' || v.length < 2 || v.length > 50)) throw Error('invalid');
      state.tags[category] = words(tags);
    }
    const settings = input.settings || {};
    state.settings = { learning: settings.learning !== false, compact: settings.compact === true,
      theme: ['light', 'dark', 'system'].includes(settings.theme) ? settings.theme : 'system' };
    return state;
  }
  function tokens(a, vocabulary = []) {
    const content = `${a.title || ''} ${a.translated_title || ''} ${a.raw_summary || ''} ${(a.summary || []).join(' ')}`.toLowerCase();
    const known = vocabulary.filter(w => typeof w === 'string' && w.length >= 2 && content.includes(w.toLowerCase()));
    const segments = typeof Intl.Segmenter === 'function'
      ? [...new Intl.Segmenter('ja', { granularity: 'word' }).segment(content)].filter(s => s.isWordLike).map(s => s.segment)
      : content.match(/[a-z][a-z0-9+#.-]{1,30}/g) || [];
    const stop = new Set(['する', 'した', 'こと', 'ため', 'ある', 'いる', 'なる', 'です', 'ます', 'これ', 'それ', 'から', 'など', 'について', 'the', 'and', 'for', 'with', 'this', 'that']);
    return words([...known, ...segments.filter(w => !stop.has(w) && !/^\d+$/.test(w))]);
  }
  function profile(state, category) {
    const tags = new Map(), sources = new Map();
    const votes = (state.feedback[category] || []).filter(v => v.value !== 'none' && !sample(v));
    for (const v of votes) {
      const amount = v.value === 'like' ? 1 : -1;
      for (const w of words(v.keywords)) tags.set(w, (tags.get(w) || 0) + amount);
      if (v.source) sources.set(v.source, (sources.get(v.source) || 0) + amount);
    }
    return { tags, sources, count: votes.length };
  }
  function rank(articles, state, vocabulary = {}) {
    const profiles = Object.fromEntries(categories.map(c => [c, profile(state, c)]));
    return articles.map(a => {
      const p = profiles[a.category] || { tags: new Map(), sources: new Map() };
      const kw = tokens(a, [...(vocabulary[a.category] || []), ...(state.tags[a.category] || []), ...p.tags.keys()]);
      const matched = kw.filter(w => (p.tags.get(w) || 0) > 0 || (state.tags[a.category] || []).includes(w));
      const tagScore = kw.reduce((n, w) => n + clamp(p.tags.get(w) || 0, 3) * 2 + ((state.tags[a.category] || []).includes(w) ? 4 : 0), 0);
      const delta = state.settings.learning && !sample(a) ? clamp(tagScore + clamp(p.sources.get(a.source) || 0, 3) * 2, 18) : 0;
      return { ...a, keywords: kw, adjustment: delta, matched: matched.slice(0, 3), priority: (Number(a.score) || 0) + delta };
    }).sort((a, b) => Number(sample(a)) - Number(sample(b)) || b.priority - a.priority || a.id.localeCompare(b.id));
  }
  function createStore(storage) {
    let state = empty(), error = '';
    try {
      const raw = storage.getItem(KEY), legacy = storage.getItem(LEGACY);
      state = raw ? normalize(JSON.parse(raw)) : legacy ? normalize(JSON.parse(legacy)) : empty();
    } catch { error = 'storage'; }
    // Commit atomically: a quota/privacy failure never pretends the vote was saved.
    function commit(next) { storage.setItem(KEY, JSON.stringify(next)); state = next; error = ''; return state; }
    return {
      get state() { return state; }, get error() { return error; },
      update(fn) { const next = structuredClone(state); fn(next); return commit(normalize(next)); },
      vote(a, value, vocabulary) {
        if (sample(a)) return state;
        return this.update(next => {
          const rows = next.feedback[a.category] || [];
          const previous = rows.find(v => v.id === a.id);
          next.feedback[a.category] = rows.filter(v => v.id !== a.id);
          next.feedback[a.category].push({ ...article(a), keywords: tokens(a, vocabulary), value: previous?.value === value ? 'none' : value, at: new Date().toISOString() });
        });
      },
      save(a) { return this.update(next => { const key = idKey(a); if (next.saved[key]) delete next.saved[key]; else next.saved[key] = article(a); }); },
      markRead(a) { return this.update(next => { next.read[idKey(a)] = new Date().toISOString(); }); },
      import(input) {
        const incoming = normalize(input);
        return this.update(next => {
          for (const c of categories) {
            const rows = new Map((next.feedback[c] || []).map(v => [v.id, v]));
            for (const v of incoming.feedback[c] || []) if (!rows.has(v.id) || rows.get(v.id).at < v.at) rows.set(v.id, v);
            next.feedback[c] = [...rows.values()];
            next.tags[c] = words([...(next.tags[c] || []), ...(incoming.tags[c] || [])]);
          }
          next.saved = { ...next.saved, ...incoming.saved };
          for (const [k, at] of Object.entries(incoming.read)) if (!next.read[k] || next.read[k] < at) next.read[k] = at;
        });
      },
      reset() { const next = empty(); storage.setItem(KEY, JSON.stringify(next)); state = next; error = ''; },
      export() { return JSON.stringify(state, null, 2); },
      feedbackExport() { return JSON.stringify(state.feedback, null, 2); },
    };
  }
  const api = { KEY, LEGACY, categories, empty, normalize, tokens, profile, rank, createStore, idKey, safeURL, sample };
  if (typeof module !== 'undefined') module.exports = api;
  else root.NewsroomLearning = api;
})(typeof window === 'undefined' ? globalThis : window);
