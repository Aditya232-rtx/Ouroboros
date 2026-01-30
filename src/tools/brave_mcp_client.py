"""
Brave Search Direct API Client
Bypasses deprecated MCP server and calls Brave Search API directly
"""

import logging
import os
import aiohttp
from typing import List, TypedDict, Optional

logger = logging.getLogger(__name__)


class BraveSearchResult(TypedDict):
    """Result from Brave Search"""
    title: str
    url: str
    snippet: str
    published_at: Optional[str]


class BraveSearchClient:
    """
    Direct client for Brave Search API (HTTP).
    No MCP server required.
    """
    
    def __init__(self, api_key: str = None):
        """
        Initialize Brave Search client.
        
        Args:
            api_key: Brave Search API key (default: reads from BRAVE_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("BRAVE_API_KEY", "")
        
        if not self.api_key:
            logger.warning("BRAVE_API_KEY not set. Brave Search functionality will fail.")
        
    async def search(
        self, 
        query: str, 
        freshness: str = "30d", 
        limit: int = 10
    ) -> List[BraveSearchResult]:
        """
        Call the Brave Search API directly and return results.
        
        Args:
            query: Search query string
            freshness: Time filter ("24h", "7d", "30d", "year", or None)
            limit: Maximum number of results to return
            
        Returns:
            List of BraveSearchResult dictionaries
        """
        try:
            if not self.api_key:
                logger.error("BRAVE_API_KEY not set")
                return []
            
            # Construct API request
            url = "https://api.search.brave.com/res/v1/web/search"
            headers = {
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": self.api_key
            }
            params = {
                "q": query,
                "count": min(limit, 20)  # Brave API max is 20
            }
            
            # Add freshness parameter if specified
            if freshness:
                params["freshness"] = freshness
            
            logger.info(f"Brave Search: {query} (freshness={freshness}, limit={limit})")
            
            # Make async HTTP request
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params, timeout=timeout) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Brave API error {response.status}: {error_text[:200]}")
                        return []
                    
                    data = await response.json()
            
            # Extract web results
            web_results = data.get("web", {}).get("results", [])
            
            if not web_results:
                logger.warning(f"No results for: {query}")
                return []
            
            # Normalize to BraveSearchResult format
            normalized_results = []
            for result in web_results[:limit]:
                normalized_results.append(BraveSearchResult(
                    title=result.get("title", "Untitled"),
                    url=result.get("url", ""),
                    snippet=result.get("description", ""),
                    published_at=result.get("age", None)
                ))
            
            logger.info(f"Retrieved {len(normalized_results)} results")
            return normalized_results
            
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error: {e}")
            return []
        except Exception as e:
            logger.error(f"Brave Search failed: {e}", exc_info=True)
            return []


# Compatibility: Keep old name for existing imports
BraveMCPClient = BraveSearchClient
