import unittest
import tempfile
import os
from pathlib import Path
from langnet.cache.core import QueryCache, NoOpCache, create_cache, get_cache_path


class TestQueryCache(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cache_path = Path(self.temp_dir)
        self.cache = QueryCache(cache_dir=self.cache_path)

    def tearDown(self):
        self.cache.close()
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cache_miss_returns_none(self):
        result = self.cache.get("lat", "lupus")
        self.assertIsNone(result)

    def test_cache_put_and_get(self):
        test_result = {"diogenes": {"word": "lupus"}, "whitakers": {"lemma": "lupus"}}
        self.cache.put("lat", "lupus", test_result)
        retrieved = self.cache.get("lat", "lupus")
        self.assertEqual(retrieved, test_result)

    def test_cache_different_lang_query(self):
        self.cache.put("lat", "lupus", {"result": "latin"})
        result = self.cache.get("grc", "lupus")
        self.assertIsNone(result)

    def test_cache_different_word(self):
        self.cache.put("lat", "lupus", {"result": "latin"})
        result = self.cache.get("lat", "canis")
        self.assertIsNone(result)

    def test_cache_multiple_puts_same_key(self):
        result1 = {"result": "first"}
        result2 = {"result": "second"}
        self.cache.put("lat", "lupus", result1)
        self.cache.put("lat", "lupus", result2)
        retrieved = self.cache.get("lat", "lupus")
        self.assertEqual(retrieved, result2)

    def test_cache_clear(self):
        self.cache.put("lat", "lupus", {"result": "latin"})
        self.cache.put("grc", "logos", {"result": "greek"})
        self.cache.clear()
        self.assertIsNone(self.cache.get("lat", "lupus"))
        self.assertIsNone(self.cache.get("grc", "logos"))

    def test_cache_clear_by_key(self):
        self.cache.put("lat", "lupus", {"result": "latin"})
        self.cache.put("lat", "canis", {"result": "canine"})
        count = self.cache.clear_by_key("lat", "lupus")
        self.assertEqual(count, 1)
        self.assertIsNone(self.cache.get("lat", "lupus"))
        self.assertIsNotNone(self.cache.get("lat", "canis"))


class TestNoOpCache(unittest.TestCase):
    def setUp(self):
        self.cache = NoOpCache()

    def test_get_always_returns_none(self):
        self.assertIsNone(self.cache.get("lat", "lupus"))
        self.assertIsNone(self.cache.get("grc", "logos"))

    def test_put_is_noop(self):
        self.cache.put("lat", "lupus", {"result": "test"})

    def test_clear_returns_zero(self):
        result = self.cache.clear()
        self.assertIsNone(result)

    def test_clear_by_lang_returns_zero(self):
        result = self.cache.clear_by_lang("lat")
        self.assertEqual(result, 0)

    def test_clear_by_key_returns_zero(self):
        result = self.cache.clear_by_key("lat", "lupus")
        self.assertEqual(result, 0)

    def test_close_is_noop(self):
        self.cache.close()


class TestNoOpCacheStats(unittest.TestCase):
    def setUp(self):
        self.cache = NoOpCache()

    def test_get_stats_returns_empty(self):
        stats = self.cache.get_stats()
        self.assertEqual(stats["total_entries"], 0)
        self.assertEqual(stats["by_language"], {})
        self.assertEqual(stats["total_size_human"], "0.0B")


class TestCreateCache(unittest.TestCase):
    def test_create_cache_enabled(self):
        cache = create_cache(cache_enabled=True)
        self.assertIsInstance(cache, QueryCache)

    def test_create_cache_disabled(self):
        cache = create_cache(cache_enabled=False)
        self.assertIsInstance(cache, NoOpCache)


class TestGetCachePath(unittest.TestCase):
    def test_returns_path(self):
        path = get_cache_path()
        self.assertIsInstance(path, Path)
        self.assertTrue(path.parent.exists())


if __name__ == "__main__":
    unittest.main()
