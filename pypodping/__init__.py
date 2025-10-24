"""
PodPing - Simple Python Library for Podcast Notifications

Monitor and send podcast update notifications via the Hive blockchain.
No Hive knowledge required!

Example Usage:

    # Watch for podcast updates
    >>> import asyncio
    >>> from pypodping import PodpingWatcher
    >>>
    >>> async def main():
    ...     watcher = PodpingWatcher()
    ...
    ...     @watcher.on_update
    ...     async def handle_update(urls):
    ...         print(f"Podcast updated: {urls}")
    ...
    ...     await watcher.start()

    # Send podcast update notifications
    >>> from pypodping import PodpingWriter
    >>>
    >>> writer = PodpingWriter()  # Uses PODPING_HIVE_ACCOUNT and PODPING_HIVE_POSTING_KEY env vars
    >>> await writer.post("https://example.com/feed.xml")
    >>>
    >>> # Check if you have enough credits to send
    >>> credits = await writer.get_credits()
    >>> print(f"Credits remaining: {credits}%")
"""

from .watcher import PodpingWatcher
from .writer import PodpingWriter
from .errors import PodpingError
from .types import PodpingData

__version__ = "1.0.0"
__all__ = ["PodpingWatcher", "PodpingWriter", "PodpingError", "PodpingData"]