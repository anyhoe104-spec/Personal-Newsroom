# 設定層の分離計画（テーマパック化）

- 起案：2026-09-09
- 状態：Step 1〜3は実装済み、非公開テーマ準備PRはマージ済み。2026-09-18のオーナー指示でアラートURL差替えのみ先行し、現行の公開側ActionsでもSecret注入できるようにする。運用主体の切替は未完了。手順は [alert-rotation.md](alert-rotation.md) を参照。
- 起案の経緯：`project-dashboard` での公開戦略の検討（`strategy/2026-09-09-publication-strategy.md`）

このドキュメントは、次に作業するエージェントが会話履歴なしで着手できることを目的に書かれている。

---

## 1. なぜやるのか

### 現状の問題

`config/sources.yaml` に **Google アラートのRSSフィードURLが5本**含まれており、本リポジトリは Public である。

- これらのURLは**認証不要**である。URLを知っていれば誰でも購読できる
- 何を監視しているか（検索クエリ）がそのまま読める
- **ローテーションできない。** アラートを削除して作り直す以外に無効化する手段がなく、git 履歴には残り続ける

深刻度は中。アカウントへのアクセス権にはならない。

### ただし、個別対処では解かない

この件は「URLを1つ隠す」問題ではなく、**設定層と実装層が同じリポジトリに同居している**ことの症状である。本製品の将来像は「ユーザーがテーマを選んでビルドできるニュースアプリ」であり、その**テーマ1つ＝設定バンドル1つ**である。つまり `config/` は実装の付属物ではなく、製品そのものにあたる。

現状 `config/` にあるものは、使いながら収束させた成果である。

| ファイル | 内容 |
|---|---|
| `config/sources.yaml` | 4カテゴリ・約20ソース・`focus` 文・`domestic_ratio`・`region` |
| `config/preferences.yaml` | boost / downrank キーワード、5因子の重み（keyword 0.42, recency 0.22, source 0.18, feedback 0.13, egg_price 0.05） |
| `config/prompts.yaml` | 要約プロンプト2本 |
| `data/feedback.json`, `data/source_recommendations.json` | 学習の蓄積 |

一方、収集・スコアリング・要約・静的サイト生成（`scripts/` 配下）は一般的なパイプラインであり、**公開しても失うものがない**。むしろ公開されていることに価値がある（後述）。

### 分離後の姿

| 層 | 中身 | 公開設定 | 誰のため |
|---|---|---|---|
| **エンジン** | `scripts/`, `tests/`, `public/` のテンプレート | 🌐 Public（本リポジトリ） | 外部の読者。clone して動かせること自体が価値 |
| **テーマパック** | `sources` / `preferences` / `prompts` / 学習データ | 🔒 Private（新規リポジトリ） | 製品。将来の販売対象 |
| **配信物** | ビルド済みHTML | 🌐 Public（GitHub Pages） | オーナーのスマホ |

この構造にした時点で、Google アラートURLの露出は**構造的に起きなくなる**。

---

## 2. 絶対に壊してはいけないもの

**オーナーは毎日このサイトをスマホで読んでいる。** そもそも本リポジトリが Public なのは、GitHub Pages で配信するためであり（無料プランでは Public リポジトリからのみ Pages を配信できる）、公開そのものが目的だったわけではない。

したがって次の2点が設計制約になる。

1. **配信URL `https://anyhoe104-spec.github.io/Personal-Newsroom/` を変えない。** ホーム画面のショートカットが生きたままであること
2. **新しい配信経路の成功を確認してから、古い経路を止める。** 逆順にすると、ニュースが読めない日が発生する

---

## 3. 目標とする構成

```
Personal-Newsroom（本リポジトリ・Public・名前を変えない）
  main
    scripts/            エンジン
    tests/
    themes/example/     サンプルテーマパック（誰でも動かせる最小構成）
    docs/
    LICENSE             MIT（コードのみ）
  gh-pages
    ビルド済みサイト。GitHub Pages はこのブランチを配信する

newsroom-themes（新規・Private）
  themes/<name>/sources.yaml, preferences.yaml, prompts.yaml
  state/                feedback.json などの学習データ
  .github/workflows/daily.yml   実行主体。本リポジトリを checkout して走る
  Secrets: ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_ALERT_FEEDS
```

**実行主体を Private 側に置くことが要点である。** 鍵も設定も Private リポジトリの外へ出ない。Public 側のワークフローは、サンプルテーマパックでのテスト実行のみを担う。

### なぜ2リポジトリで足りるか

GitHub Pages は無料プランでは Public リポジトリからしか配信できないため、配信物の置き場は Public でなければならない。本リポジトリの `gh-pages` ブランチを使えば新規リポジトリを増やさずに済み、かつ**配信URLが変わらない**。

---

## 4. 実装手順

**この順序を守ること。**

### Step 1：エンジンを設定非依存にする（Public 側・このリポジトリ）

