#!/usr/bin/env python3
"""
Cache Monitor and Management Tool for Linkwarden Alfred Workflow

Provides tools to monitor, analyze, and manage the cache used by the
Linkwarden Alfred workflow.

Usage:
    python cache_monitor.py stats     # Show cache statistics
    python cache_monitor.py info      # Show detailed cache information
    python cache_monitor.py clear     # Clear all cache entries
    python cache_monitor.py cleanup   # Remove expired entries only
    python cache_monitor.py test      # Run cache verification tests

Author: joscandreu
"""

import sys
import os
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cache_manager import get_cache, clear_cache
from test_cache import run_cache_verification

# Try to import LinkwardenAPI for configuration display
try:
    from linkwarden_api import LinkwardenAPI
    HAS_API = True
except ImportError:
    HAS_API = False


def format_bytes(bytes_size):
    """Format bytes in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"


def format_duration(seconds):
    """Format duration in human readable format"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"


def show_cache_stats():
    """Display cache statistics"""
    cache = get_cache()
    stats = cache.get_stats()
    info = cache.cache_info()

    print("Linkwarden Cache Statistics")
    print("=" * 40)

    # Basic stats
    print(f"Cache Directory: {info['cache_dir']}")
    print(f"Cache Files: {info['file_count']}")
    print(f"Total Size: {format_bytes(info['total_size_bytes'])}")
    print()

    # Show cache configuration if API is available
    if HAS_API:
        try:
            # Set dummy environment variables if not set to avoid errors
            original_url = os.environ.get('LW_API_URL')
            original_token = os.environ.get('LW_API_TOKEN')

            if not original_url:
                os.environ['LW_API_URL'] = 'https://dummy.linkwarden.com'
            if not original_token:
                os.environ['LW_API_TOKEN'] = 'dummy_token'

            api = LinkwardenAPI(output_alfred_format=False)
            config = api.get_cache_config()

            print("Cache Configuration:")
            print(f"  Collections TTL: {config['collections_ttl_minutes']}m ({config['collections_ttl']}s)")
            print(f"  Tags TTL: {config['tags_ttl_minutes']}m ({config['tags_ttl']}s)")
            print(f"  Search TTL: {config['search_ttl_minutes']}m ({config['search_ttl']}s)")
            print()

            # Restore original environment
            if original_url is None and 'LW_API_URL' in os.environ:
                del os.environ['LW_API_URL']
            elif original_url is not None:
                os.environ['LW_API_URL'] = original_url

            if original_token is None and 'LW_API_TOKEN' in os.environ:
                del os.environ['LW_API_TOKEN']
            elif original_token is not None:
                os.environ['LW_API_TOKEN'] = original_token

        except SystemExit:
            # API initialization failed due to missing config, that's OK
            print("Cache Configuration:")
            print("  Collections TTL: 10m (600s) [default]")
            print("  Tags TTL: 10m (600s) [default]")
            print("  Search TTL: 2m (120s) [default]")
            print("  Configure via environment variables:")
            print("    LW_CACHE_COLLECTIONS_TTL, LW_CACHE_TAGS_TTL, LW_CACHE_SEARCH_TTL")
            print()
        except Exception:
            # Other errors, skip configuration display
            pass

    # Request statistics
    print("Request Statistics:")
    print(f"  Hits: {stats['hits']}")
    print(f"  Misses: {stats['misses']}")
    print(f"  Total Requests: {stats['total_requests']}")
    print(f"  Hit Rate: {stats['hit_rate']:.1%}")
    print()

    # Other stats
    print("Cache Operations:")
    print(f"  Sets: {stats['sets']}")
    print(f"  Expired: {stats['expired']}")
    print(f"  Errors: {stats['errors']}")
    print()

    # Performance assessment
    if stats['total_requests'] > 0:
        print("Performance Assessment:")
        if stats['hit_rate'] >= 0.7:
            print("  Excellent cache performance (≥70% hit rate)")
        elif stats['hit_rate'] >= 0.5:
            print("  Good cache performance (≥50% hit rate)")
        elif stats['hit_rate'] >= 0.3:
            print("  Fair cache performance (≥30% hit rate)")
        else:
            print("  Poor cache performance (<30% hit rate)")

        api_calls_saved = stats['hits']
        if api_calls_saved > 0:
            print(f"  API calls saved: {api_calls_saved}")
            print(f"  Estimated time saved: {format_duration(api_calls_saved * 0.5)}")
    else:
        print("No cache activity yet. Use the workflow to see statistics.")


