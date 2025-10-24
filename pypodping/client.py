"""Hive blockchain client for PodPing operations."""

import asyncio
import json
import logging
from typing import List, Optional

import aiohttp
from lighthive.client import Client
from lighthive.datastructures import Operation
from lighthive.helpers.account import Account

from .errors import PodpingConnectionError, PodpingNetworkError

logger = logging.getLogger(__name__)

# Default Hive nodes
HIVE_NODES = [
    "https://api.hive.blog",
    "https://hived.emre.sh",
    "https://api.deathwing.me",
    "https://rpc.ausbit.dev",
    "https://rpc.ecency.com",
    "https://hive-api.arcange.eu",
    "https://api.openhive.network",
    "https://techcoderx.com",
    "https://rpc.mahdiyari.info",
]


class HiveClient:
    """Client for interacting with the Hive blockchain."""

    def __init__(self, nodes: Optional[List[str]] = None):
        """
        Initialize Hive client.

        Args:
            nodes: List of Hive API nodes (uses defaults if not provided)
        """
        self.nodes = nodes or HIVE_NODES.copy()
        self._session: Optional[aiohttp.ClientSession] = None
        self._current_node = 0

    async def __aenter__(self):
        """Async context manager entry."""
        timeout = aiohttp.ClientTimeout(total=30.0, connect=10.0)
        self._session = aiohttp.ClientSession(timeout=timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._session:
            await self._session.close()

    async def rpc_call(self, method: str, params: list = None) -> dict:
        """
        Make RPC call with automatic node failover.

        Args:
            method: RPC method name
            params: RPC parameters

        Returns:
            RPC response result

        Raises:
            PodpingConnectionError: If all nodes fail
        """
        if not self._session:
            raise PodpingConnectionError("Client not initialized. Use async context manager.")

        request = {"jsonrpc": "2.0", "method": method, "params": params or [], "id": 1}

        for _ in range(len(self.nodes)):
            node = self.nodes[self._current_node]
            try:
                async with self._session.post(node, json=request) as resp:
                    data = await resp.json()
                    if "error" in data:
                        raise PodpingNetworkError(data["error"].get("message"))
                    return data["result"]
            except Exception as e:
                logger.debug(f"Node {node} failed: {e}")
                self._current_node = (self._current_node + 1) % len(self.nodes)
                await asyncio.sleep(0.1)

        raise PodpingConnectionError("All Hive nodes failed")

    async def get_dynamic_global_properties(self) -> dict:
        """Get dynamic global properties."""
        return await self.rpc_call("condenser_api.get_dynamic_global_properties")

    async def get_block(self, block_num: int) -> dict:
        """Get block by number."""
        return await self.rpc_call("condenser_api.get_block", [block_num])


class HiveWriter:
    """Client for writing to the Hive blockchain."""

    def __init__(
        self,
        account: str,
        posting_key: str,
        nodes: Optional[List[str]] = None,
    ):
        """
        Initialize Hive writer.

        Args:
            account: Hive account name
            posting_key: Hive posting key
            nodes: List of Hive API nodes (uses defaults if not provided)
        """
        self.account = account
        self.posting_key = posting_key
        self.nodes = nodes or HIVE_NODES.copy()
        self._client = Client(
            keys=[posting_key],
            nodes=self.nodes,
            connect_timeout=10.0,
            read_timeout=30.0,
        )

    async def broadcast_operation(self, operation: Operation) -> dict:
        """
        Broadcast operation to blockchain.

        Args:
            operation: Operation to broadcast

        Returns:
            Broadcast response
        """
        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, self._client.broadcast_sync, [operation])
            return response
        except Exception as e:
            raise PodpingNetworkError(f"Failed to broadcast operation: {e}") from e

    async def get_account_rc(self) -> float:
        """
        Get account Resource Credits percentage.

        Returns:
            RC percentage (0.0 to 100.0)
        """
        try:
            loop = asyncio.get_running_loop()
            account = await loop.run_in_executor(None, Account, self._client, self.account)
            rc_percent = await loop.run_in_executor(None, account.rc)
            return rc_percent if rc_percent is not None else 0.0
        except Exception as e:
            logger.debug(f"Failed to get RC: {e}")
            return 0.0
