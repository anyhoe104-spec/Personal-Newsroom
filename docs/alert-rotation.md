# GoogleアラートURLの差し替え

公開コードの5本の実URLを削除し、url_env参照に統一する。
現時点の本番実行元はPersonal-Newsroomなので、まず同リポジトリのActions secretへ登録する。
非公開テーマ側への運用切替は別工程。まだ使われていない側だけにSecretを登録しても本番には反映されない。

1. Googleアラートで現行5本の検索条件・言語・地域・頻度・件数を確認する。
2. 条件を保持して再作成し、配信先RSSの新しいURLを取得する。旧URLの無効化も確認する。
3. Personal-Newsroom → Settings → Secrets and variables → Actions で、GOOGLE_ALERT_FEEDSを登録する。値は下記キーと新URLのJSONオブジェクト。URLはチャット・Issue・リポジトリファイルへ貼らない。
4. PRのCI成功後に統合し、Daily Personal Newsroomを手動実行。5本が未設定としてスキップされていないこと、build/deploy成功、従来のPages URLの表示を確認する。

| JSONキー | 対象 |
| --- | --- |
| GOOGLE_ALERT_SWEETS | スイーツ 新商品 |
| GOOGLE_ALERT_DINING | 外食 トレンド |
| GOOGLE_ALERT_AI_DEV | 生成AI 開発 |
| GOOGLE_ALERT_EGG | 卵 加工品 |
| GOOGLE_ALERT_FOOD_INDUSTRY | 食品業界 ニュース |

```json
{
  "GOOGLE_ALERT_SWEETS": "新しいスイーツ用RSS URL",
  "GOOGLE_ALERT_DINING": "新しい外食用RSS URL",
  "GOOGLE_ALERT_AI_DEV": "新しい生成AI用RSS URL",
  "GOOGLE_ALERT_EGG": "新しい卵加工品用RSS URL",
  "GOOGLE_ALERT_FOOD_INDUSTRY": "新しい食品業界用RSS URL"
}
```

値の日本語部分を対応する新URLへ置き換え、SecretのValueにJSON全体を登録する。

Secretが未登録の場合、その5本は警告付きでスキップされ、一般RSSの収集は継続する。
既存Googleアラートの再発行・Secret登録完了を確認するまで、本番切替完了とはしない。
この変更はGit履歴を消去せず、過去に公開された旧URLを無効化する操作の代わりにはならない。
