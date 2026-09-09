# Personal Newsroom — リリースガイド

## 使い方

1. 「今日のニュース」で記事を読み、「役に立った」「関心が薄い」を選ぶ。同じボタンで取り消せる。
2. 「あなたの関心」で学習タグ・情報源の見直し候補・活用提案を確認。優先して追うタグも追加・削除できる。
3. 「あとで読む」は記事が日次一覧から消えても要約とリンクを保持する。「評価の履歴」から過去の評価を変更できる。
4. 設定で表示テーマ・簡易表示・学習反映を調整。機種変更やブラウザデータ削除前にバックアップを保存する。
5. ブラウザの「ホーム画面に追加」でアプリとして起動。最初のオンライン訪問後はオフラインでも画面を開ける。原文記事は通信が必要。

## 学習の範囲

- 評価は端末内に保存し、日次で配信された記事に毎回適用。カテゴリ間の好みは混ぜない。
- キーワードと情報源の評価からおすすめ順を±18点以内で補正する。元の編集スコア・新しい順・学習停止も利用可能。
- 学習したRSSタグはアプリ内の推薦用。RSSサーバーや購読URLは自動変更しない。
- 情報源の見直しは3件以上の評価が集まってから提案する。活用提案は複数の肯定評価があるタグからルールベースで作る。
- 個人評価の自動アップロード・自動同期はない。バックアップを別端末に取り込める。最新評価を優先して統合する。
- 保存容量を超えた場合は成功扱いにしない。破損データはバックアップとして書き出し可能で、復元またはリセットまで保護する。
- 任意のパイプライン用書き出しは設定の詳細メニューを使う。バックアップ全体と `feedback.json` は形式が異なる。

## 検証

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
node --test tests/learning.test.cjs
python scripts/build_site.py
python scripts/validate_newsroom.py
npm install --no-save --package-lock=false playwright@1.62.1
npx playwright install chromium
node tests/browser-smoke.cjs
```

2026-09-09: Python33件・Node7件成功。ブラウザでは320/390/768/1280px、評価・取消・再読込、保存・履歴、検索、タグ、テーマ、学習停止、バックアップ統合、不正JSON、破損保存、オフライン再読込を確認。ページエラーなし。`validate_newsroom.py` は成功、既存スナップショットの翻訳不足とカテゴリ間重複は警告が残る。

## 公開までの残作業

- PR #15 → #16 → #17 → 最終リリースPR の依存順でレビュー・マージ（所有者判断）。各PRの差分は前段をベースにしている。
- mainへのマージ後、Reader checks と Daily Personal Newsroom の成功、Pagesで最新記事と新版UIが配信されたことを確認する。
- Android実機でホーム画面追加→評価→終了→再起動、機内モードで保存記事表示、別端末へのバックアップ移行を確認する。
- iOS Safariの実機操作、ストア審査・署名・ストア掲載は未実施。今回はGitHub Pages上のPWAであり、ストア審査済みを意味しない。

PWAアイコンは192/512pxを同梱。[MDNのインストール要件](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable)に沿ってマニフェストを構成した。
