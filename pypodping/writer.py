"""PodPing writer for sending podcast update notifications."""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Union

import rfc3987
from lighthive.datastructures import Operation

from .client import HiveWriter
from .errors import PodpingError, PodpingValidationError

logger = logging.getLogger(__name__)


class PodpingWriter:
    """
    Send podcast update notifications to the Hive blockchain.

    Simple usage:
        writer = PodpingWriter(account="your-account", posting_key="your-key")
        await writer.post("https://example.com/feed.xml")

        # Check remaining credits
        credits = await writer.get_credits()
        print(f"Credits: {credits}%")
    """

    def __init__(
        self,
        account: str,
        posting_key: str,
        nodes: Optional[List[str]] = None,
        dry_run: bool = False,
    ):
        """
        Create a new PodPing writer.

        Args:
            account: Hive account name (required)
            posting_key: Hive posting key (required)
            nodes: List of Hive API nodes (uses defaults if not provided)
            dry_run: If True, don't actually send to blockchain (for testing)
        """
        self.account = account
        self.posting_key = posting_key
        self.nodes = nodes
        self.dry_run = dry_run
        self.session_id = uuid.uuid4().int & ((1 << 64) - 1)

        self._hive_writer = HiveWriter(
            account=self.account,
            posting_key=self.posting_key,
            nodes=self.nodes,
        )

    async def post(
        self,
        urls: Union[str, List[str]],
        reason: str = "update",
        medium: str = "podcast",
    ) -> dict:
        """
        Post podcast update notification(s).

        Args:
            urls: Single URL or list of URLs that were updated
            reason: Why the notification is being sent. Options:
                   - "update" (default): Regular content update
                   - "live": Podcast going live
                   - "liveEnd": Live podcast ending
            medium: Type of content. Options:
                   - "podcast" (default): Audio podcast
                   - "music": Music content
                   - "video": Video content
                   - "film": Film content
                   - "audiobook": Audiobook content
                   - "newsletter": Newsletter content
                   - "blog": Blog content

        Returns:
            dict with transaction details: {"tx_id": "...", "block_num": 12345}

        Example:
            # Single URL
            result = await writer.post("https://example.com/feed.xml")

            # Multiple URLs
            result = await writer.post([
                "https://example.com/feed1.xml",
                "https://example.com/feed2.xml",
            ])

            # Going live
            result = await writer.post("https://example.com/feed.xml", reason="live")
        """
        # Validate and normalize URLs
        url_list = [urls] if isinstance(urls, str) else urls
        for url in url_list:
            if not rfc3987.match(url, "IRI"):
                raise PodpingValidationError(f"Invalid URL: {url}")

        if self.dry_run:
            logger.info(f"DRY RUN - Would post notification for {len(url_list)} URLs")
            return {"tx_id": "dry_run", "block_num": 0}

        # Build notification payload
        payload = {
            "version": "1.1",
            "medium": medium,
            "reason": reason,
            "iris": url_list,
            "timestampNs": int(datetime.now(timezone.utc).timestamp() * 1e9),
            "sessionId": self.session_id,
        }

        json_str = json.dumps(payload, separators=(",", ":"))
        if len(json_str.encode("utf-8")) > 8192:
            raise PodpingValidationError("Too many URLs (payload exceeds 8KB limit)")

        # Create blockchain operation
        operation = Operation(
            "custom_json",
            {
                "required_auths": [],
                "required_posting_auths": [self.account],
                "id": f"pp_{medium}_{reason}",
                "json": json_str,
            },
        )

        # Send to blockchain
        try:
            response = await self._hive_writer.broadcast_operation(operation)
            logger.info(f"Posted notification for {len(url_list)} URLs: {response['id']}")
            return {
                "tx_id": response["id"],
                "block_num": response["block_num"],
            }
        except Exception as e:
            raise PodpingError(f"Failed to post notification: {e}") from e

    async def get_credits(self) -> float:
        """
        Get remaining Resource Credits (RC) as a percentage.

        Resource Credits are consumed when posting notifications and regenerate over time.
        You need credits to post notifications.

        Returns:
            Percentage from 0.0 to 100.0

        Example:
            credits = await writer.get_credits()
            if credits < 10:
                print("Warning: Running low on credits!")
        """
        return await self._hive_writer.get_account_rc()
