"""
pypodping - Simple Python library for podcast update notifications via Hive blockchain.

Watch for updates:

    watcher = PodpingWatcher()

    @watcher.on_update
    async def handle(data):
        for url in data.urls:
            print(url)

    await watcher.start()

Send updates:

    writer = PodpingWriter(account="myaccount", posting_key="5K...")
    await writer.post("https://example.com/feed.xml")
"""

from .client import HIVE_NODES
from .errors import (
    PodpingAuthenticationError,
    PodpingConnectionError,
    PodpingError,
    PodpingNetworkError,
    PodpingValidationError,
)
from .types import PodpingData
from .watcher import PodpingWatcher
from .writer import PodpingWriter

__version__ = "1.0.0"
__all__ = [
    "PodpingWatcher",
    "PodpingWriter",
    "PodpingData",
    "PodpingError",
    "PodpingConnectionError",
    "PodpingAuthenticationError",
    "PodpingValidationError",
    "PodpingNetworkError",
    "HIVE_NODES",
]
