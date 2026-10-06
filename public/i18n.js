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
      reader: {
  all: "すべて",
  unknown_date: "日付不明",
  sample: "サンプル・評価対象外",
  translated: "日本語表示",
  read: "既読",
  adjusted: "好みの反映 {n}",
  because: "関心タグ：{tags}",
  summary: "要約・活用のヒント",
  save: "あとで読む",
  saved: "保存済み",
  saved_notice: "あとで読むに保存しました",
  unsaved: "保存を解除しました",
  learned: "評価を保存しました。並び順への反映は「順位を更新」で行えます。",
  recorded_vote: "この端末の保存済み評価：{date}（同じボタンで取消）",
  refresh_ranking: "順位を更新",
  refresh_pending: "順位を更新・変更あり",
  ranking_hint: "閲覧中の並び順は固定です。順位を更新するか、ページを開き直すと最新の好みを反映します。",
  ranking_pending: "評価・関心の変更を保存しました。「順位を更新」で並び順に反映します。",
  ranking_updated: "最新の好みで順位を更新しました",
  history_hint: "評価した日時の新しい順です。30件ずつ表示します。",
  category_filter: "表示するカテゴリ",
  more_history: "履歴をさらに30件表示（残り{n}件）",
  import_help: "「ファイル」→「ダウンロード」から newsroom-backup.json を選んでください。写真ではありません。選べない場合は下の貼り付け取り込みをお使いください。",
  paste_backup: "ファイルを選べない場合：貼り付けて取り込む",
  paste_help: "バックアップJSONの内容をすべて貼り付けてください。",
  import_pasted: "貼り付けたバックアップを取り込む",
  save_failed: "保存できませんでした。空き容量・ブラウザの保存設定をご確認ください。",
  storage_error: "保存データを読み込めません。設定からバックアップを取り込むか、データをリセットしてください。",
  results: "{n} 本の記事",
  view_today: "今日のニュース",
  view_saved: "あとで読む",
  view_history: "評価の履歴",
  view_insights: "あなたの関心",
  empty_today: "記事が見つかりません",
  empty_saved: "保存した記事はここに",
  empty_history: "評価した記事はここに",
  empty_hint: "条件を変えて探すか、今日のニュースから気になる記事を選んでください。",
  clear_filters: "検索条件をクリア",
  insights_hint: "評価から育つ、あなた専用の編集方針",
  votes: "これまで {n} 本を評価",
  learned_tags: "学習したRSSタグ",
  follow_tags: "優先して追うタグ",
  start_learning: "気になるニュースを評価すると、タグと情報源の傾向がここに育ちます。",
  tag_placeholder: "例：商品開発、冷凍技術",
  add: "追加",
  tag_limit: "タグはカテゴリごとに30個まで追加できます。",
  source_review: "情報源の見直し提案",
  source_wait: "{source}：評価収集中（{n} 本）",
  source_promote: "{source}：優先して読む候補（{n} 本の評価）",
  source_watch: "{source}：購読内容の見直し候補（{n} 本の評価）",
  source_keep: "{source}：幅広く継続して確認（{n} 本の評価）",
  idea_business: "次の一歩：「{tag}」の事例を比較し、自社への影響と検証指標をメモしてみましょう。",
  idea_food: "次の一歩：「{tag}」から季節メニューの試作案を1つ考え、原価と客単価への影響を比べてみましょう。",
  idea_ai_dev: "次の一歩：「{tag}」を日常業務1つで試し、短縮できる時間を測ってみましょう。",
  idea_egg: "次の一歩：「{tag}」を商品開発の仮説にし、試作条件と品質の評価軸をまとめてみましょう。",
  learning_count: "{n} 本の評価を学習中",
  learning_paused: "学習の反映は一時停止中",
  copied: "コピーしました",
  copy_failed: "コピーできませんでした。JSON保存をお使いください。",
  imported: "バックアップを統合しました",
  import_failed: "取り込めませんでした。5MB以内の対応JSONをご確認ください。元のデータは変更していません。",
  reset_confirm: "この端末の評価・保存記事・既読・関心タグをすべて消去します。必要なら先にバックアップを保存してください。",
  reset_done: "データをリセットしました",
  settings: "設定",
  close: "閉じる",
  search: "記事・情報源を検索",
  sort: "表示順",
  recommended: "おすすめ順",
  latest: "新しい順",
  unread: "未読のみ",
  freshness: "最新記事の取得から時間が経っています。記事の日付をご確認ください。",
  offline: "オフラインです。保存済みの画面を表示しています。",
  privacy: "評価と保存記事はこの端末のブラウザに保存します。クラウドへの自動送信はありません。機種変更前にバックアップを保存してください。",
  learning: "評価をおすすめ順に反映",
  compact: "コンパクト表示",
  theme: "表示テーマ",
  system: "端末に合わせる",
  light: "ライト",
  dark: "ダーク",
  backup: "バックアップを保存",
  import: "バックアップを取り込む",
  reset: "端末のデータをリセット",
  data: "データ管理",
  advanced: "詳細：フィードバック書き出し",
  intro: "読む。選ぶ。自分の視点が育つ。",
  tag_note: "学習タグは毎日の記事の並び順に自動反映します。RSS配信元のタグや購読URLそのものは変更しません。",
  install: "ホーム画面に追加",
  install_hint: "ブラウザのメニューから「ホーム画面に追加」を選ぶと、アプリとして開けます。"
},
      app: {
        title: "Personal-Newsroom",
        name: "Personal-Newsroom",
        locale_tag: "ja-JP",
      },
      header: {
        headline: "今日の視点を、育てる。",
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
        like: "役に立った",
        bad: "関心が薄い",
      },
      feedback_tools: {
        aria_label: "フィードバック管理",
        copy: "フィードバックをコピー",
        download: "JSON保存",
        copied: "コピーしました",
        copy_failed: "コピーに失敗しました",
        saved: "保存しました",
        download_filename: "feedback.json",
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
