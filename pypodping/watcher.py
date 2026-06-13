"""PodPing watcher for monitoring podcast update notifications."""

import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Callable, List, Optional

from .client import HiveClient
from .errors import PodpingConnectionError, PodpingError, PodpingNetworkError
from .types import PodpingData

logger = logging.getLogger(__name__)

_RETRYABLE_ERRORS = (PodpingConnectionError, PodpingNetworkError)
_OP_REGEX = re.compile(r"^pp_(.*)_(.*)|podping$")


class PodpingWatcher:
    """Watch for podcast update notifications on the Hive blockchain."""

    def __init__(self, nodes: Optional[List[str]] = None) -> None:
        self.nodes = nodes
        self.running = False
        self.total_updates = 0
        self.current_block = None
        self._callback: Optional[Callable] = None

    def on_update(self, callback: Callable) -> Callable:
        """Decorator to register a callback that receives :class:`PodpingData`."""
        self._callback = callback
        return callback

    async def start(self) -> None:
        """Start watching for podcast updates. Runs until stopped."""
        if self.running:
            raise PodpingError("Watcher is already running")

        self.running = True

        async with HiveClient(self.nodes) as client:
            try:
                while self.running:
                    await self._process_blocks(client)
                    await asyncio.sleep(3)
            finally:
                self.running = False

    def stop(self) -> None:
        """Stop the watcher."""
        self.running = False

    async def _process_blocks(self, client: HiveClient) -> None:
        head_block = await self._head_block(client)
        if head_block is None:
            return

        self.current_block = self.current_block or head_block

        while self.current_block <= head_block and self.running:
            block = await self._get_block(client, self.current_block)
            if block is None:
                return

            updates = await self._process_block(block, self.current_block)
            self.total_updates += updates
            self.current_block += 1

    async def _head_block(self, client: HiveClient) -> Optional[int]:
        try:
            props = await client.get_dynamic_global_properties()
            return props["head_block_number"]
        except _RETRYABLE_ERRORS as e:
            logger.warning("Failed to get head block: %s", e)
            return None

    async def _get_block(self, client: HiveClient, block_num: int) -> Optional[dict]:
        try:
            return await client.get_block(block_num)
        except _RETRYABLE_ERRORS as e:
            logger.warning("Failed to get block %s: %s", block_num, e)
            return None

    async def _process_block(self, block: dict, block_num: int) -> int:
        """Process a block and return number of updates found."""
        try:
            updates = 0
            timestamp = datetime.fromisoformat(block["timestamp"].replace("Z", "+00:00"))
            tx_ids = block.get("transaction_ids", [])

            for tx_idx, tx in enumerate(block.get("transactions", [])):
                for op_type, op_data in tx.get("operations", []):
                    if op_type != "custom_json":
                        continue

                    if not _OP_REGEX.match(op_data.get("id", "")):
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