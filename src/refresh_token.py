"""
TikTok アクセストークン更新ユーティリティ

使い方:
  python -m src.refresh_token

環境変数:
  TIKTOK_APP_ID      アプリID
  TIKTOK_APP_SECRET  アプリシークレット
  TIKTOK_REFRESH_TOKEN_SHOSEI   翔星建設のリフレッシュトークン
  TIKTOK_REFRESH_TOKEN_ESCO     エスコのリフレッシュトークン

取得した新アクセストークンを標準出力に表示する。
GitHub Actions Secrets の更新は手動で行う。
"""
import os
import sys
import requests

REFRESH_URL = "https://business-api.tiktok.com/open_api/v1.3/oauth2/refresh_token/"


def refresh(app_id: str, app_secret: str, refresh_token: str) -> dict:
    resp = requests.post(REFRESH_URL, json={
        "app_id": app_id,
        "secret": app_secret,
        "refresh_token": refresh_token,
    }, timeout=30)
    resp.raise_for_status()
    body = resp.json()
    if body.get("code") != 0:
        raise ValueError(f"Refresh failed: {body}")
    return body["data"]


def main():
    app_id = os.environ.get("TIKTOK_APP_ID")
    app_secret = os.environ.get("TIKTOK_APP_SECRET")
    if not app_id or not app_secret:
        print("ERROR: TIKTOK_APP_ID / TIKTOK_APP_SECRET が未設定", file=sys.stderr)
        sys.exit(1)

    targets = [
        ("翔星建設",           "TIKTOK_REFRESH_TOKEN_SHOSEI", "TIKTOK_TOKEN_SHOSEI"),
        ("エスコプロモーション", "TIKTOK_REFRESH_TOKEN_ESCO",   "TIKTOK_TOKEN_ESCO"),
    ]

    for name, refresh_env, token_env in targets:
        rt = os.environ.get(refresh_env)
        if not rt:
            print(f"[SKIP] {name}: {refresh_env} 未設定")
            continue
        try:
            data = refresh(app_id, app_secret, rt)
            print(f"\n[{name}]")
            print(f"  新アクセストークン ({token_env}): {data['access_token']}")
            print(f"  有効期限: {data.get('access_token_expire_in', '?')} 秒")
            print(f"  新リフレッシュトークン ({refresh_env}): {data.get('refresh_token', '変更なし')}")
        except Exception as e:
            print(f"[ERROR] {name}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
