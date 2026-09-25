# 移行完了までの指示書

- 宛先：アプリ公開を前提とした改修を進めているエージェント
- 記録：2026-09-25
- 決定：オーナー（2026-09-25）
- 前提の整理：[repository-topology.md](repository-topology.md)。手順の背景は [config-separation-plan.md](config-separation-plan.md)

---

## 0. 先に結論

1. **Gate 1 → 2 → 3 → 4 をこの順で完了させる。** 順序を崩すとオーナーがニュースを読めない日が出る
2. **Gate 3 が終わるまで、公開側の `config/` と `data/` に依存する新機能を追加しない**
3. 完了したゲートは、この文書のチェックボックスを更新して記録する
4. アプリ改修の本番反映は Gate 3 の完了後に進める（§6 の制約は今から適用される）

## 1. オーナーの決定（2026-09-25）

分離の目的を「何を隠すか」で確定させた。

| | 対象 | 決定 |
|---|---|---|
| ① | 関心キーワード・監視テーマ文・重み・プロンプト | 🔒 **隠す** |
| ② | GoogleアラートのRSS URL | 🔒 **隠す** |
| ③ | 記事の評価・学習データ | 🔒 **隠す** |
| ④ | 配信サイト（毎日の40記事） | 🌐 **公開のまま** |

④の理由はオーナーの判断である。**「実際にこんな記事が並んでいる」ことがアプリ化したときのイメージとして必要**であり、公開されていることに価値がある。したがって④を隠す作業は行わない。有料プランへの移行も不要。

公開設定（Personal-Newsroom = Public / newsroom-themes = Private）は**変更しない**。分離はリポジトリの公開設定を入れ替える作業ではなく、**中身を移す**作業である。

## 2. 対象の実体

| | 実体 |
|---|---|
| ① | `config/sources.yaml`（媒体名・`focus` 文・`domestic_ratio`・`region`）、`config/preferences.yaml`（boost/downrank キーワード・5因子の重み）、`config/prompts.yaml` |
| ② | `sources.yaml` の `url_env` が指す5本。実URLは公開側リポジトリの `GOOGLE_ALERT_FEEDS` Secret にあり、**git 履歴には旧URLが残る** |
| ③ | `data/feedback.json`、`data/source_recommendations.json`、`data/run_history.json`、`data/articles.json`、および `state/learned.yaml` |
| ④ | `gh-pages` ブランチと `https://anyhoe104-spec.github.io/Personal-Newsroom/` |

## 3. 現状（2026-09-25 実測）

| 項目 | 実測値 |
|---|---|
| 日次の実行主体 | **公開側 Personal-Newsroom**（`gh-pages` 最新 `398021e` の Publish 元が公開側 main `01f0b68`） |
| 本番の配信経路 | **`actions/deploy-pages`**（`daily_news.yml` の `deploy` ジョブ）。`gh-pages` は並走している**未使用**の経路 |
| 非公開側 | `themes/personal/*.yaml` は公開側 `config/` と**バイト単位で同一**。`preview.yml` は `workflow_dispatch` のみで配送ステップなし。日次実行は**していない** |
| ①の公開状況 | 🌐 公開中（`config/` が公開側に存在） |
| ②の公開状況 | 実URLは0件（`url_env` 参照のみ）。ただし履歴に残存 |
| ③の公開状況 | `data/feedback.json` と `source_recommendations.json` は**中身が空**。実際の評価は端末の localStorage |

つまり隠す作業が実際に必要なのは**①と、将来蓄積し始める③**である。②はファイル上は済んでおり、残りは Gate 4（履歴の無効化）。

---

## 4. ゲート

### Gate 1：非公開側の日次実行を成立させる

**現在地（2026-09-25 実測）：未着手。** `newsroom-themes` の PR #2 は open で未マージ、同リポジトリの Actions 実行回数は **0件**（preview を含め一度も走っていない）、`gh-pages` の最新コミット `398021e`（2026-09-24）の Publish 元は公開側 main `01f0b68`。`daily.yml` が main に無い間は `workflow_dispatch` の選択肢にも現れないため、マージが最初の一手になる。

- [ ] `newsroom-themes` の PR #2（`daily.yml`）をマージする
- [ ] **オーナー作業**：`newsroom-themes` の Actions secrets に登録する
  - `PAGES_PUSH_TOKEN`：fine-grained PAT。対象は `anyhoe104-spec/Personal-Newsroom` のみ、権限は **Contents: Read and write のみ**
  - `ANTHROPIC_API_KEY`、`GOOGLE_ALERT_FEEDS`（5キーのJSON）、任意で `OPENAI_API_KEY`