- `scripts/` が読む設定のパスを環境変数で差し替え可能にする（例：`NEWSROOM_CONFIG_DIR`、既定値は `config/`）
- 学習データの読み書き先も同様に外出しする（例：`NEWSROOM_STATE_DIR`、既定値は `data/`）
- Google アラートのURLを設定ファイルに直書きせず、環境変数から注入できる経路を用意する。`sources.yaml` 側は参照名だけを持つ形にする（例：`url_env: "GOOGLE_ALERT_SWEETS"`、または `GOOGLE_ALERT_FEEDS` に名前とURLの対応をまとめて渡す）
- **`source_type: "google_alert"` の分岐は既に存在する**ので、その読み込み部分だけを差し替えればよい
- 既存の回帰テストが通ること。設定注入の分岐にテストを追加すること

この時点ではまだ挙動は変わらない（既定値が現状と同じであるため）。

### Step 2：サンプルテーマパックを作る（Public 側）

- `themes/example/` に、公開してよいソースだけで構成した最小のテーマパックを置く
- Google アラートは含めない。公開RSS（NHK、ITmedia、Zenn など）のみで成立させる
- README に「clone してこれを動かす手順」を書く。**外部の読者にとってはここが入口になる**
- 注意：サンプルを作り込みすぎると本製品を食う。動くことの証明に留める

### Step 3：`gh-pages` への配信に切り替える（Public 側）

- 現行の `daily_news.yml` は Pages へ直接デプロイしている。これをビルド成果物の `gh-pages` ブランチへの push に変更する
- **この時点ではまだ Pages の配信元を切り替えない。** `gh-pages` に正しい内容が入ることだけを確認する

### Step 4：Private リポジトリを作る

- `newsroom-themes` を Private で作成
- 現行の `config/` の内容を `themes/personal/` として移す
- `.github/workflows/daily.yml` を置く。本リポジトリを checkout し、`NEWSROOM_CONFIG_DIR` を自分の `themes/personal/` に向けて実行し、成果物を Public 側の `gh-pages` へ push する
- Secrets を登録する（**オーナーの手作業**）

### Step 5：切り替え（順序が重要）

1. Private 側のワークフローを手動実行し、`gh-pages` が更新されることを確認する
2. Pages の配信元を `gh-pages` ブランチへ変更する（**オーナーの手作業・1クリック**）
3. スマホで `https://anyhoe104-spec.github.io/Personal-Newsroom/` を開き、**当日のニュースが表示されることを確認する**
4. 確認できてから、Public 側の `daily_news.yml` のスケジュール実行を止める（サンプルでのテスト実行だけ残す）

### Step 6：Public 側から実運用設定を除去する

- `config/` の実運用ファイルを削除する（`themes/example/` は残す）
- **git 履歴からは消えない。** 履歴の書き換えは行わないこと（Public リポジトリで既にクローンされ得ているため意味が薄く、リスクだけが残る）
- 露出済みの Google アラートURLは Step 7 で無効化する

### Step 7：Google アラートの作り直し（**オーナーの手作業。自動化不可**）

**Google アラートには公開APIが存在しない。** 非公式のスクレイパーはあるが、5本のために導入する価値はない。

1. https://www.google.com/alerts で現行の5本を削除する（削除により旧フィードURLは無効になる）
2. 同じ条件で作り直し、新しいフィードURLを取得する
3. **新URLをチャットやIssueに貼らないこと。** `newsroom-themes` の Secrets 画面へ直接入力する

対象の5本（`config/sources.yaml` 内の `source_type: "google_alert"` の項目）：

| カテゴリ | 名前 |
|---|---|
| food | Google Alert: スイーツ 新商品 |
| food | Google Alert: 外食 トレンド |
| ai_dev | Google Alert: 生成AI 開発 |
| egg | Google Alert: 卵 加工品 |
| egg | Google Alert: 食品業界 ニュース |

---

## 5. 完了条件

- [ ] スマホで当日のニュースが表示される（配信URLは従来どおり）
- [ ] Public 側に実運用の Google アラートURLが存在しない（`grep -r "alerts/feeds" .` が `themes/example/` を含めて0件）
- [ ] Public 側を clone した第三者が `themes/example/` で動かせる
- [ ] 回帰テストが全件通る
- [ ] `newsroom-themes` のワークフローが日次で成功している

---

## 6. やってはいけないこと

- **本リポジトリを Private にしない。** 外部の読者に見せる対象はエンジンであり、Public であることに価値がある
- **リポジトリ名を変えない。** 配信URLが変わり、ホーム画面のショートカットが切れる
- **git 履歴を書き換えない。** 既に公開済みであり、効果に対してリスクが見合わない
- **サンプルテーマパックを作り込みすぎない。** 将来の製品と競合する

---

## 7. 関連する未解決事項

- 露出していた Google アラートURLは、Step 7 を実施するまで有効なままである
- テーマパックをどう販売するか（単体／サブスク／エンジン同梱）は未決
- 本リポジトリには現在 LICENSE ファイルがない。エンジンを公開資産として位置づけるなら MIT の追加を検討する
