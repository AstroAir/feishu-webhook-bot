"""Web search module for AI capabilities.

This module provides a unified interface for web search across multiple
search engine providers including:
- DuckDuckGo (free, no API key required)
- Tavily (AI-optimized search)
- Exa (semantic search)
- Brave Search
- Bing Web Search API
- Google Custom Search

Features:
- Unified search interface with standardized results
- Automatic failover between providers
- Result caching for performance
- Concurrent search across multiple providers
"""

from .base import SearchError, SearchProvider, SearchResult
from .cache import SearchCache
from .manager import SearchManager

__all__ = [
    "SearchProvider",
    "SearchResult",
    "SearchError",
    "SearchCache",
    "SearchManager",
]
