import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import requests
from unittest.mock import patch, MagicMock
from tenacity import wait_none

import src.sources.tiktok as tiktok


def _make_response(body: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = body
    if status_code >= 400:
        http_err = requests.HTTPError(response=resp)
        resp.raise_for_status.side_effect = http_err
    else:
        resp.raise_for_status.return_value = None
    return resp


def _success_body(rows: list, total_page: int = 1, page: int = 1) -> dict:
    return {
        "code": 0,
        "message": "OK",
        "data": {
            "list": rows,
            "page_info": {
                "total_page": total_page,
                "page": page,
            },
        },
    }


SAMPLE_ROW = {
    "dimensions": {"ad_id": "123", "stat_time_day": "2024-01-01 00:00:00"},
    "metrics": {"spend": "100", "impressions": "1000", "clicks": "50"},
}


def test_fetch_single_page():
    body = _success_body([SAMPLE_ROW], total_page=1)
    mock_resp = _make_response(body)

    with patch("src.sources.tiktok.requests.get", return_value=mock_resp) as mock_get:
        rows = tiktok.fetch_report(
            advertiser_id="111",
            token="tok",
            report_type="BASIC",
            data_level="AUCTION_AD",
            dimensions=["ad_id", "stat_time_day"],
            metrics=["spend"],
            start="2024-01-01",
            end="2024-01-01",
        )

    assert mock_get.call_count == 1
    assert rows == [SAMPLE_ROW]


def test_fetch_pagination():
    def make_page_resp(page: int) -> MagicMock:
        body = _success_body([SAMPLE_ROW], total_page=3, page=page)
        return _make_response(body)

    side_effects = [make_page_resp(1), make_page_resp(2), make_page_resp(3)]

    with patch("src.sources.tiktok.requests.get", side_effect=side_effects) as mock_get:
        rows = tiktok.fetch_report(
            advertiser_id="111",
            token="tok",
            report_type="BASIC",
            data_level="AUCTION_AD",
            dimensions=["ad_id", "stat_time_day"],
            metrics=["spend"],
            start="2024-01-01",
            end="2024-01-03",
        )

    assert mock_get.call_count == 3
    assert len(rows) == 3  # one row per page


def test_fetch_retries_on_429():
    # Patch wait to avoid real sleeps
    tiktok._get.retry.wait = wait_none()

    err_resp = _make_response({}, status_code=429)
    ok_body = _success_body([SAMPLE_ROW], total_page=1)
    ok_resp = _make_response(ok_body)

    with patch("src.sources.tiktok.requests.get", side_effect=[err_resp, ok_resp]) as mock_get:
        rows = tiktok.fetch_report(
            advertiser_id="111",
            token="tok",
            report_type="BASIC",
            data_level="AUCTION_AD",
            dimensions=["ad_id", "stat_time_day"],
            metrics=["spend"],
            start="2024-01-01",
            end="2024-01-01",
        )

    assert mock_get.call_count == 2
    assert rows == [SAMPLE_ROW]


def test_fetch_raises_on_tiktok_error():
    body = {
        "code": 40001,
        "message": "invalid token",
        "data": {},
    }
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = body
    resp.raise_for_status.return_value = None

    with patch("src.sources.tiktok.requests.get", return_value=resp):
        with pytest.raises(requests.HTTPError):
            tiktok.fetch_report(
                advertiser_id="111",
                token="tok",
                report_type="BASIC",
                data_level="AUCTION_AD",
                dimensions=["ad_id", "stat_time_day"],
                metrics=["spend"],
                start="2024-01-01",
                end="2024-01-01",
            )


def test_fetch_empty_list():
    body = _success_body([], total_page=1)
    mock_resp = _make_response(body)

    with patch("src.sources.tiktok.requests.get", return_value=mock_resp):
        rows = tiktok.fetch_report(
            advertiser_id="111",
            token="tok",
            report_type="BASIC",
            data_level="AUCTION_AD",
            dimensions=["ad_id", "stat_time_day"],
            metrics=["spend"],
            start="2024-01-01",
            end="2024-01-01",
        )

    assert rows == []
