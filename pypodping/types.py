"""Data types for the PodPing library."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class PodpingData:
    """
    Podcast update notification data.

    Can be iterated directly: `for url in podping_data: ...`

    Attributes:
        urls: List of feed URLs that were updated
        timestamp: When the update was posted
        account: Hive account that posted the update
        medium: Type of content (podcast, music, video, etc.)
        reason: Why posted (update, live, liveEnd)
        trx_id: Blockchain transaction ID
        block_num: Blockchain block number
        version: PodPing protocol version
    """
    urls: List[str]
    timestamp: datetime
    account: str
    medium: str = "podcast"
    reason: str = "update"
    trx_id: Optional[str] = None
    block_num: Optional[int] = None
    version: str = "1.0"

    def __iter__(self):
        """Allow iterating over URLs directly: for url in update"""
        return iter(self.urls)

    def __len__(self):
        """Return number of URLs"""
        return len(self.urls)