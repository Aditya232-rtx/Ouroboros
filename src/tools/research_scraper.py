"""
Ouroboros Research Agent — Chunk 1: The Searcher (Ingestion)
Implements the PentAGI 'Searcher Agent' ingestion pattern.

Scrapes security blogs and exploit databases, returning AI-optimised clean
Markdown that is token-efficient for the local qwen2.5-coder:1.5b reasoning node.
"""

import asyncio
from crawl4ai import AsyncWebCrawler


async def scrape_vulnerability_data(url: str) -> str:
    """
    Scrapes a security blog or exploit database and returns clean Markdown.

    This fulfils the PentAGI 'Searcher Agent' ingestion requirement by
    ensuring token-efficiency for the local LLM reasoning node.
    Crawl4AI performs AI-optimised DOM parsing to aggressively prune
    boilerplate, navigation bars, and styling artifacts.
    """
    print(f"[*] Research Agent initiating PentAGI-style scrape for: {url}")

    # Initialise the asynchronous crawler
    async with AsyncWebCrawler(verbose=True) as crawler:
        # Run the crawler on the target URL
        result = await crawler.arun(
            url=url,
            # Bypass cache to get the freshest zero-day info
            bypass_cache=True
        )

        if result.success:
            print("[+] Scrape successful! Extracted clean Markdown.")
            return result.markdown
        else:
            print(f"[-] Scrape failed: {result.error_message}")
            return ""


# ── Quick Test Block ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Example: A standard CVE advisory
    test_url = "https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2023-38408"

    markdown_output = asyncio.run(scrape_vulnerability_data(test_url))

    print("\n--- SCRAPED MARKDOWN PREVIEW ---\n")
    if markdown_output:
        print(markdown_output[:500] + "\n...[TRUNCATED]")
    else:
        print("No markdown was generated. Check your network or URL.")
