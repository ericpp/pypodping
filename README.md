# pypodping

Send and receive podcast update notifications via the Hive blockchain. No blockchain knowledge required.

Based on [podping-hivewatcher](https://github.com/Podcastindex-org/podping-hivewatcher) and [podping-hivewriter](https://github.com/Podcastindex-org/podping-hivewriter).

## Install

```bash
pip install pypodping
```

## Watching for Updates

```python
import asyncio
from pypodping import PodpingWatcher

async def main():
    watcher = PodpingWatcher()

    @watcher.on_update
    async def handle(data):
        print(f"{data.account} at {data.timestamp}")
        for url in data.urls:
            print(f"  {url}")

    await watcher.start()

asyncio.run(main())
```

## Sending Updates

```python
import asyncio
from pypodping import PodpingWriter

async def main():
    writer = PodpingWriter(
        account="your-account",
        posting_key="your-posting-key",
    )

    credits = await writer.get_credits()
    print(f"Credits: {credits:.0f}%")

    result = await writer.post("https://example.com/feed.xml")
    print(f"Posted! tx_id={result['tx_id']}")

asyncio.run(main())
```

## Getting Hive Credentials

1. Create a free Hive account at https://signup.hive.io
2. Your posting key can be found in your wallet settings
3. Never share your posting key publicly

## API Reference

### PodpingWatcher

```python
watcher = PodpingWatcher(nodes=None)
```

- `nodes` — list of Hive API endpoints (optional, uses reliable defaults)

| Method | Description |
|---|---|
| `@watcher.on_update` | Decorator for the callback that receives `PodpingData` |
| `await watcher.start()` | Start watching (runs until stopped) |
| `watcher.stop()` | Stop watching |

### PodpingWriter

```python
writer = PodpingWriter(account, posting_key, nodes=None, dry_run=False)
```

- `account` — Hive account name
- `posting_key` — Hive posting key
- `nodes` — list of Hive API endpoints (optional)
- `dry_run` — if `True`, skip the actual broadcast (for testing)

| Method | Description |
|---|---|
| `await writer.post(urls, reason="update", medium="podcast")` | Post update notification. `urls` is a string or list of strings. Returns `{"tx_id": ..., "block_num": ...}`. |
| `await writer.get_credits()` | Resource Credits remaining as a percentage (0–100). |

`reason` values: `"update"`, `"live"`, `"liveEnd"`

`medium` values: `"podcast"`, `"music"`, `"video"`, `"film"`, `"audiobook"`, `"newsletter"`, `"blog"`

### PodpingData

Passed to the watcher callback. Can be iterated directly (`for url in data`).

| Field | Type | Description |
|---|---|---|
| `urls` | `list[str]` | Feed URLs that were updated |
| `timestamp` | `datetime` | When posted |
| `account` | `str` | Hive account that posted |
| `medium` | `str` | Content type |
| `reason` | `str` | Why posted |
| `trx_id` | `str \| None` | Transaction ID |
| `block_num` | `int \| None` | Block number |
| `version` | `str` | Protocol version |

## Error Handling

All errors inherit from `PodpingError`:

```python
from pypodping import PodpingError, PodpingConnectionError, PodpingValidationError

try:
    await writer.post("not-a-url")
except PodpingValidationError as e:
    print(f"Bad input: {e}")
except PodpingConnectionError as e:
    print(f"Network issue: {e}")
except PodpingError as e:
    print(f"Error: {e}")
```

| Exception | When |
|---|---|
| `PodpingError` | Base for all pypodping errors |
| `PodpingConnectionError` | All Hive nodes unreachable |
| `PodpingAuthenticationError` | Bad account credentials |
| `PodpingValidationError` | Invalid URLs or payload too large |
| `PodpingNetworkError` | Broadcast or RPC failure |

## Custom Nodes

Override the default Hive API nodes:

```python
from pypodping import PodpingWatcher, HIVE_NODES

watcher = PodpingWatcher(nodes=["https://api.hive.blog"])
```

## License

MIT