- [ ] `Private newsroom daily` を **`publish=false`** で手動実行し、成果物を確認する
- [ ] `publish=true` で手動実行し、`gh-pages` が更新されることを確認する

**配送元の判別方法**：`publish_gh_pages.sh` はコミットメッセージに `GITHUB_SHA` を書く。非公開側で走ると、そこに入るのは **`newsroom-themes` の SHA** である。`gh-pages` 最新コミットの SHA が公開リポジトリに存在しなければ、非公開側が配送元になっている。

```
git fetch --force origin gh-pages:refs/remotes/origin/gh-pages
git log -1 --format='%s' origin/gh-pages          # → Publish site <SHA>
git cat-file -e <SHA>^{commit}                    # 公開側に無ければ exit 1 = 非公開側由来
```

**停止条件**：`gh-pages` が更新されない、または記事が0件・fallback が出る場合は Gate 2 へ進まない。この時点では本番表示は変わらないので、安全に何度でもやり直せる。

### Gate 2：配信元を切り替え、公開側の日次実行を止める

- [ ] **オーナー作業**：Settings → Pages の配信元を **`gh-pages` ブランチ**へ変更する（1クリック）
- [ ] スマホで `https://anyhoe104-spec.github.io/Personal-Newsroom/` を開き、**当日のニュースが表示されることを確認する**
- [ ] 確認できてから、`daily_news.yml` から `schedule` と `push` トリガを外す（`workflow_dispatch` は残す）
- [ ] 同じ変更で `Publish site to gh-pages` / `Configure Pages` / `Upload artifact` ステップと `deploy` ジョブを削除する（配送は非公開側に一本化される）

**停止条件**：スマホで当日のニュースが出ない場合、Pages の配信元を元に戻す。公開側のワークフローはまだ生きているので復旧できる。**この確認を飛ばしてはいけない。**

### Gate 3：公開側から①③を除去する（ここが「隠す」の本体）

- [ ] 削除する（7ファイル）

```
config/sources.yaml  config/preferences.yaml  config/prompts.yaml
data/articles.json  data/feedback.json  data/run_history.json  data/source_recommendations.json
```

- [ ] 生成物も削除する。**`public/index.html` には①のキーワードが埋め込まれている**（`新規事業` `価格戦略` `卵加工` の存在を確認済み）。`public/index.html`、`public/run_history.json`、`public/source_recommendations.json` はビルド成果物であり、配信は `gh-pages` から行われるので main に置く必要がない
- [ ] `.gitignore` に `config/` `data/` `public/index.html` `public/run_history.json` `public/source_recommendations.json` を追加する（ローカル実行の再コミット防止）
- [ ] `daily_news.yml`（手動のサンプル検証用に残る分）を `themes/example` へ向ける

```yaml
env:
  NEWSROOM_CONFIG_DIR: ${{ github.workspace }}/themes/example
  NEWSROOM_STATE_DIR: ${{ runner.temp }}/newsroom-state
```

- [ ] 回帰テストを直す。**削除後に失敗するのは2件だけである（実測）**

| テスト | 原因 | 対応 |
|---|---|---|
| `SourcesConfigTests.test_every_google_alert_names_an_injection_lookup` | `ROOT / "config" / "sources.yaml"` を直接読む（`tests/test_regressions.py:600` 付近） | 本番パックがこのリポジトリに無くなるため、ファイル不在時は `skipTest` にする |
| `TranslationRegressionTests.test_japanese_display_article_gets_localized_fields` | `config_path("preferences.yaml")` を経由して読む | `themes/example` を指すようにする。`NEWSROOM_CONFIG_DIR=themes/example` を与えると解消することを実測で確認 |

実測の内訳：`config/` と `data/` を削除した複製で `python -m unittest discover -s tests` を実行 → 65件中 **errors=2**。`NEWSROOM_CONFIG_DIR=themes/example` を与えると **errors=1**（残るのは上の表の1件目）。

- [ ] `grep -r "alerts/feeds" .` が `themes/example/` を含めて0件であることを確認する
- [ ] ①のキーワードが追跡ファイルに残っていないことを確認する

```
git grep -n -E '新規事業|価格戦略|卵加工|domestic_ratio' -- . ':!docs' ':!WORKLOG.md'
```

**git 履歴からは消えない。履歴の書き換えは行わないこと。** 公開リポジトリで既にクローンされ得ており、効果に対してリスクが見合わない。

### Gate 4：②を無効化する（オーナーのみ・自動化不可）

