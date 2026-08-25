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

generatedAt.textContent = new Date(data.generated_at).toLocaleString("ja-JP", {
  month: "numeric",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

function createFallbackData() {
  const categories = {
    business: "経営・ビジネス",
    food: "スイーツ・飲食",
    ai_dev: "AI・開発",
    egg: "卵",
  };
  const themes = {
    business: ["新規事業の成長余地", "市場構造の変化", "経営判断の材料", "価格戦略と顧客価値", "組織開発と生産性", "資本政策の論点", "海外市場の兆し", "ブランド再設計", "提携による拡張", "業務プロセス改善"],
    food: ["季節限定スイーツ", "カフェ業態の新商品", "外食チェーンの売場改善", "ベーカリーの素材訴求", "冷凍スイーツの伸長", "地域食材の活用", "テイクアウト需要", "小容量商品の企画", "健康志向メニュー", "SNS起点の話題化"],
    ai_dev: ["LLM活用パターン", "開発者向けAPI更新", "エージェント設計", "推論コスト最適化", "コード生成ワークフロー", "モデル評価の実務", "RAG改善", "ローカル開発環境", "AIセキュリティ", "プロンプト運用"],
    egg: ["ゆで卵商品の差別化", "温泉卵の品質安定", "煮卵の味付け技術", "卵加工品の新市場", "惣菜向け卵素材", "殻むき工程の改善", "たんぱく訴求商品", "海外の卵加工トレンド", "チルド流通の工夫", "商品開発事例"],
  };
  const articles = categoryKeys.flatMap((category) =>
    themes[category].map((theme, index) => {
      const label = categories[category];
      const raw = `${theme}に関する初回MVP用のフォールバック記事です。RSS取得後は実ニュースに置き換わります。`;
      return {
        id: `${category}-${index + 1}`,
        title: `${label}: ${theme}`,
        url: `https://example.com/personal-newsroom/${category}/${index + 1}`,
        source: category === "egg" && index === 7 ? "Food Business News" : "Fallback Sample",
        source_region: category === "egg" && index === 7 ? "global" : "jp",
        category,
        category_label: label,
        published_at: new Date(Date.now() - index * 3600000).toISOString(),
        raw_summary: raw,
        summary: [`${label}で注目したい動きです。`, raw, "今後の事業・開発・購買判断のヒントとして確認します。"],
        impact: "自分の関心テーマに近ければ、次の深掘り候補として保存します。",
        egg_insight: category === "egg" ? "加工技術・商品企画・売場展開のどこに応用できるかを見る価値があります。" : "",
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
    button.textContent = `${data.categories[key]} ${count}`;
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
    const card = node.querySelector(".card");
    const title = node.querySelector(".title");
    const displayTitle = article.translated_title || article.fallback_title || article.display_title || article.title;
    title.textContent = displayTitle;
    title.href = article.url;
    const originalTitle = node.querySelector(".original-title");
    if (article.original_title && article.original_title !== displayTitle) {
      originalTitle.textContent = `原文: ${article.original_title}`;
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