def show_cache_info():
    """Display detailed cache information"""
    cache = get_cache()
    info = cache.cache_info()

    print("Detailed Cache Information")
    print("=" * 40)

    # Basic info
    print(f"Cache Directory: {info['cache_dir']}")
    print(f"Cache Files: {info['file_count']}")
    print(f"Total Size: {format_bytes(info['total_size_bytes'])}")
    print()

    # List cache files with details
    cache_dir = Path(info['cache_dir'])
    if cache_dir.exists():
        print("Cache Files:")
        cache_files = list(cache_dir.glob("*.json"))

        if not cache_files:
            print("  No cache files found")
        else:
            for cache_file in sorted(cache_files):
                try:
                    stat = cache_file.stat()
                    size = format_bytes(stat.st_size)

                    # Try to read cache data for more info
                    try:
                        with open(cache_file, 'r') as f:
                            cache_data = json.load(f)

                        created = datetime.fromtimestamp(cache_data.get('created_at', stat.st_mtime))
                        expires = datetime.fromtimestamp(cache_data.get('expires_at', 0))

                        # Check if expired
                        now = datetime.now()
                        status = "expired" if now > expires else "valid"
                        time_left = expires - now if now < expires else timedelta(0)

                        print(f"  {cache_file.name}")
                        print(f"      Size: {size}")
                        print(f"      Created: {created.strftime('%Y-%m-%d %H:%M:%S')}")
                        print(f"      Status: {status}")
                        if status == "valid":
                            print(f"      Expires in: {format_duration(time_left.total_seconds())}")

                        # Show cached data summary
                        if 'value' in cache_data:
                            value = cache_data['value']
                            if isinstance(value, list):
                                print(f"      Data: {len(value)} items")
                            elif isinstance(value, dict):
                                print(f"      Data: {len(value)} keys")
                            else:
                                print(f"      Data: {type(value).__name__}")
                        print()

                    except Exception:
                        print(f"  {cache_file.name} (Size: {size}) - Cannot read content")

                except Exception as e:
                    print(f"  {cache_file.name} - Error: {e}")
    else:
        print("Cache directory does not exist yet.")

    # Show statistics
    print("\nStatistics:")
    stats = cache.get_stats()
    for key, value in stats.items():
        if key == 'hit_rate':
            print(f"  {key}: {value:.1%}")
        else:
            print(f"  {key}: {value}")


def clear_cache_command():
    """Clear all cache entries"""
    print("Clearing cache...")

    cache = get_cache()
    deleted_count = cache.clear()

    print(f"Cleared {deleted_count} cache entries")
    print("Cache statistics have been reset.")

    # Reset statistics
    cache.reset_stats()


def cleanup_cache():
    """Remove only expired cache entries"""
    print("Cleaning up expired cache entries...")

    cache = get_cache()
    expired_count = cache.cleanup_expired()

    if expired_count > 0:
        print(f"Removed {expired_count} expired cache entries")
    else:
        print("No expired entries found")


def monitor_cache_realtime():
    """Monitor cache in real-time (demonstration)"""
    print("Real-time Cache Monitor")
    print("=" * 40)
    print("This would show real-time cache activity.")
    print("Use 'python cache_monitor.py stats' to see current statistics.")
    print("\nTo see cache activity, use the Linkwarden Alfred workflow and then check stats again.")


def benchmark_cache():
    """Run cache performance benchmark"""
    print("Cache Performance Benchmark")
    print("=" * 40)

    cache = get_cache()

    # Clear cache and reset stats for clean benchmark
    cache.clear()
    cache.reset_stats()

    # Benchmark cache operations
    test_data = {"benchmark": True, "data": list(range(100))}

    print("Running cache operations benchmark...")

    # Test cache set performance
    start_time = time.time()
    for i in range(100):
        cache.set(f"bench_key_{i}", test_data, ttl_seconds=60)
    set_time = time.time() - start_time

    # Test cache get performance (hits)
    start_time = time.time()
    for i in range(100):
        cache.get(f"bench_key_{i}")
    get_time = time.time() - start_time

    # Test cache get performance (misses)
    start_time = time.time()
    for i in range(100):
        cache.get(f"missing_key_{i}")
    miss_time = time.time() - start_time

    print(f"\nResults (100 operations each):")
    print(f"  Cache SET: {set_time:.3f}s ({set_time*10:.1f}ms per operation)")
    print(f"  Cache GET (hit): {get_time:.3f}s ({get_time*10:.1f}ms per operation)")
    print(f"  Cache GET (miss): {miss_time:.3f}s ({miss_time*10:.1f}ms per operation)")

    stats = cache.get_stats()
    print(f"\nBenchmark Statistics:")
    print(f"  Sets: {stats['sets']}")
    print(f"  Hits: {stats['hits']}")
    print(f"  Misses: {stats['misses']}")
    print(f"  Hit Rate: {stats['hit_rate']:.1%}")

    # Clean up benchmark data
    cache.clear()
    print(f"\nBenchmark complete, cache cleared")


