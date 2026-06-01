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
            written = sheets.upsert(sheet_id, rows)
            logger.info("Account %s: wrote %d row(s) to sheet", name, written)
            successes.append(name)
            total_rows_written += written
        except Exception as exc:
            reason = str(exc)
            logger.exception("Account %s failed: %s", name, reason)
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