- [ ] **オーナー作業**：https://www.google.com/alerts で現行5本を削除し、同条件で作り直す
- [ ] **オーナー作業**：新URLを `newsroom-themes` の `GOOGLE_ALERT_FEEDS` へ直接入力する

**新URLをチャット・Issue・リポジトリファイルに貼らないこと。** Googleアラートに公開APIはなく、この作業は代行できない。手順は [alert-rotation.md](alert-rotation.md)。ここまで完了して初めて、履歴に残る旧URLが無害になる。

---

## 5. ④を公開のまま保つことの副作用（①が完全には隠れない）

**実測した事実**：公開中のページに `vocabulary` が埋め込まれており、**boost_keywords が読める**。

| 語 | 公開ページ内 |
|---|---|
| `新規事業` `価格戦略` `卵加工`（boost） | **1件ずつ存在** |
| `為替` `株価`（downrank） | 0件 |

`focus` 文・重み・プロンプト・downrank キーワードは埋め込まれていない。漏れるのは boost_keywords だけである。

用途は飾りではない。`public/app.js:33,96` と `public/learning.js:62,85,109` が、投票後の端末内再ランキングとキーワード抽出に使っている。

**Gate 3 を完了しても、これは④を通じて公開されたままになる。** ①を完全に隠すなら、次のどれかを選ぶ判断が必要である。

| 案 | 内容 | 代償 |
|---|---|---|
| A | 許容する | 一般的な業種語彙であり、`focus` 文ほど個人の意図を表さない。追加作業なし |
| B | **推奨**：その日の記事本文に実際に出現する語だけを出力する | 当日の40記事の再ランキングは不変。保存・履歴の古い記事のランキングが僅かに鈍る |
| C | ランキングをサーバ側へ移す | オフライン動作と即時反映を失う。PWAの利点を削る |

B の実装箇所は `scripts/build_site.py` の `reader_vocabulary()`（59〜69行）。記事集合を引数に取り、`word in 記事テキスト` で絞ってから返す形にすればよい。

**この判断と実装はアプリ改修側に委ねる。** 同じ3ファイル（`build_site.py` / `app.js` / `learning.js`）を改修中のため、ここで先に変更すると衝突するだけになる。**①が完全に隠れたと言えるのは、Gate 3 の完了とこの対応の両方が揃ってからである。**

## 6. アプリ改修側への制約（今から適用）

1. **設定と状態は必ず `config_path()` / `state_path()` 経由で読む。** `ROOT / "config"` や `ROOT / "data"` を直接書かない
   - 実例：`scripts/build_site.py` に `ROOT / "config/preferences.yaml"` の直書きが混入し、外部テーマパックを無視して公開側の設定を読んでいた。`config/` を削除すると `FileNotFoundError` になる状態だった（PR #18 で修正済み）
   - 検出は `tests/test_regressions.py` の `test_every_pipeline_script_reads_through_the_config_layer` が行う。**上記の実例を見逃したため、本PRで検出パターンを厳しくした**（`ROOT / "config"` の完全一致から、`ROOT / "config` の前方一致へ）
2. **生成ページに設定由来の値を新たに埋め込むときは、④として公開されることを前提に判断する。** §5がその実例である
3. **`config/` `data/` に依存する新機能を追加しない。** Gate 3 で消える
4. 学習状態は `state_path()` の下に置く。編集用の設定ファイル（`preferences.yaml`）へ機械が書き戻すと、オーナーが書いたコメントが消える

## 7. やってはいけないこと

- **Gate 2 の実機確認を飛ばして Gate 3 に進む。** ニュースが読めない日が発生する
- **Personal-Newsroom を Private にする。** 無料プランでは Pages が配信できず、配信が止まる
- **`newsroom-themes` を Public にする。** ①を隠す先がなくなる
- **リポジトリ名を変える。** 配信URLが変わり、ホーム画面のショートカットが切れる
- **git 履歴を書き換える**
- **新しいアラートURLをチャット・Issue・リポジトリファイルに貼る**
- **テストを緩めて通す。** Gate 3 の2件は原因が特定されている

## 8. 完了条件

- [ ] スマホで当日のニュースが表示される（配信URLは従来どおり）
- [ ] `gh-pages` の配送元が `newsroom-themes` である
- [ ] 公開側に `config/` の実運用ファイルと `data/` の学習ファイルが存在しない
- [ ] `grep -r "alerts/feeds" .` が0件
- [ ] 回帰テストが全件通る
- [ ] `newsroom-themes` の日次ワークフローが連日成功している
- [ ] 旧Googleアラート5本が無効化され、新URLがSecretに入っている
- [ ] §5 の判断が記録され、選んだ案が実装されている
