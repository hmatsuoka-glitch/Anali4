import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.sources.tiktok import normalize
from src import schema

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "tiktok_sample_response.json")
ADVERTISER = {"advertiser_id": "7613640650042425345", "name": "翔星建設"}


@pytest.fixture
def sample_rows():
    with open(FIXTURE_PATH) as f:
        return json.load(f)["data"]["list"]


def test_normalize_ad_level_basic_fields(sample_rows):
    result = normalize(sample_rows, "ad", ADVERTISER)
    assert len(result) == 2
    r = result[0]
    assert r.source == "tiktok"
    assert r.level == "ad"
    assert r.advertiser_id == "7613640650042425345"
    assert r.spend == 100.50
    assert r.impressions == 10000.0
    assert r.clicks == 500.0


def test_normalize_date_extraction(sample_rows):
    result = normalize(sample_rows, "ad", ADVERTISER)
    assert result[0].date == "2024-01-15"
    assert result[1].date == "2024-01-15"


def test_normalize_video_metrics(sample_rows):
    result = normalize(sample_rows, "ad", ADVERTISER)
    r = result[0]
    assert r.video_plays == 9000.0
    assert r.video_p25 == 75.0
    assert r.avg_watch_time == 8.5


def test_normalize_placement_breakdown():
    rows = [{
        "dimensions": {"ad_id": "111", "stat_time_day": "2024-01-15 00:00:00", "placement": "TikTok"},
        "metrics": {"spend": "50", "impressions": "5000", "clicks": "100"},
    }]
    result = normalize(rows, "placement", ADVERTISER)
    assert result[0].breakdown_key == "placement"
    assert result[0].breakdown_value == "TikTok"


def test_normalize_age_gender_breakdown():
    rows = [{
        "dimensions": {"ad_id": "111", "stat_time_day": "2024-01-15 00:00:00", "age": "18-24", "gender": "MALE"},
        "metrics": {"spend": "30"},
    }]
    result = normalize(rows, "age_gender", ADVERTISER)
    assert result[0].breakdown_key == "age_gender"
    assert result[0].breakdown_value == "18-24_MALE"


def test_normalize_region_breakdown():
    rows = [{
        "dimensions": {"ad_id": "111", "stat_time_day": "2024-01-15 00:00:00", "province_id": "JP-13"},
        "metrics": {"spend": "30"},
    }]
    result = normalize(rows, "region", ADVERTISER)
    assert result[0].breakdown_key == "region"
    assert result[0].breakdown_value == "JP-13"


def test_normalize_missing_metric_is_none(sample_rows):
    rows = [{
        "dimensions": {"ad_id": "111", "stat_time_day": "2024-01-15 00:00:00"},
        "metrics": {"spend": "10"},
    }]
    result = normalize(rows, "ad", ADVERTISER)
    r = result[0]
    assert r.ctr is None
    assert r.reach is None
    assert r.video_p25 is None


def test_normalize_dash_metric_is_none(sample_rows):
    # second fixture row has "-" for reach, frequency, video metrics
    result = normalize(sample_rows, "ad", ADVERTISER)
    r = result[1]
    assert r.reach is None
    assert r.frequency is None
    assert r.video_2s_rate is None
    assert r.video_p25 is None


def test_normalize_conversion_fallback_to_result(sample_rows):
    # second row has conversion="-" but result="8"
    result = normalize(sample_rows, "ad", ADVERTISER)
    assert result[1].conversions == 8.0


def test_normalize_key_uniqueness(sample_rows):
    result = normalize(sample_rows, "ad", ADVERTISER)
    keys = [r.key() for r in result]
    assert len(keys) == len(set(keys))
