# 公開前の運用確認（2026-09-09）

## 確認できたこと

- 最終アプリ版 `8a35a7b` の [Reader checks](https://github.com/anyhoe104-spec/Personal-Newsroom/actions/runs/34300223430) は全工程成功。Python33件・Node7件・Playwright操作テストを含む。
- 現行main `f58ecb2` の [日次運用](https://github.com/anyhoe104-spec/Personal-Newsroom/actions/runs/34288778211) はbuild/deployともに成功。
- 日次ログでは4カテゴリとも10件。AI・活用と卵の20件中18件が日本語表示可能、近似重複は全カテゴリ0件。
- 履歴キャッシュが復元され、`history_runs=4` を確認。履歴が毎回1へ戻る問題は現行mainで解消されている。
- 上記の日次運用は新UI統合前のmainの結果。新UIの本番Pages検証を代替するものではない。

## 今回の修正

Food Navigatorの旧URL `https://www.foodnavigator.com/Info/Latest-News/RSS` は本番で404。
[公式サイト](https://www.foodnavigator.com/)のフッター「RSS feed」が指す `https://www.foodnavigator.com/arc/outboundfeeds/rss/` を確認し、HTTP 200・XML解析で20記事を取得した。`config/sources.yaml` をこの配信先へ更新。媒体名・カテゴリ・地域・重みは変更しない。

Food Business Newsは `https://www.foodbusinessnews.net/rss` というHTML案内ページを登録していて0件だった。[公式RSS案内](https://www.foodbusinessnews.net/rss)の「FBN Best News」が指す `https://www.foodbusinessnews.net/rss/2` へ更新し、HTTP 200・30記事を確認した。

実RSSの検証で経済カテゴリの10件すべてが1媒体になっていたため、経済にも同一媒体6件の目安を追加した。他媒体が不足する場合は従来どおり制限を緩め、10件を確保する。

## 新アプリ版の実RSS検証

検証用コピーで取得・スコア・生成・validator・ソース分析をすべて終了コード0で完了した。スコア前は283記事、表示は各カテゴリ10件・合計40件。全40件が実記事で、カテゴリ横断重複・カテゴリ内近似重複は0件。APIキーがないため日本語表示可能なのは対象20件中11件で、残りはフォールバック表示になる。

この全工程実行はURL修正前の設定で行った。その後、修正先の2フィードを個別にHTTP取得・XML解析で確認した。経済カテゴリの媒体制限は回帰テストで、複数媒体時の6/4配分と単一媒体しかない場合の10件確保を確認。Python回帰テストは34件成功。

## 継続確認する項目

| 対象 | 観測結果 | 次の対応 |
| --- | --- | --- |
| HBR | 本番で404、今回の代替候補は502 | 有効な公式RSSが確認できてから変更する |
| Reddit r/artificial | 本番・ローカルで429 | 次の日次実行で回復を確認。制限の回避は行わない |
| 農林水産省 | 本番で403 | 配信側の状況を確認してからURL変更を判断 |
| 翻訳 | 本番で20件中18件が表示可能 | 残り2件はフォールバック表示。今回の手元環境にはAPIキーなし |
| 本番公開 | PR #15〜#18とRSS修正PRは未統合 | 所有者のマージ指示後、mainの生成・Pagesを確認 |

## 公開操作の順序

PR #15 → #16 → #17 → #18 → RSS修正PRを順に統合する。後続PRのbaseが前段ブランチなので、各段のmain取り込みを確認してから次へ進む。最終版がmainに入った後、Daily Personal Newsroomを実行し、最新記事・新UI・評価保持・サービスワーカー更新を確認する。Android/iOS実機とストア審査は別途必要。
