const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { test } = require("node:test");

const script = fs.readFileSync(
  process.env.NEWSROOM_APP_PATH || path.join(__dirname, "../public/app.js"), "utf8",
);

function boot(stored, blocked = false) {
  const writes = [];
  const item = { id: "article-1", category: "business", title: "記事", summary: [], score: 50 };
  function element() {
    return {
      children: [], dataset: {}, classList: { add() {} },
      appendChild(child) { this.children.push(child); },
      addEventListener() {}, remove() {},
      querySelector() { return element(); }, querySelectorAll() { return []; },
      cloneNode() { return element(); },
    };
  }
  const elements = Object.fromEntries(
    ["tabs", "app", "articleTemplate", "generatedAt", "copyFeedback", "downloadFeedback", "feedbackStatus", "newsData"]
      .map((id) => [id, element()]),
  );
  elements.articleTemplate.content = element();
  elements.newsData.textContent = JSON.stringify({
    generated_at: "2026-09-08T00:00:00Z", categories: { business: "経営" }, articles: [item],
  });
  const context = vm.createContext({
    document: { getElementById: (id) => elements[id], createElement: element },
    window: { i18n: { t: (key) => key === "app.locale_tag" ? "ja-JP" : key, tList: () => [], applyStaticText() {} } },
    localStorage: {
      getItem() { if (blocked) throw new Error("Storage denied"); return stored; },
      setItem(...args) { writes.push(args); },
    },
  });
  vm.runInContext(script, context);
  assert.equal(elements.app.children.length, 1, "news still renders");
  assert.deepEqual(writes, [], "startup must not overwrite saved feedback");
  return JSON.parse(vm.runInContext("JSON.stringify(normalizedFeedbackExport())", context));
}

test("valid votes and metadata are preserved", () => {
  const vote = { id: "article-1", value: "like", source: "source-a", keywords: ["経営"], at: "2026-09-08" };
  assert.deepEqual(boot(JSON.stringify({ business: [vote] })).business, [vote]);
});

test("missing storage starts with empty feedback", () => {
  assert.deepEqual(boot(null).business, []);
});

test("malformed JSON does not prevent news rendering", () => {
  assert.deepEqual(boot("{broken").business, []);
});

test("non-object storage is ignored", () => {
  for (const value of ["null", "42", "true", '"text"', "[]"]) {
    assert.deepEqual(boot(value).business, []);
  }
});

test("non-array categories are ignored without losing valid categories", () => {
  const vote = { id: "food-1", value: "bad" };
  const result = boot(JSON.stringify({ business: {}, food: [vote] }));
  assert.deepEqual(result.business, []);
  assert.deepEqual(result.food, [vote]);
});

test("invalid vote entries are removed while valid votes survive", () => {
  const vote = { id: "article-1", value: "like" };
  const result = boot(JSON.stringify({ business: [null, 2, [], {}, { id: "" , value: "like" }, { id: "x", value: "other" }, vote] }));
  assert.deepEqual(result.business, [vote]);
});

test("denied storage access does not prevent news rendering", () => {
  assert.deepEqual(boot(null, true).business, []);
});
