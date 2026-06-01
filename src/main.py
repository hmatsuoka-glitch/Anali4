import json
import logging
import os
import sys
from datetime import date

import yaml

from src.sources import tiktok
from src.sink import sheets
from src import notify

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def load_accounts(path: str = "config/accounts.yaml") -> list:
    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config.get("accounts", [])


def main() -> None:
    dry_run = os.environ.get("DRY_RUN", "").strip() == "1"
    if dry_run:
        logger.info("DRY_RUN mode enabled — sheets.upsert will be skipped")

    accounts = load_accounts()
    logger.info("Loaded %d account(s) from config", len(accounts))

    successes: list = []
    failures: list = []
    total_rows_written = 0

    for account in accounts:
        name: str = account["name"]
        token_env: str = account["token_env"]
        sheet_id: str = account["sheet_id"]

        token = os.environ.get(token_env)
        if not token:
            reason = f"環境変数 {token_env} が未設定"
            logger.error("Account %s: %s", name, reason)
            failures.append((name, reason))
            continue

        try:
            rows = tiktok.collect_account(account, token)
            logger.info("Account %s: collected %d row(s)", name, len(rows))
            if dry_run:
                logger.info("DRY_RUN: skip upsert (%d rows)", len(rows))
                preview = [r.to_list() for r in rows[:3]]
                print(json.dumps(preview, ensure_ascii=False, indent=2))
                written = 0
            else:
                written = sheets.upsert(sheet_id, rows)
                logger.info("Account %s: wrote %d row(s) to sheet", name, written)
            successes.append(name)
            total_rows_written += written
        except Exception as exc:
            reason = str(exc)
            logger.exception("Account %s failed: %s", name, reason)
            # Token expiry detection
            reason_lower = reason.lower()
            if "token" in reason_lower or "40001" in reason or "40002" in reason:
                notify.notify_slack(
                    f"⚠️ TikTok token 期限切れの可能性 / アカウント: {name} / 要トークン更新"
                )
            failures.append((name, reason))

    today = date.today().strftime("%Y-%m-%d")

    if successes:
        notify.notify_slack(
            f"✅ TikTok pipeline 完了 / 取得アカウント数: {len(successes)} / "
            f"追記行: {total_rows_written} / 日付: {today}"
        )

    for name, reason in failures:
        notify.notify_slack(
            f"🔴 TikTok pipeline 失敗 / アカウント: {name} / 原因: {reason}"
        )

    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
