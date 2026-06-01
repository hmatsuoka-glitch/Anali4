import os
import json
import urllib.request


def notify_slack(text: str):
    url = os.environ.get("SLACK_WEBHOOK_URL")
    if not url:
        return
    data = json.dumps({"text": text}).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    urllib.request.urlopen(req, timeout=10)
