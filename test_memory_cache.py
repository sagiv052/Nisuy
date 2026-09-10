import asyncio
import unittest

from memory_cache import ChunkMemoryCache


class MemoryCacheTests(unittest.IsolatedAsyncioTestCase):
    async def test_cache_reuses_loaded_chunk(self):
        cache = ChunkMemoryCache(1024, 120)
        calls = 0

        async def loader():
            nonlocal calls
            calls += 1
            await asyncio.sleep(0.01)
            return b"chunk"

        self.assertEqual(await cache.get_or_load((1, 2, 3), loader), b"chunk")
        self.assertEqual(await cache.get_or_load((1, 2, 3), loader), b"chunk")
        self.assertEqual(calls, 1)
        self.assertEqual((await cache.stats())["hits"], 1)

    async def test_concurrent_requests_are_single_flight(self):
        cache = ChunkMemoryCache(1024, 120)
        calls = 0

        async def loader():
            nonlocal calls
            calls += 1
            await asyncio.sleep(0.02)
            return b"same"

        results = await asyncio.gather(*[
            cache.get_or_load((1, 2, 4), loader) for _ in range(5)
        ])
        self.assertEqual(results, [b"same"] * 5)
        self.assertEqual(calls, 1)

    async def test_byte_limit_evicts_old_chunks(self):
        cache = ChunkMemoryCache(5, 120)
        await cache.get_or_load((1, 2, 1), lambda: asyncio.sleep(0, result=b"1234"))
        await cache.get_or_load((1, 2, 2), lambda: asyncio.sleep(0, result=b"5678"))
        stats = await cache.stats()
        self.assertLessEqual(stats["bytes"], 5)
        self.assertGreaterEqual(stats["evictions"], 1)


if __name__ == "__main__":
    unittest.main()