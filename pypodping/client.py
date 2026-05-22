"""Hive blockchain client for PodPing operations."""

import asyncio
import logging
from typing import List, Optional

import aiohttp
from lighthive.client import Client
from lighthive.datastructures import Operation
from lighthive.exceptions import RPCNodeException
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


def _format_rpc_error(error) -> str:
    """Build a readable message from an RPC error (dict or RPCNodeException)."""
    if isinstance(error, RPCNodeException):
        msg = str(error)
        code = error.code
        raw_data = (error.raw_body or {}).get("error", {}).get("data") if isinstance(error.raw_body, dict) else None
    elif isinstance(error, dict):
        msg = error.get("message", "Unknown RPC error")
        code = error.get("code")
        raw_data = error.get("data")
    else:
        return str(error)

    if code is not None:
        msg = f"{msg} (code {code})"

    if raw_data:
        detail = ": ".join(filter(None, [raw_data.get("name"), raw_data.get("message")])) if isinstance(raw_data, dict) else str(raw_data)
        if detail and detail not in msg:
            msg = f"{msg}: {detail}"

    return msg


class HiveClient:
    """Async Hive JSON-RPC client with automatic node failover."""

    def __init__(self, nodes: Optional[List[str]] = None):
        self.nodes = nodes or HIVE_NODES.copy()
        self._session: Optional[aiohttp.ClientSession] = None
        self._node_idx = 0

    async def __aenter__(self):
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30.0, connect=10.0)
        )
        return self

    async def __aexit__(self, *_):
        if self._session:
            await self._session.close()

    def _next_node(self):
        self._node_idx = (self._node_idx + 1) % len(self.nodes)

    async def rpc_call(self, method: str, params: list = None) -> dict:
        if not self._session:
            raise PodpingConnectionError("Use 'async with HiveClient() as client:'.")

        payload = {"jsonrpc": "2.0", "method": method, "params": params or [], "id": 1}
        last_error = None

        for _ in range(len(self.nodes)):
            node = self.nodes[self._node_idx]
            try:
                async with self._session.post(node, json=payload) as resp:
                    data = await resp.json()
                    if "error" in data:
                        self._next_node()
                        raise PodpingNetworkError(_format_rpc_error(data["error"]))
                    return data["result"]
            except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as e:
                last_error = e
                logger.debug(f"Node {node} failed: {e}")
                self._next_node()
                await asyncio.sleep(0.1)

        raise PodpingConnectionError(f"All nodes failed. Last error: {last_error}")

    async def get_dynamic_global_properties(self) -> dict:
        return await self.rpc_call("condenser_api.get_dynamic_global_properties")

    async def get_block(self, block_num: int) -> dict:
        return await self.rpc_call("condenser_api.get_block", [block_num])


class HiveWriter:
    """Lighthive wrapper that exposes an async interface via a thread pool."""

    def __init__(self, account: str, posting_key: str, nodes: Optional[List[str]] = None):
        self.account = account
        self.nodes = nodes or HIVE_NODES.copy()
        self._client = Client(
            keys=[posting_key],
            nodes=self.nodes,
            connect_timeout=10.0,
            read_timeout=30.0,
            automatic_node_selection=True,
        )

    async def _run(self, fn, *args):
        return await asyncio.get_running_loop().run_in_executor(None, fn, *args)

    async def broadcast_operation(self, operation: Operation) -> dict:
        try:
            return await self._run(self._client.broadcast_sync, [operation])
        except Exception as e:
            raise PodpingNetworkError(f"Failed to broadcast: {_format_rpc_error(e)}") from e

    async def get_account_rc(self) -> float:
        """Return account Resource Credits as a percentage (0–100)."""
        try:
            account = await self._run(Account, self._client, self.account)
            return await self._run(account.rc) or 0.0
        except Exception as e:
            logger.debug(f"Failed to get RC: {e}")
            return 0.0