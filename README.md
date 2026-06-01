# TikTok 広告 日次パイプライン

TikTok Ads API から前日の広告実績を取得し、Google スプレッドシートへ自動転記する日次バッチです。  
毎朝 06:00 JST (UTC 21:00 前日) に GitHub Actions が自動実行します。

## 構成

```
.github/workflows/daily.yml   # スケジュール実行
  config/accounts.yaml          # 広告アカウント定義
  src/schema.py                 # 共通データスキーマ（Phase2 GA4対応）
  src/sources/tiktok.py         # TikTok Marketing API 取得
  src/sink/sheets.py            # Google Sheets upsert
  src/notify.py                 # Slack 通知
  src/main.py                   # エントリポイント
```

## 初期セットアップ

### 1. GitHub Secrets の登録

**Settings > Secrets and variables > Actions** に登録してください。

| Secret 名 | 内容 |
|---|---|
| `TIKTOK_APP_ID` | TikTok for Business アプリ ID |
| `TIKTOK_APP_SECRET` | TikTok for Business アプリシークレット |
| `TIKTOK_TOKEN_SHOSEI` | 翔星建設アクセストークン |
| `TIKTOK_TOKEN_ESCO` | エスコプロモーションアクセストークン |
| `GOOGLE_SA_JSON` | Google サービスアカウント JSON 全文 |
| `SLACK_WEBHOOK_URL` | Slack Incoming Webhook URL |

### 2. スプレッドシート ID の設定

`config/accounts.yaml` の `sheet_id` に各アカウントのスプレッドシート ID を記入してください。  
`https://docs.google.com/spreadsheets/d/<ID>/edit` の `<ID>` 部分です。

### 3. サービスアカウントの共有

各スプレッドシートをサービスアカウントのメールアドレスに **編集者** として共有してください。

## 手動実行

Actions > tiktok-daily > **Run workflow** から実行できます。

## アカウント追加手順

1. `config/accounts.yaml` にエントリ追加
2. GitHub Secrets にトークン追加
3. `.github/workflows/daily.yml` の `env` ブロックに 1 行追加

再デプロイ不要。

## Phase 2 予定

- **GA4 連携**: `src/sources/ga4.py` を追加し `source="ga4"` の Row を同一スキーマで出力。同じ `raw_tiktok` タブ構造で追記。
