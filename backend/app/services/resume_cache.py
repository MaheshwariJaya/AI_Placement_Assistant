import hashlib
import logging
from collections import OrderedDict
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Cache Invalidation Versions
EXTRACTION_SCHEMA_VERSION = "v1.0"
EXTRACTION_PROMPT_VERSION = "v1.3"


def compute_extraction_cache_key(
    file_hash: str,
    provider: str,
    model: str,
    schema_version: str = EXTRACTION_SCHEMA_VERSION,
    prompt_version: str = EXTRACTION_PROMPT_VERSION,
) -> str:
    """
    Generate a deterministic SHA-256 cache key incorporating:
    - SHA-256 file hash of the resume document
    - Extraction schema version
    - Extraction prompt version
    - AI Provider name
    - Provider Model name
    """
    raw_key = f"{file_hash}:{schema_version}:{prompt_version}:{provider.lower()}:{model.lower()}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


class ResumeExtractionCache:
    """
    Safe in-memory LRU cache for structured resume extraction results.
    Prevents duplicate extraction requests and saves billable LLM tokens.
    """

    def __init__(self, max_size: int = 256):
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached extraction payload if present."""
        if cache_key in self._cache:
            self._hits += 1
            self._cache.move_to_end(cache_key)
            return self._cache[cache_key]
        self._misses += 1
        return None

    def put(self, cache_key: str, data: Dict[str, Any]) -> None:
        """Store extraction payload in cache, evicting oldest if max_size exceeded."""
        if cache_key in self._cache:
            self._cache.move_to_end(cache_key)
        self._cache[cache_key] = data
        if len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    def clear(self) -> None:
        """Clear all entries and reset hit/miss counters."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    @property
    def stats(self) -> Dict[str, int]:
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
        }


# Singleton service-level cache instance
extraction_cache = ResumeExtractionCache()

