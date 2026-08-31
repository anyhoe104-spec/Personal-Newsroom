/**
 * Minimal translation hook for the Personal-Newsroom UI.
 *
 * Japanese is the default and only shipped locale, so behaviour is unchanged:
 * every key resolves through MESSAGES.ja. Adding a second locale later means
 * adding one more object to MESSAGES and calling i18n.setLocale("en") — no
 * component or rendering change.
 *
 * Static markup keeps its Japanese text inline and is annotated with
 * data-i18n / data-i18n-attr, so the page still reads correctly if this script
 * fails to load.
 */
(function (global) {
  const DEFAULT_LOCALE = "ja";

  const MESSAGES = {
    ja: {
      app: {
        title: "Personal-Newsroom",
        name: "Personal-Newsroom",
        locale_tag: "ja-JP",
      },
      header: {
        headline: "今日読むべき40本",
        updated_label: "更新:",
      },
      nav: {
        categories_aria_label: "カテゴリ",
        // `${label} ${count}` — label is the category name, count the article count.
        tab_label: "{label} {count}",
      },
      article: {
        original_title_prefix: "原文: {title}",
      },
      feedback: {
        like: "いいね",
        bad: "バッド",
      },
      // Category names must match config/sources.yaml. Live data supplies these
      // labels; the dictionary is the fallback when no articles are embedded.
      category: {
        business: "経済・ビジネス",
        food: "スイーツ・飲食",
        ai_dev: "AI・活用",
        egg: "卵・食品開発",
      },
      fallback: {
        source_name: "Fallback Sample",
        global_source_name: "Food Business News",
        raw_summary: "{theme}に関する初回MVP用のフォールバック記事です。RSS取得後は実ニュースに置き換わります。",
        title: "{label}: {theme}",
        summary_lead: "{label}で注目したい動きです。",
        summary_tail: "今後の事業・開発・購買判断のヒントとして確認します。",
        impact: "自分の関心テーマに近ければ、次の深掘り候補として保存します。",
        egg_insight: "加工技術・商品企画・売場展開のどこに応用できるかを見る価値があります。",
        themes: {
          business: [
            "新規事業の成長余地",
            "市場構造の変化",
            "経営判断の材料",
            "価格戦略と顧客価値",
            "組織開発と生産性",
            "資本政策の論点",
            "海外市場の兆し",
            "ブランド再設計",
            "提携による拡張",
            "業務プロセス改善",
          ],
          food: [
            "季節限定スイーツ",
            "カフェ業態の新商品",
            "外食チェーンの売場改善",
            "ベーカリーの素材訴求",
            "冷凍スイーツの伸長",
            "地域食材の活用",
            "テイクアウト需要",
            "小容量商品の企画",
            "健康志向メニュー",
            "SNS起点の話題化",
          ],
          ai_dev: [
            "LLM活用パターン",
            "開発者向けAPI更新",
            "エージェント設計",
            "推論コスト最適化",
            "コード生成ワークフロー",
            "モデル評価の実務",
            "RAG改善",
            "ローカル開発環境",
            "AIセキュリティ",
            "プロンプト運用",
          ],
          egg: [
            "ゆで卵商品の差別化",
            "温泉卵の品質安定",
            "煮卵の味付け技術",
            "卵加工品の新市場",
            "惣菜向け卵素材",
            "殻むき工程の改善",
            "たんぱく訴求商品",
            "海外の卵加工トレンド",
            "チルド流通の工夫",
            "商品開発事例",
          ],
        },
      },
    },
  };

  let activeLocale = DEFAULT_LOCALE;

  function lookup(locale, key) {
    const parts = String(key).split(".");
    let node = MESSAGES[locale];
    for (const part of parts) {
      if (node === null || typeof node !== "object" || !(part in node)) return undefined;
      node = node[part];
    }
    return node;
  }

  function resolve(key) {
    const value = lookup(activeLocale, key);
    return value === undefined ? lookup(DEFAULT_LOCALE, key) : value;
  }

  function interpolate(template, params) {
    if (!params) return template;
    return template.replace(/\{(\w+)\}/g, (match, name) =>
      Object.prototype.hasOwnProperty.call(params, name) ? String(params[name]) : match
    );
  }

  /** Translate `key`. Returns the key itself when it is missing, so a typo is visible. */
  function t(key, params) {
    const value = resolve(key);
    if (typeof value !== "string") return key;
    return interpolate(value, params);
  }

  /** Translate a key whose value is an array of strings. */
  function tList(key) {
    const value = resolve(key);
    return Array.isArray(value) ? value.slice() : [];
  }

  function setLocale(locale) {
    activeLocale = MESSAGES[locale] ? locale : DEFAULT_LOCALE;
    return activeLocale;
  }

  function getLocale() {
    return activeLocale;
  }

  /**
   * Fill in every element marked with data-i18n (text) or data-i18n-attr
   * ("attribute:key" pairs, comma separated).
   */
  function applyStaticText(root) {
    const scope = root || document;
    scope.querySelectorAll("[data-i18n]").forEach((element) => {
      element.textContent = t(element.dataset.i18n);
    });
    scope.querySelectorAll("[data-i18n-attr]").forEach((element) => {
      element.dataset.i18nAttr.split(",").forEach((pair) => {
        const [attribute, key] = pair.split(":").map((part) => part.trim());
        if (attribute && key) element.setAttribute(attribute, t(key));
      });
    });
    if (scope === document) {
      document.documentElement.lang = getLocale();
    }
  }

  global.i18n = {
    t,
    tList,
    setLocale,
    getLocale,
    applyStaticText,
    DEFAULT_LOCALE,
    MESSAGES,
  };
})(window);
