#!/usr/bin/env python3
"""
Cache Manager for Linkwarden Alfred Workflow

Provides simple file-based caching with TTL support to reduce API calls
and improve workflow responsiveness.

Features:
- File-based cache storage in system temp directory
- TTL (Time To Live) support with automatic expiration
- Cache statistics for monitoring and testing
- Thread-safe operations
- Automatic cleanup of expired entries

Author: joscandreu
"""

import os
import json
import time
import tempfile
import threading
from typing import Any, Dict, Optional, Tuple
from pathlib import Path


class CacheManager:
    """
    Simple file-based cache manager with TTL support.

    This cache is optimized for the Alfred workflow use case where:
    - Cache hit speed is critical (file-based is fast enough)
    - Data persistence across workflow runs is beneficial
    - Memory usage should be minimal
    - Network calls are the primary bottleneck
    """

    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize cache manager.

        Args:
            cache_dir: Custom cache directory path. If None, uses system temp.
        """
        self.cache_dir = Path(cache_dir) if cache_dir else Path(tempfile.gettempdir()) / "linkwarden_cache"
        self.cache_dir.mkdir(exist_ok=True)

        # Cache statistics for monitoring
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'expired': 0,
            'errors': 0
        }

        # Thread lock for stats (overkill for Alfred but good practice)
        self._stats_lock = threading.Lock()

    def _get_cache_file(self, key: str) -> Path:
        """Get cache file path for a given key."""
        safe_key = "".join(c for c in key if c.isalnum() or c in ('_', '-', '.'))
        return self.cache_dir / f"{safe_key}.json"

    def _is_expired(self, cache_data: Dict) -> bool:
        """Check if cache entry has expired."""
        if 'expires_at' not in cache_data:
            return True
        return time.time() > cache_data['expires_at']

    def get(self, key: str) -> Tuple[Optional[Any], bool]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Tuple of (value, hit) where hit indicates if cache was hit
        """
        cache_file = self._get_cache_file(key)

        try:
            if not cache_file.exists():
                with self._stats_lock:
                    self.stats['misses'] += 1
                return None, False

            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            if self._is_expired(cache_data):
                # Remove expired file
                cache_file.unlink(missing_ok=True)
                with self._stats_lock:
                    self.stats['expired'] += 1
                    self.stats['misses'] += 1
                return None, False

            with self._stats_lock:
                self.stats['hits'] += 1
            return cache_data['value'], True

        except Exception as e:
            # On any error, treat as cache miss
            with self._stats_lock:
                self.stats['errors'] += 1
                self.stats['misses'] += 1
            return None, False

    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> bool:
        """
        Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl_seconds: Time to live in seconds (default: 5 minutes)

        Returns:
            True if successfully cached, False otherwise
        """
        cache_file = self._get_cache_file(key)

        try:
            cache_data = {
                'value': value,
                'expires_at': time.time() + ttl_seconds,
                'created_at': time.time()
            }

            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)

            with self._stats_lock:
                self.stats['sets'] += 1
            return True

        except Exception as e:
            with self._stats_lock:
                self.stats['errors'] += 1
            return False

    def delete(self, key: str) -> bool:
        """
        Delete specific cache entry.

        Args:
            key: Cache key to delete

        Returns:
            True if deleted, False if not found or error
        """
        cache_file = self._get_cache_file(key)
        try:
            if cache_file.exists():
                cache_file.unlink()
                return True
            return False
        except Exception:
            with self._stats_lock:
                self.stats['errors'] += 1
            return False

    def clear(self) -> int:
        """
        Clear all cache entries.

        Returns:
            Number of files deleted
        """
        deleted_count = 0
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    cache_file.unlink()
                    deleted_count += 1
                except Exception:
                    pass
        except Exception:
            pass
        return deleted_count

    def cleanup_expired(self) -> int:
        """
        Remove all expired cache entries.

        Returns:
            Number of expired entries removed
        """
        expired_count = 0
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)

                    if self._is_expired(cache_data):
                        cache_file.unlink()
                        expired_count += 1

                except Exception:
                    # If we can't read the file, consider it corrupted and remove it
                    try:
                        cache_file.unlink()
                        expired_count += 1
                    except Exception:
                        pass
        except Exception:
            pass

        with self._stats_lock:
            self.stats['expired'] += expired_count
        return expired_count

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics including hit rate
        """
        with self._stats_lock:
            stats = self.stats.copy()

        total_requests = stats['hits'] + stats['misses']
        stats['hit_rate'] = stats['hits'] / total_requests if total_requests > 0 else 0.0
        stats['total_requests'] = total_requests

        return stats

    def reset_stats(self):
        """Reset cache statistics."""
        with self._stats_lock:
            self.stats = {
                'hits': 0,
                'misses': 0,
                'sets': 0,
                'expired': 0,
                'errors': 0
            }

    def cache_info(self) -> Dict[str, Any]:
        """
        Get comprehensive cache information.

        Returns:
            Dictionary with cache directory, file count, and statistics
        """
        file_count = 0
        total_size = 0

        try:
            for cache_file in self.cache_dir.glob("*.json"):
                if cache_file.is_file():
                    file_count += 1
                    total_size += cache_file.stat().st_size
        except Exception:
            pass

        return {
            'cache_dir': str(self.cache_dir),
            'file_count': file_count,
            'total_size_bytes': total_size,
            'stats': self.get_stats()
        }


# Global cache instance for the workflow
_cache_instance = None


def get_cache() -> CacheManager:
    """Get the global cache instance (singleton pattern)."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheManager()
    return _cache_instance


def clear_cache():
    """Clear the global cache."""
    cache = get_cache()
    return cache.clear()


def cache_stats():
    """Get global cache statistics."""
    cache = get_cache()
    return cache.get_stats()