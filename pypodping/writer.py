"""PodPing writer for sending podcast update notifications."""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Union

import rfc3987
from lighthive.datastructures import Operation

from .client import HiveWriter
from .errors import PodpingError, PodpingValidationError

logger = logging.getLogger(__name__)


class PodpingWriter:
    """Send podcast update notifications to the Hive blockchain."""

    def __init__(
        self,
        account: str,
        posting_key: str,
        nodes: Optional[List[str]] = None,
        dry_run: bool = False,
    ):
        self.account = account
        self.dry_run = dry_run
        self.session_id = uuid.uuid4().int & ((1 << 64) - 1)
        self._hive_writer = HiveWriter(
            account=account, posting_key=posting_key, nodes=nodes
        )

    async def post(
        self,
        urls: Union[str, List[str]],
        reason: str = "update",
        medium: str = "podcast",
    ) -> dict:
        """Post update notification for one or more feed URLs.

        Returns ``{"tx_id": "...", "block_num": 12345}``.
        """
        url_list = [urls] if isinstance(urls, str) else list(urls)
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
        """Return remaining Resource Credits as a percentage (0.0–100.0)."""
        return await self._hive_writer.get_account_rc()
