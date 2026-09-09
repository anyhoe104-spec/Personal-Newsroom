// All UI copy is dictionary-backed; external article text is rendered as text.
const { t } = window.i18n;
const L = window.NewsroomLearning;
const $ = id => document.getElementById(id);
let store;
try { store = L.createStore(window.localStorage); }
catch { store = L.createStore({ getItem() { throw Error('storage'); }, setItem() { throw Error('storage'); } }); }
let data = { articles: [], categories: {} };
try { data = JSON.parse($('newsData').textContent); if (!Array.isArray(data.articles)) throw Error(); }
catch { data = { articles: [], categories: {} }; }
const articles = data.articles.filter(a => a && L.categories.includes(a.category) && typeof a.id === 'string');
let view = 'today', category = 'all', query = '', sort = 'recommended', unread = false;
const label = c => t(`category.${c}`);
const titleOf = a => a.translated_title || a.fallback_title || a.display_title || a.title;
const vocabulary = c => [...(data.vocabulary?.[c] || []), ...(store.state.tags[c] || [])];
function el(tag, text, className) { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (className) n.className = className; return n; }
function button(text, action, className) { const b = el('button', text, className); b.type = 'button'; b.onclick = action; return b; }
let noticeTimer;
function notice(key) { const message = t(`reader.${key}`); $('feedbackStatus').textContent = message; if ($('settingsStatus')) $('settingsStatus').textContent = message; clearTimeout(noticeTimer); if (!['storage_error', 'save_failed'].includes(key)) noticeTimer = setTimeout(() => { $('feedbackStatus').textContent = ''; }, 5000); }
function update(fn) { try { fn(); render(); return true; } catch { notice('save_failed'); return false; } }
function download(content, name) { const url = URL.createObjectURL(new Blob([content], { type: 'application/json' })); const a = el('a'); a.href = url; a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
function relative(date) { const d = new Date(date); return Number.isFinite(d.getTime()) ? d.toLocaleDateString('ja-JP', { month: 'numeric', day: 'numeric' }) : t('reader.unknown_date'); }
function renderNav() {
  $('tabs').replaceChildren();
  for (const c of ['all', ...L.categories]) {
    const b = button(c === 'all' ? t('reader.all') : label(c), () => { category = c; render(); }, `tab ${category === c ? 'active' : ''}`);
    b.setAttribute('aria-pressed', String(category === c)); $('tabs').append(b);
  }
  document.querySelectorAll('[data-view]').forEach(b => { b.setAttribute('aria-current', b.dataset.view === view ? 'page' : 'false'); });
}
function card(a) {
  const card = el('article', undefined, 'card'); card.dataset.id = a.id;
  const top = el('div', undefined, 'card-top');
  top.append(el('span', `${label(a.category)} · ${a.source || ''}`, 'source'), el('time', relative(a.published_at), 'date')); card.append(top);
  const h = el('h2'), link = el('a', titleOf(a), 'title'); const url = L.safeURL(a.url);
  if (url && !L.sample(a)) { link.href = url; link.target = '_blank'; link.rel = 'noopener noreferrer'; link.onclick = () => { try { store.markRead(a); } catch { notice('save_failed'); } }; }
  h.append(link); card.append(h);
  const markers = el('div', undefined, 'markers');
  if (L.sample(a)) markers.append(el('span', t('reader.sample'), 'badge warning'));
  else if (a.translated_title) markers.append(el('span', t('reader.translated'), 'badge'));
  if (store.state.read[L.idKey(a)]) markers.append(el('span', t('reader.read'), 'badge'));
  if (a.adjustment) markers.append(el('span', t('reader.adjusted', { n: `${a.adjustment > 0 ? '+' : ''}${a.adjustment}` }), 'badge learned'));
  if (markers.childNodes.length) card.append(markers);
  if (a.matched?.length && store.state.settings.learning) card.append(el('p', t('reader.because', { tags: a.matched.join(', ') }), 'reason'));
  const details = el('details', undefined, 'article-detail'); details.open = !store.state.settings.compact;
  details.append(el('summary', t('reader.summary')));
  const list = el('ul', undefined, 'summary');
  const lines = a.translated_summary?.length ? a.translated_summary : a.summary;
  (Array.isArray(lines) ? lines : []).filter(Boolean).slice(0, 3).forEach(line => list.append(el('li', line))); details.append(list);
  if (a.impact) details.append(el('p', a.impact, 'impact'));
  if (a.egg_insight) details.append(el('p', a.egg_insight, 'egg-insight'));
  if (a.original_title && a.original_title !== titleOf(a)) details.append(el('p', t('article.original_title_prefix', { title: a.original_title }), 'original-title'));
  card.append(details);
  const actions = el('div', undefined, 'actions');
  const vote = (store.state.feedback[a.category] || []).find(v => v.id === a.id)?.value;
  for (const v of ['like', 'bad']) {
    const b = button(t(`feedback.${v}`), () => {
      const focus = `${a.category}:${a.id}:${v}`;
      if (update(() => store.vote(a, v, vocabulary(a.category)))) { notice('learned'); document.querySelectorAll('[data-focus]').forEach(n => { if (n.dataset.focus === focus) n.focus({ preventScroll: true }); }); }
    }, `feedback ${v} ${vote === v ? 'selected' : ''}`);
    b.dataset.focus = `${a.category}:${a.id}:${v}`; b.disabled = L.sample(a); b.setAttribute('aria-pressed', String(vote === v)); actions.append(b);
  }
  const saved = Boolean(store.state.saved[L.idKey(a)]);
  const save = button(t(saved ? 'reader.saved' : 'reader.save'), () => { if (update(() => store.save(a))) notice(saved ? 'unsaved' : 'saved_notice'); }, `save ${saved ? 'selected' : ''}`);
  save.disabled = L.sample(a); save.setAttribute('aria-pressed', String(saved)); actions.append(save); card.append(actions); return card;
}
function renderArticles() {
  const pool = view === 'saved' ? Object.values(store.state.saved) : view === 'history'
    ? L.categories.flatMap(c => store.state.feedback[c] || []).filter(v => v.value !== 'none') : articles;
  const byKey = new Map(articles.map(a => [L.idKey(a), a]));
  let ranked = L.rank(pool.map(a => byKey.get(L.idKey(a)) || a), store.state, data.vocabulary);
  ranked = ranked.filter(a => (category === 'all' || a.category === category) && (!unread || !store.state.read[L.idKey(a)]) && `${titleOf(a)} ${a.source} ${(a.summary || []).join(' ')}`.toLowerCase().includes(query.toLowerCase()));
  if (sort === 'latest') ranked.sort((a, b) => (Date.parse(b.published_at) || 0) - (Date.parse(a.published_at) || 0));
  $('resultCount').textContent = t('reader.results', { n: ranked.length });
  $('app').replaceChildren(...ranked.map(card));
  if (!ranked.length) { const panel = el('section', undefined, 'empty'); panel.append(el('h2', t(`reader.empty_${view}`)), el('p', t('reader.empty_hint'))); if (query || unread || category !== 'all') panel.append(button(t('reader.clear_filters'), () => { query = ''; unread = false; category = 'all'; $('search').value = ''; $('unread').checked = false; render(); })); $('app').append(panel); }
}
function renderInsights() {
  const panel = $('app'); panel.replaceChildren(); $('resultCount').textContent = t('reader.insights_hint');
  for (const c of L.categories.filter(c => category === 'all' || c === category)) {
    const p = L.profile(store.state, c), section = el('section', undefined, 'card insight');
    section.append(el('h2', label(c)), el('p', t('reader.votes', { n: p.count }), 'muted'));
    const heading = el('h3', t('reader.learned_tags')); section.append(heading);
    const tags = el('div', undefined, 'tag-list');
    [...p.tags].filter(([, n]) => n !== 0).sort((a, b) => b[1] - a[1]).slice(0, 12).forEach(([w, n]) => tags.append(el('span', `${w} ${n > 0 ? '+' : ''}${n}`, `badge ${n > 0 ? 'learned' : 'warning'}`)));
    section.append(tags.childNodes.length ? tags : el('p', t('reader.start_learning'), 'muted'));
    section.append(el('h3', t('reader.follow_tags')));
    const followed = el('div', undefined, 'tag-list');
    (store.state.tags[c] || []).forEach(w => followed.append(button(`${w} ×`, () => update(() => store.update(n => { n.tags[c] = n.tags[c].filter(x => x !== w); })), 'tag-remove')));
    section.append(followed);
    const form = el('form', undefined, 'tag-form'), input = el('input'); input.maxLength = 50; input.minLength = 2; input.required = true; input.placeholder = t('reader.tag_placeholder'); input.setAttribute('aria-label', `${label(c)} ${t('reader.follow_tags')}`);
    const add = el('button', t('reader.add')); add.type = 'submit'; form.append(input, add);
    form.onsubmit = e => { e.preventDefault(); const tag = input.value.trim().toLowerCase(); if (tag.length < 2) return; if ((store.state.tags[c] || []).length >= 30) { notice('tag_limit'); return; } update(() => store.update(n => { n.tags[c] = [...new Set([...(n.tags[c] || []), tag])]; })); }; section.append(form);
    section.append(el('h3', t('reader.source_review')));
    if (!p.sources.size) section.append(el('p', t('reader.start_learning'), 'muted'));
    for (const [source, net] of p.sources) {
      const count = (store.state.feedback[c] || []).filter(v => v.source === source && v.value !== 'none').length;
      section.append(el('p', t(`reader.${count < 3 ? 'source_wait' : net >= 2 ? 'source_promote' : net <= -2 ? 'source_watch' : 'source_keep'}`, { source, n: count })));
    }
    const best = [...p.tags].filter(([, n]) => n >= 2).sort((a, b) => b[1] - a[1])[0];
    if (best) section.append(el('p', t(`reader.idea_${c}`, { tag: best[0] }), 'impact'));
    panel.append(section);
  }
}
function render() {
  document.documentElement.dataset.theme = store.state.settings.theme;
  document.body.classList.toggle('compact', store.state.settings.compact);
  $('viewTitle').textContent = t(`reader.view_${view}`); renderNav();
  $('filters').hidden = view === 'insights';
  view === 'insights' ? renderInsights() : renderArticles();
  const votes = L.categories.reduce((n, c) => n + L.profile(store.state, c).count, 0);
  $('learningCount').textContent = t(store.state.settings.learning ? 'reader.learning_count' : 'reader.learning_paused', { n: votes });
  $('learningToggle').checked = store.state.settings.learning; $('compactToggle').checked = store.state.settings.compact; $('theme').value = store.state.settings.theme;
}
window.i18n.applyStaticText();
$('generatedAt').textContent = data.generated_at ? new Date(data.generated_at).toLocaleString('ja-JP') : t('reader.unknown_date');
const newest = Math.max(0, ...articles.filter(a => !L.sample(a)).map(a => Date.parse(a.published_at) || 0));
if (!newest || Date.now() - newest > 172800000) $('freshness').hidden = false;
if (store.error) notice('storage_error');
$('search').oninput = e => { query = e.target.value; renderArticles(); };
$('sort').onchange = e => { sort = e.target.value; renderArticles(); };
$('unread').onchange = e => { unread = e.target.checked; renderArticles(); };
document.querySelectorAll('[data-view]').forEach(b => { b.onclick = () => { view = b.dataset.view; render(); window.scrollTo({ top: 0, behavior: 'instant' }); }; });
$('openSettings').onclick = () => $('settings').showModal();
$('closeSettings').onclick = () => $('settings').close();
$('learningToggle').onchange = e => update(() => store.update(n => { n.settings.learning = e.target.checked; }));
$('compactToggle').onchange = e => update(() => store.update(n => { n.settings.compact = e.target.checked; }));
$('theme').onchange = e => update(() => store.update(n => { n.settings.theme = e.target.value; }));
$('downloadBackup').onclick = () => { let content = store.export(); if (store.error) { try { content = localStorage.getItem(L.KEY) || localStorage.getItem(L.LEGACY) || content; } catch {} } download(content, 'newsroom-backup.json'); };
$('downloadFeedback').onclick = () => download(store.feedbackExport(), 'feedback.json');
$('copyFeedback').onclick = async () => { try { await navigator.clipboard.writeText(store.feedbackExport()); notice('copied'); } catch { notice('copy_failed'); } };
$('importBackup').onchange = async e => {
  const file = e.target.files[0]; if (!file) return;
  try { if (file.size > 5000000) throw Error(); const payload = JSON.parse(await file.text()); store.import(payload); render(); notice('imported'); }
  catch { notice('import_failed'); } finally { e.target.value = ''; }
};
$('resetData').onclick = () => { if (window.confirm(t('reader.reset_confirm'))) { if (update(() => store.reset())) notice('reset_done'); } };
window.addEventListener('storage', e => { if (e.key === L.KEY || e.key === null) { try { store = L.createStore(window.localStorage); render(); } catch { notice('storage_error'); } } });
function connection() { $('offline').hidden = navigator.onLine; }
window.addEventListener('online', connection); window.addEventListener('offline', connection); connection();
render();
