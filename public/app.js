// UI copy goes through i18n.t(); article text itself comes from data/articles.json
// and is never translated here.
const { t, tList } = window.i18n;

window.i18n.applyStaticText();

const embeddedData = JSON.parse(document.getElementById("newsData").textContent);
const categoryKeys = ["business", "food", "ai_dev", "egg"];
const data = embeddedData.articles.length ? embeddedData : createFallbackData();
const tabs = document.getElementById("tabs");
const app = document.getElementById("app");
const template = document.getElementById("articleTemplate");
const generatedAt = document.getElementById("generatedAt");
const copyFeedbackButton = document.getElementById("copyFeedback");
const downloadFeedbackButton = document.getElementById("downloadFeedback");
const feedbackStatus = document.getElementById("feedbackStatus");
const feedbackKey = "personal-newsroom-feedback-v1";

let activeCategory = categoryKeys[0];
let feedback = JSON.parse(localStorage.getItem(feedbackKey) || "{}");

generatedAt.textContent = new Date(data.generated_at).toLocaleString(t("app.locale_tag"), {
  month: "numeric",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

function categoryLabel(key) {
  return (data.categories && data.categories[key]) || t(`category.${key}`);
}

function createFallbackData() {
  const categories = Object.fromEntries(categoryKeys.map((key) => [key, t(`category.${key}`)]));
  const articles = categoryKeys.flatMap((category) =>
    tList(`fallback.themes.${category}`).map((theme, index) => {
      const label = categories[category];
      const raw = t("fallback.raw_summary", { theme });
      const isGlobalSample = category === "egg" && index === 7;
      return {
        id: `${category}-${index + 1}`,
        title: t("fallback.title", { label, theme }),
        url: `https://example.com/personal-newsroom/${category}/${index + 1}`,
        source: isGlobalSample ? t("fallback.global_source_name") : t("fallback.source_name"),
        source_region: isGlobalSample ? "global" : "jp",
        category,
        category_label: label,
        published_at: new Date(Date.now() - index * 3600000).toISOString(),
        raw_summary: raw,
        summary: [t("fallback.summary_lead", { label }), raw, t("fallback.summary_tail")],
        impact: t("fallback.impact"),
        egg_insight: category === "egg" ? t("fallback.egg_insight") : "",
        score: Number((92 - index * 3.7).toFixed(1)),
      };
    })
  );
  return { generated_at: new Date().toISOString(), categories, articles };
}

function saveFeedback() {
  localStorage.setItem(feedbackKey, JSON.stringify(feedback));
}

function normalizedFeedbackExport() {
  return categoryKeys.reduce((payload, category) => {
    payload[category] = feedback[category] || [];
    return payload;
  }, {});
}

function setFeedbackStatus(message) {
  feedbackStatus.textContent = message;
  window.setTimeout(() => {
    if (feedbackStatus.textContent === message) feedbackStatus.textContent = "";
  }, 3200);
}

async function copyFeedback() {
  const json = JSON.stringify(normalizedFeedbackExport(), null, 2);
  await navigator.clipboard.writeText(json);
  setFeedbackStatus("コピーしました");
}

function downloadFeedback() {
  const json = JSON.stringify(normalizedFeedbackExport(), null, 2);
  const blob = new Blob([`${json}\n`], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "feedback.json";
  link.click();
  URL.revokeObjectURL(link.href);
  setFeedbackStatus("保存しました");
}

function articleKeywords(article) {
  return `${article.title} ${article.raw_summary || ""}`
    .toLowerCase()
    .match(/[A-Za-z0-9_+#.-]+|[\u3040-\u30ff\u3400-\u9fff]+/g) || [];
}

function setFeedback(article, value) {
  const categoryItems = feedback[article.category] || [];
  const nextItem = {
    id: article.id,
    value,
    title: article.title,
    source: article.source,
    keywords: [...new Set(articleKeywords(article))].slice(0, 20),
    at: new Date().toISOString(),
  };
  feedback[article.category] = categoryItems.filter((item) => item.id !== article.id);
  feedback[article.category].push(nextItem);
  saveFeedback();
  renderArticles();
}

function currentFeedback(article) {
  return (feedback[article.category] || []).find((item) => item.id === article.id)?.value;
}

function renderTabs() {
  tabs.innerHTML = "";
  categoryKeys.forEach((key) => {
    const count = data.articles.filter((article) => article.category === key).length;
    const button = document.createElement("button");
    button.type = "button";
    button.className = `tab ${key === activeCategory ? "active" : ""}`;
    button.textContent = t("nav.tab_label", { label: categoryLabel(key), count });
    button.addEventListener("click", () => {
      activeCategory = key;
      renderTabs();
      renderArticles();
    });
    tabs.appendChild(button);
  });
}

function renderArticles() {
  app.innerHTML = "";
  const articles = data.articles
    .filter((article) => article.category === activeCategory)
    .sort((a, b) => b.score - a.score)
    .slice(0, 10);

  articles.forEach((article) => {
    const node = template.content.cloneNode(true);
    window.i18n.applyStaticText(node);
    const card = node.querySelector(".card");
    const title = node.querySelector(".title");
    const displayTitle = article.translated_title || article.fallback_title || article.display_title || article.title;
    title.textContent = displayTitle;
    title.href = article.url;
    const originalTitle = node.querySelector(".original-title");
    if (article.original_title && article.original_title !== displayTitle) {
      originalTitle.textContent = t("article.original_title_prefix", { title: article.original_title });
    } else {
      originalTitle.remove();
    }
    node.querySelector(".source").textContent = article.source;
    node.querySelector(".score").textContent = `${article.score}`;
    node.querySelector(".category").textContent = article.category_label;
    const summary = node.querySelector(".summary");
    const translatedSummary = (article.translated_summary || []).filter(Boolean);
    const summaryLines = translatedSummary.length ? translatedSummary : article.summary;
    summaryLines.filter(Boolean).slice(0, 3).forEach((line) => {
      const li = document.createElement("li");
      li.textContent = line;
      summary.appendChild(li);
    });
    node.querySelector(".impact").textContent = article.impact;
    const eggInsight = node.querySelector(".egg-insight");
    if (article.category === "egg" && article.egg_insight) {
      eggInsight.textContent = article.egg_insight;
    } else {
      eggInsight.remove();
    }
    const selected = currentFeedback(article);
    node.querySelectorAll(".feedback").forEach((button) => {
      if (button.dataset.value === selected) button.classList.add("selected");
      button.addEventListener("click", () => setFeedback(article, button.dataset.value));
    });
    card.dataset.feedback = selected || "";
    app.appendChild(node);
  });
}

renderTabs();
renderArticles();

copyFeedbackButton.addEventListener("click", () => {
  copyFeedback().catch(() => setFeedbackStatus("コピーに失敗しました"));
});
downloadFeedbackButton.addEventListener("click", downloadFeedback);
