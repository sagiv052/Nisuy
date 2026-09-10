"""Bounded in-memory cache for Telegram media chunks."""

from __future__ import annotations

import asyncio
import time
from collections import OrderedDict
from typing import Awaitable, Callable, Optional


class ChunkMemoryCache:
    def __init__(self, max_bytes: int, ttl_seconds: float) -> None:
        self.max_bytes = max(1, max_bytes)
        self.ttl_seconds = max(1.0, ttl_seconds)
        self._items: OrderedDict[tuple[int, int, int], tuple[float, bytes]] = OrderedDict()
        self._inflight: dict[tuple[int, int, int], asyncio.Future[bytes]] = {}
        self._bytes = 0
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._loads = 0

    async def _get(self, key: tuple[int, int, int]) -> Optional[bytes]:
        now = time.monotonic()
        async with self._lock:
            item = self._items.get(key)
            if item is None:
                self._misses += 1
                return None
            expires_at, data = item
            if expires_at <= now:
                self._bytes -= len(data)
                del self._items[key]
                self._misses += 1
                return None
            self._hits += 1
            self._items.move_to_end(key)
            self._items[key] = (now + self.ttl_seconds, data)
            return data

    async def _put(self, key: tuple[int, int, int], data: bytes) -> None:
        if not data or len(data) > self.max_bytes:
            return
        async with self._lock:
            old = self._items.pop(key, None)
            if old:
                self._bytes -= len(old[1])
            self._items[key] = (time.monotonic() + self.ttl_seconds, data)
            self._bytes += len(data)
            while self._bytes > self.max_bytes and self._items:
                _, (_, removed) = self._items.popitem(last=False)
                self._bytes -= len(removed)
                self._evictions += 1

    async def get_or_load(
        self,
        key: tuple[int, int, int],
        loader: Callable[[], Awaitable[bytes]],
    ) -> bytes:
        cached = await self._get(key)
        if cached is not None:
            return cached
        owner = False
        async with self._lock:
            future = self._inflight.get(key)
            if future is None:
                future = asyncio.get_running_loop().create_future()
                self._inflight[key] = future
                owner = True
        if not owner:
            return await future
        try:
            async with self._lock:
                self._loads += 1
            data = await loader()
            await self._put(key, data)
            if not future.done():
                future.set_result(data)
            return data
        except BaseException as error:
            if not future.done():
                future.set_exception(error)
            raise
        finally:
            async with self._lock:
                self._inflight.pop(key, None)

    async def stats(self) -> dict[str, int]:
        async with self._lock:
            return {
                "items": len(self._items),
                "bytes": self._bytes,
                "max_bytes": self.max_bytes,
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "loads": self._loads,
                "inflight": len(self._inflight),
            }

    async def clear(self) -> None:
        async with self._lock:
            self._items.clear()
            self._bytes = 0
