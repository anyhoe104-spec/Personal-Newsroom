# リポジトリ構成と公開設定の方針

- 記録：2026-09-25
- 位置づけ：この文書が公開設定に関する唯一の決定記録である。[config-separation-plan.md](config-separation-plan.md) は手順、この文書は**どちらのリポジトリを公開し、どちらを非公開にするか**を確定させる。

会話の中で「Personal-Newsroom を Private にし、`newsroom-themes` を Public にする」という逆向きの構成が言及されたが、**その方向へ変更した決定記録はリポジトリ内に存在しない。** 反対に、Public のままとする判断は 2026-09-09 に記録されている（`WORKLOG.md` の同日エントリ）。同じ確認が繰り返されているため、実測値とともにここに固定する。

---

## 1. 方針（変更しない）

| リポジトリ | 役割 | 公開設定 | 理由 |
|---|---|---|---|
| `anyhoe104-spec/Personal-Newsroom` | エンジン（`scripts/` / `tests/` / `public/` テンプレート）と、`gh-pages` ブランチによる配信 | 🌐 **Public のまま** | 無料プランでは Public リポジトリからしか GitHub Pages を配信できない。加えて、外部の読者に見せる対象はエンジンであり、公開されていること自体に価値がある |
| `anyhoe104-spec/newsroom-themes` | テーマパック（`sources` / `preferences` / `prompts`）と学習データ、および日次実行の主体 | 🔒 **Private のまま** | 個人の関心設定・学習の蓄積・GoogleアラートURLが入る層であり、分離の目的そのもの |

あわせて、次の2点も変更しない。

- 配信URL `https://anyhoe104-spec.github.io/Personal-Newsroom/`（オーナーのホーム画面ショートカットが生きたままであること）
- リポジトリ名

## 2. 現在の実態（2026-09-25 実測）

| 項目 | 実測値 | 確認方法 |
|---|---|---|
| Personal-Newsroom の公開設定 | public | リポジトリ一覧API |
| `newsroom-themes` の公開設定 | private | 同上 |
| 日次の実行主体 | **Personal-Newsroom**（公開側） | `gh-pages` の最新コミット `398021e`（2026-09-24）の Publish 元が Personal-Newsroom の main `01f0b68` |
| `gh-pages` への配信 | 稼働中・日次で更新 | 2026-09-19〜09-24 の連続コミット |
| `newsroom-themes` の最終 push | 2026-09-15 | リポジトリ一覧API。以降の更新がなく、非公開側の日次実行は動いていない |
| 公開 config 内の実アラートURL | 0件（`url_env` 参照のみ） | `git grep 'alerts/feeds' -- config themes` |
| アラートURLの注入元 | Personal-Newsroom の `GOOGLE_ALERT_FEEDS` Secret | `daily_news.yml` |

つまり、**公開設定は計画どおりの向き（Public エンジン／Private テーマ）で既に正しい。** 未完了なのは公開設定ではなく、実行主体を非公開側へ移す運用移行である。

## 3. 計画との差分

| Step | 状態 |
|---|---|
| Step 1 エンジンの設定非依存化 | 済（`NEWSROOM_CONFIG_DIR` / `NEWSROOM_STATE_DIR` / `url_env`） |
| Step 2 サンプルテーマパック | 済（`themes/example/`） |
| Step 3 `gh-pages` への配信 | 済・稼働中 |
| Step 4 Private リポジトリ | リポジトリ作成と準備PRのマージは済。日次実行は未稼働 |
| Step 5 実行主体の切替 | **未** |
| Step 6 公開側から実運用設定を除去 | **未**（`config/` は公開側に残る。実URLは既に不在） |
| Step 7 Googleアラートの作り直し | **未**（オーナーの手作業。旧URLの無効化も未確認） |

2026-09-18 のオーナー指示により、Step 5 を待たずにアラートURLの差し替えだけを先行させ、現行の公開側 Actions で Secret 注入できるようにしてある。手順は [alert-rotation.md](alert-rotation.md) を参照。**非公開側だけに Secret を登録しても本番には反映されない。**

## 4. 採用しない構成

「Personal-Newsroom を Private にし、`newsroom-themes` を Public にする」構成は採用しない。決定記録がないだけでなく、次の2点が壊れる。

1. **配信が止まる。** 無料プランでは Private リポジトリから GitHub Pages を配信できない。Personal-Newsroom を Private にした時点で、オーナーが毎朝読んでいるサイトが配信されなくなる
2. **分離の目的が反転する。** `newsroom-themes` を Public にすると、個人の関心設定・学習の蓄積・アラートURLが公開される。これは分離によって隠そうとしていた層そのものである

将来この向きへ変更する場合、少なくとも次が前提になる。判断はオーナーが行い、結論はこの文書へ追記する。

- 有料プランで Private リポジトリからの Pages 配信を有効にする、または配信専用の Public リポジトリを別に立てる（**後者は配信URLが変わるため、ホーム画面のショートカットが切れる**）
- `newsroom-themes` から個人設定・学習データ・アラート参照を取り除く（取り除いた後の `newsroom-themes` は `themes/example/` と役割が重複する）

## 5. 参照

- 手順と背景：[config-separation-plan.md](config-separation-plan.md)
- アラートURLの差し替え：[alert-rotation.md](alert-rotation.md)
- 本番確認の記録：[operations-verification.md](operations-verification.md)
- Public のままとする判断の一次記録：`WORKLOG.md` 2026-09-09 エントリ
