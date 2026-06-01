from dataclasses import dataclass, asdict
from typing import Optional

COLUMNS = [
    "date", "source", "advertiser_id", "advertiser_name", "level",
    "ad_id", "ad_name", "breakdown_key", "breakdown_value",
    "spend", "impressions", "clicks", "ctr", "cpc", "cpm",
    "reach", "frequency", "lp_views", "conversions", "video_plays",
    "video_2s_rate", "video_p25", "video_p50", "video_p75", "video_p100",
    "avg_watch_time",
]


@dataclass
class Row:
    date: str
    source: str
    advertiser_id: str
    advertiser_name: str
    level: str
    ad_id: str = ""
    ad_name: str = ""
    breakdown_key: str = ""
    breakdown_value: str = ""
    spend: float = 0.0
    impressions: float = 0.0
    clicks: float = 0.0
    ctr: Optional[float] = None
    cpc: Optional[float] = None
    cpm: Optional[float] = None
    reach: Optional[float] = None
    frequency: Optional[float] = None
    lp_views: float = 0.0
    conversions: float = 0.0
    video_plays: float = 0.0
    video_2s_rate: Optional[float] = None
    video_p25: Optional[float] = None
    video_p50: Optional[float] = None
    video_p75: Optional[float] = None
    video_p100: Optional[float] = None
    avg_watch_time: Optional[float] = None

    def key(self) -> str:
        return f"{self.date}|{self.source}|{self.advertiser_id}|{self.level}|{self.ad_id}|{self.breakdown_value}"

    def to_list(self):
        d = asdict(self)
        return [d[c] for c in COLUMNS]