def show_cache_config():
    """Show detailed cache configuration"""
    print("Cache Configuration")
    print("=" * 40)

    if HAS_API:
        try:
            # Set dummy environment variables if not set to avoid errors
            original_url = os.environ.get('LW_API_URL')
            original_token = os.environ.get('LW_API_TOKEN')

            if not original_url:
                os.environ['LW_API_URL'] = 'https://dummy.linkwarden.com'
            if not original_token:
                os.environ['LW_API_TOKEN'] = 'dummy_token'

            api = LinkwardenAPI(output_alfred_format=False)
            config = api.get_cache_config()

            print("Current TTL Settings:")
            print(f"  Collections: {config['collections_ttl_minutes']} minutes ({config['collections_ttl']} seconds)")
            print(f"  Tags: {config['tags_ttl_minutes']} minutes ({config['tags_ttl']} seconds)")
            print(f"  Search: {config['search_ttl_minutes']} minutes ({config['search_ttl']} seconds)")
            print()

            # Restore original environment
            if original_url is None and 'LW_API_URL' in os.environ:
                del os.environ['LW_API_URL']
            elif original_url is not None:
                os.environ['LW_API_URL'] = original_url

            if original_token is None and 'LW_API_TOKEN' in os.environ:
                del os.environ['LW_API_TOKEN']
            elif original_token is not None:
                os.environ['LW_API_TOKEN'] = original_token

        except SystemExit:
            print("Current TTL Settings:")
            print("  Collections: 10 minutes (600 seconds) [default]")
            print("  Tags: 10 minutes (600 seconds) [default]")
            print("  Search: 2 minutes (120 seconds) [default]")
            print()
        except Exception:
            print("Error reading configuration.")
            print()

    print("Environment Variables:")
    print("  LW_CACHE_COLLECTIONS_TTL   Collections cache TTL in seconds")
    print("  LW_CACHE_TAGS_TTL          Tags cache TTL in seconds")
    print("  LW_CACHE_SEARCH_TTL        Search results cache TTL in seconds")
    print()

    print("Current Environment Values:")
    collections_ttl = os.environ.get('LW_CACHE_COLLECTIONS_TTL', 'not set (default: 600)')
    tags_ttl = os.environ.get('LW_CACHE_TAGS_TTL', 'not set (default: 600)')
    search_ttl = os.environ.get('LW_CACHE_SEARCH_TTL', 'not set (default: 120)')

    print(f"  LW_CACHE_COLLECTIONS_TTL = {collections_ttl}")
    print(f"  LW_CACHE_TAGS_TTL = {tags_ttl}")
    print(f"  LW_CACHE_SEARCH_TTL = {search_ttl}")
    print()

    print("TTL Guidelines:")
    print("  • Minimum: 30 seconds")
    print("  • Maximum: 86400 seconds (24 hours)")
    print("  • Collections: 300-3600s (5m-1h) recommended")
    print("  • Tags: 300-3600s (5m-1h) recommended")
    print("  • Search: 60-300s (1m-5m) recommended")
    print()

    print("Configuration Examples:")
    print("  export LW_CACHE_COLLECTIONS_TTL=1800  # 30 minutes")
    print("  export LW_CACHE_TAGS_TTL=1800         # 30 minutes")
    print("  export LW_CACHE_SEARCH_TTL=300        # 5 minutes")


def show_help():
    """Show help information"""
    print("Linkwarden Cache Monitor")
    print("=" * 40)
    print("Usage: python cache_monitor.py <command>")
    print()
    print("Commands:")
    print("  stats     Show cache statistics and performance")
    print("  info      Show detailed cache information and file list")
    print("  config    Show cache configuration and TTL settings")
    print("  clear     Clear all cache entries")
    print("  cleanup   Remove expired entries only")
    print("  test      Run cache verification tests")
    print("  benchmark Run cache performance benchmark")
    print("  help      Show this help message")
    print()
    print("Examples:")
    print("  python cache_monitor.py stats")
    print("  python cache_monitor.py config")
    print("  python cache_monitor.py clear")


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        show_help()
        return

    command = sys.argv[1].lower()

    if command == 'stats':
        show_cache_stats()
    elif command == 'info':
        show_cache_info()
    elif command == 'config':
        show_cache_config()
    elif command == 'clear':
        clear_cache_command()
    elif command == 'cleanup':
        cleanup_cache()
    elif command == 'test':
        success = run_cache_verification()
        if not success:
            sys.exit(1)
    elif command == 'benchmark':
        benchmark_cache()
    elif command == 'monitor':
        monitor_cache_realtime()
    elif command == 'help':
        show_help()
    else:
        print(f"Unknown command: {command}")
        print("Use 'python cache_monitor.py help' for available commands.")
        sys.exit(1)


if __name__ == "__main__":
    main()