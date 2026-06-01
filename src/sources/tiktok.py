from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from typing import Any, Optional

import requests
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from src import schema

logger = logging.getLogger(__name__)

_BASE_URL = "https://business-api.tiktok.com/open_api/v1.3/report/integrated/get/"
_PAGE_SIZE = 1000

_METRICS = [
    "spend", "impressions", "clicks", "ctr", "cpc", "cpm", "reach", "frequency",
    "landing_page_view", "conversion", "result",
    "video_play_actions", "video_watched_2s",
    "video_views_p25", "video_views_p50", "video_views_p75", "video_views_p100",
    "average_video_play",
]

_REPORT_CONFIGS = [
    {
        "report_type": "BASIC",
        "data_level": "AUCTION_AD",
        "dimensions": ["ad_id", "stat_time_day"],
        "level": "ad",
    },
    {
        "report_type": "AUDIENCE",
        "data_level": "AUCTION_AD",
        "dimensions": ["ad_id", "stat_time_day", "placement"],
        "level": "placement",
    },
    {
        "report_type": "AUDIENCE",
        "data_level": "AUCTION_AD",
        "dimensions": ["ad_id", "stat_time_day", "province_id"],
        "level": "region",
    },
    {
        "report_type": "AUDIENCE",
        "data_level": "AUCTION_AD",
        "dimensions": ["ad_id", "stat_time_day", "age", "gender"],
        "level": "age_gender",
    },
]


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, requests.HTTPError):
        status = exc.response.status_code if exc.response is not None else 0
        return status == 429 or status >= 500
    return False


@retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _get(url: str, params: dict, headers: dict) -> dict:
    resp = requests.get(url, params=params, headers=headers, timeout=30)
    resp.raise_for_status()
    body = resp.json()
    code = body.get("code", 0)
    if code != 0:
        raise requests.HTTPError(
            f"TikTok API error code={code} message={body.get('message')}",
            response=resp,
        )
    return body


def fetch_report(
    advertiser_id: str,
    token: str,
    report_type: str,
    data_level: str,
    dimensions: list,
    metrics: list,
    start: str,
    end: str,
) -> list[dict]:
    headers = {"Access-Token": token}
    all_rows: list[dict] = []
    page = 1

    while True:
        params = {
            "advertiser_id": advertiser_id,
            "report_type": report_type,
            "data_level": data_level,
            "dimensions": json.dumps(dimensions),
            "metrics": json.dumps(metrics),
            "start_date": start,
            "end_date": end,
            "page": page,
            "page_size": _PAGE_SIZE,
        }
        body = _get(_BASE_URL, params, headers)
        data = body.get("data", {})
        rows = data.get("list", [])
        all_rows.extend(rows)

        page_info = data.get("page_info", {})
        total_pages = page_info.get("total_page", 1)
        logger.debug(
            "advertiser=%s level=%s page=%d/%d rows_so_far=%d",
            advertiser_id, data_level, page, total_pages, len(all_rows),
        )
        if page >= total_pages:
            break
        page += 1

    return all_rows


def _opt_float(val: Any) -> Optional[float]:
    if val is None or val == "-" or val == "":
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _req_float(val: Any) -> float:
    result = _opt_float(val)
    return result if result is not None else 0.0


def normalize(rows: list[dict], level: str, advertiser: dict) -> list[schema.Row]:
    advertiser_id = str(advertiser["advertiser_id"])
    advertiser_name = str(advertiser.get("name", advertiser.get("advertiser_name", "")))
    result_rows: list[schema.Row] = []

    for raw in rows:
        dims: dict = raw.get("dimensions", {})
        mets: dict = raw.get("metrics", {})

        stat_day = dims.get("stat_time_day", "")
        row_date = stat_day[:10] if stat_day else ""
        ad_id = str(dims.get("ad_id", ""))
        ad_name = str(mets.get("ad_name", ""))

        breakdown_key = ""
        breakdown_value = ""
        if level == "placement":
            breakdown_key = "placement"
            breakdown_value = str(dims.get("placement", ""))
        elif level == "region":
            breakdown_key = "region"
            breakdown_value = str(dims.get("province_id", dims.get("dma_id", "")))
        elif level == "age_gender":
            age = str(dims.get("age", ""))
            gender = str(dims.get("gender", ""))
            breakdown_key = "age_gender"
            breakdown_value = f"{age}_{gender}"

        conv_raw = mets.get("conversion")
        if conv_raw is None or conv_raw == "-" or conv_raw == "":
            conv_raw = mets.get("result")
        conversions = _req_float(conv_raw)

        row = schema.Row(
            date=row_date,
            source="tiktok",
            advertiser_id=advertiser_id,
            advertiser_name=advertiser_name,
            level=level,
            ad_id=ad_id,
            ad_name=ad_name,
            breakdown_key=breakdown_key,
            breakdown_value=breakdown_value,
            spend=_req_float(mets.get("spend")),
            impressions=_req_float(mets.get("impressions")),
            clicks=_req_float(mets.get("clicks")),
            lp_views=_req_float(mets.get("landing_page_view")),
            video_plays=_req_float(mets.get("video_play_actions")),
            conversions=conversions,
            ctr=_opt_float(mets.get("ctr")),
            cpc=_opt_float(mets.get("cpc")),
            cpm=_opt_float(mets.get("cpm")),
            reach=_opt_float(mets.get("reach")),
            frequency=_opt_float(mets.get("frequency")),
            video_2s_rate=_opt_float(mets.get("video_watched_2s")),
            video_p25=_opt_float(mets.get("video_views_p25")),
            video_p50=_opt_float(mets.get("video_views_p50")),
            video_p75=_opt_float(mets.get("video_views_p75")),
            video_p100=_opt_float(mets.get("video_views_p100")),
            avg_watch_time=_opt_float(mets.get("average_video_play")),
        )
        result_rows.append(row)

    return result_rows


def collect_account(advertiser: dict, token: str) -> list[schema.Row]:
    today = date.today()
    start = (today - timedelta(days=3)).strftime("%Y-%m-%d")
    end = (today - timedelta(days=1)).strftime("%Y-%m-%d")

    advertiser_id = str(advertiser["advertiser_id"])
    all_rows: list[schema.Row] = []

    for cfg in _REPORT_CONFIGS:
        level = cfg["level"]
        try:
            raw_rows = fetch_report(
                advertiser_id=advertiser_id,
                token=token,
                report_type=cfg["report_type"],
                data_level=cfg["data_level"],
                dimensions=cfg["dimensions"],
                metrics=_METRICS,
                start=start,
                end=end,
            )
            normalized = normalize(raw_rows, level=level, advertiser=advertiser)
            all_rows.extend(normalized)
            logger.info("advertiser=%s level=%s rows=%d", advertiser_id, level, len(normalized))
        except Exception as exc:
            logger.warning("advertiser=%s level=%s 未取得: %s", advertiser_id, level, exc)

    return all_rows
