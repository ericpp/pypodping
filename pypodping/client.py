"""Hive blockchain client for PodPing operations."""

import asyncio
import logging
from typing import List, Optional

import aiohttp
from lighthive.client import Client
from lighthive.datastructures import Operation
from lighthive.helpers.account import Account

from .errors import PodpingConnectionError, PodpingNetworkError

logger = logging.getLogger(__name__)

HIVE_NODES = [
    "https://api.hive.blog",
    "https://api.openhive.network",
    "https://anyx.io",
    "https://rpc.ausbit.dev",
    "https://rpc.mahdiyari.info",
    "https://api.hive.blue",
    "https://techcoderx.com",
    "https://hive.roelandp.nl",
    "https://hived.emre.sh",
    "https://api.deathwing.me",
    "https://api.c0ff33a.uk",
    "https://hive-api.arcange.eu",
    "https://hive-api.3speak.tv",
    "https://hiveapi.actifit.io",
]
"""Default Hive API nodes used when none are provided."""


class HiveClient:
    """Async JSON-RPC client for reading the Hive blockchain, with automatic node failover."""

    def __init__(self, nodes: Optional[List[str]] = None):
        self.nodes = nodes or HIVE_NODES.copy()
        self._session: Optional[aiohttp.ClientSession] = None
        self._current_node = 0

    async def __aenter__(self):
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30.0, connect=10.0)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()

    async def rpc_call(self, method: str, params: list = None) -> dict:
        """Make an RPC call, rotating through nodes on transient failures."""
        if not self._session:
            raise PodpingConnectionError(
                "Client not initialized. Use 'async with HiveClient() as client:'."
            )

        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or [],
            "id": 1,
        }
        last_error: Optional[Exception] = None

        for _ in range(len(self.nodes)):
            node = self.nodes[self._current_node]
            try:
                async with self._session.post(node, json=request) as resp:
                    data = await resp.json()
                    if "error" in data:
                        raise PodpingNetworkError(
                            data["error"].get("message", "Unknown RPC error")
                        )
                    return data["result"]
            except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as e:
                last_error = e
                logger.debug(f"Node {node} failed: {e}")
                self._current_node = (self._current_node + 1) % len(self.nodes)
                await asyncio.sleep(0.1)

        raise PodpingConnectionError(
            f"All Hive nodes failed. Last error: {last_error}"
        )

    async def get_dynamic_global_properties(self) -> dict:
        return await self.rpc_call("condenser_api.get_dynamic_global_properties")

    async def get_block(self, block_num: int) -> dict:
        return await self.rpc_call("condenser_api.get_block", [block_num])


class HiveWriter:
    """Synchronous lighthive wrapper, run in a thread pool for async callers."""

    def __init__(
        self,
        account: str,
        posting_key: str,
        nodes: Optional[List[str]] = None,
    ):
        self.account = account
        self.nodes = nodes or HIVE_NODES.copy()
        self._client = Client(
            keys=[posting_key],
            nodes=self.nodes,
            connect_timeout=10.0,
            read_timeout=30.0,
        )

    async def broadcast_operation(self, operation: Operation) -> dict:
        try:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                None, self._client.broadcast_sync, [operation]
            )
        except Exception as e:
            raise PodpingNetworkError(f"Failed to broadcast: {e}") from e

    async def get_account_rc(self) -> float:
        """Return account Resource Credits as a percentage (0.0–100.0)."""
        try:
            loop = asyncio.get_running_loop()
            account = await loop.run_in_executor(
                None, Account, self._client, self.account
            )
            rc = await loop.run_in_executor(None, account.rc)
            return rc if rc is not None else 0.0
        except Exception as e:
            logger.debug(f"Failed to get RC: {e}")
            return 0.0
