# PodPing - Simple Podcast Notifications

Send and receive podcast update notifications via the Hive blockchain. No blockchain knowledge required!

Based on the [podping-hivewatcher](https://github.com/Podcastindex-org/podping-hivewatcher) and [podping-hivewriter](https://github.com/Podcastindex-org/podping-hivewatcher) libraries

## Quick Start

### Watching for Updates

```python
import asyncio
from pypodping import PodpingWatcher

async def main():
    watcher = PodpingWatcher()

    @watcher.on_update
    async def handle_update(podping_data):
        print(f"Update from {podping_data.account} at {podping_data.timestamp}")
        for url in podping_data.urls:
            print(f"  {url}")

    await watcher.start()

asyncio.run(main())
```

### Sending Updates

```python
import asyncio
from pypodping import PodpingWriter

async def main():
    writer = PodpingWriter(
        account="your-account",
        posting_key="your-posting-key"
    )

    # Check if you have enough credits
    credits = await writer.get_credits()
    print(f"Credits: {credits}%")

    # Post notification
    result = await writer.post("https://example.com/feed.xml")
    print(f"Posted! Transaction ID: {result['tx_id']}")

asyncio.run(main())
```

### Getting Hive Credentials

1. Create a free Hive account at https://signup.hive.io
2. Your posting key can be found in your wallet settings
3. Never share your posting key publicly!

## API Reference

### PodpingData Object

The `PodpingData` object passed to callbacks contains:

```python
podping_data.urls          # List[str] - Feed URLs that were updated
podping_data.timestamp     # datetime - When posted
podping_data.account       # str - Hive account that posted
podping_data.medium        # str - Content type (podcast, music, etc.)
podping_data.reason        # str - Why posted (update, live, liveEnd)
podping_data.trx_id        # str - Blockchain transaction ID
podping_data.block_num     # int - Blockchain block number
podping_data.version       # str - PodPing protocol version

# Can iterate directly over URLs:
for url in podping_data:
    print(url)

# Get number of URLs:
len(podping_data)
```

### PodpingWatcher

**`PodpingWatcher(nodes=None)`**

Watch for podcast update notifications on the Hive blockchain.

- `nodes`: List of Hive API endpoints (optional, uses 9 reliable default nodes)

**`@watcher.on_update`**

Decorator for the callback function that receives PodpingData objects.

**`await watcher.start()`**

Start watching for updates. Runs until stopped.

**`watcher.stop()`**

Stop watching.

### PodpingWriter

**`PodpingWriter(account, posting_key, nodes=None, dry_run=False)`**

Send podcast update notifications.

- `account`: Hive account name (required)
- `posting_key`: Hive posting key (required)
- `nodes`: List of Hive API endpoints (optional, uses defaults)
- `dry_run`: If True, don't actually send (for testing)

**`await writer.post(urls, reason="update", medium="podcast")`**

Post notification for updated podcast(s).

- `urls`: Single URL string or list of URLs
- `reason`: "update", "live", or "liveEnd"
- `medium`: "podcast", "music", "video", "film", "audiobook", "newsletter", "blog"

Returns dict with `tx_id` and `block_num`.

**`await writer.get_credits()`**

Get remaining Resource Credits as percentage (0-100).

## Error Handling

The library provides specific error types for better debugging:

```python
from pypodping import PodpingError, PodpingConnectionError, PodpingValidationError

try:
    await writer.post("invalid-url")
except PodpingValidationError as e:
    print(f"Invalid URL: {e}")
except PodpingConnectionError as e:
    print(f"Network issue: {e}")
except PodpingError as e:
    print(f"General error: {e}")
```

**Error Types:**
- `PodpingError` - Base exception for all PodPing operations
- `PodpingConnectionError` - Error connecting to Hive nodes
- `PodpingAuthenticationError` - Error with Hive account authentication
- `PodpingValidationError` - Error validating input data (URLs, etc.)
- `PodpingNetworkError` - Network-related error during operations

## Hive Node Configuration

The library uses 9 reliable Hive nodes by default for maximum reliability:

- `https://api.hive.blog`
- `https://hived.emre.sh`
- `https://api.deathwing.me`
- `https://rpc.ausbit.dev`
- `https://rpc.ecency.com`
- `https://hive-api.arcange.eu`
- `https://api.openhive.network`
- `https://techcoderx.com`
- `https://rpc.mahdiyari.info`

You can override these by passing a custom `nodes` list to `PodpingWatcher` or `PodpingWriter`.

## License

MIT
