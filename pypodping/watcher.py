"""PodPing watcher for monitoring podcast update notifications."""

import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Callable, List, Optional

from .client import HiveClient
from .errors import PodpingError
from .types import PodpingData

logger = logging.getLogger(__name__)


class PodpingWatcher:
    """
    Watch for podcast update notifications on the Hive blockchain.

    Simple usage:
        watcher = PodpingWatcher()

        @watcher.on_update
        async def handle_update(update):
            for url in update.urls:
                print(f"Updated: {url}")

        await watcher.start()
    """

    def __init__(self, nodes: Optional[List[str]] = None) -> None:
        """
        Create a new PodPing watcher.

        Args:
            nodes: List of Hive API nodes (uses defaults if not provided)
        """
        self.nodes = nodes
        self.running = False
        self.total_updates = 0
        self._callback: Optional[Callable] = None
        self._operation_regex = re.compile(r"^pp_(.*)_(.*)|podping$")

    def on_update(self, callback: Callable) -> Callable:
        """
        Decorator to set the callback for podcast updates.

        Callback receives a PodpingData object with URLs and metadata.

        Example:
            @watcher.on_update
            async def handle(podping_data):
                print(f"{podping_data.account} posted at {podping_data.timestamp}")
                for url in podping_data.urls:
                    print(f"  {url}")
        """
        self._callback = callback
        return callback

    async def start(self) -> None:
        """Start watching for podcast updates. Runs until stopped."""
        if self.running:
            raise PodpingError("Watcher is already running")

        self.running = True

        async with HiveClient(self.nodes) as client:
            try:
                # Determine starting block
                props = await client.get_dynamic_global_properties()
                current_block = props["head_block_number"]

                while self.running:
                    props = await client.get_dynamic_global_properties()
                    head_block = props["head_block_number"]

                    # Process all available blocks
                    while current_block <= head_block and self.running:
                        updates = await self._process_block(client, current_block)
                        self.total_updates += updates
                        current_block += 1

                    await asyncio.sleep(3)

            finally:
                self.running = False

    def stop(self) -> None:
        """Stop the watcher."""
        self.running = False

    async def _process_block(self, client: HiveClient, block_num: int) -> int:
        """Process a block and return number of updates found."""
        try:
            block = await client.get_block(block_num)
            if not block:
                return 0

            updates = 0
            timestamp = datetime.fromisoformat(block["timestamp"].replace("Z", "+00:00"))
            tx_ids = block.get("transaction_ids", [])

            for tx_idx, tx in enumerate(block.get("transactions", [])):
                for op_type, op_data in tx.get("operations", []):
                    if op_type != "custom_json":
                        continue

                    if not self._operation_regex.match(op_data.get("id", "")):
                        continue

                    try:
                        data = json.loads(op_data.get("json", "{}"))

                        # Handle both iris (v1.1) and urls (v1.0)
                        urls = data.get("iris") or data.get("urls") or []
                        if isinstance(urls, str):
                            urls = [urls]

                        if not urls:
                            continue

                        podping_data = PodpingData(
                            urls=urls,
                            timestamp=timestamp,
                            account=op_data.get("required_posting_auths", [None])[0],
                            medium=data.get("medium"),
                            reason=data.get("reason"),
                            trx_id=tx_ids[tx_idx] if tx_idx < len(tx_ids) else None,
                            block_num=block_num,
                            version=data.get("version", "1.0"),
                        )

                        if self._callback:
                            if asyncio.iscoroutinefunction(self._callback):
                                await self._callback(podping_data)
                            else:
                                self._callback(podping_data)

                            updates += len(urls)
                    except Exception as e:
                        logger.debug(f"Failed to parse update: {e}")

            return updates
        except Exception as e:
            logger.debug(f"Failed to process block {block_num}: {e}")
            return 0