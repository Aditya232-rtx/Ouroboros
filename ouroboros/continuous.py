"""
ouroboros/continuous.py — Watch mode (continuous monitoring).

Re-scans a repo on a fixed interval and raises PRs on new findings.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core import Ouroboros

logger = logging.getLogger("ouroboros.continuous")


class ContinuousScanner:
    """
    Periodically re-scans a repository and opens PRs for new findings.

    Usage::

        scanner = ContinuousScanner(sdk, repo_url, interval_seconds=300)
        await scanner.start()   # blocks until Ctrl-C
    """

    def __init__(
        self,
        sdk: "Ouroboros",
        repo_url: str,
        interval_seconds: int = 300,
    ):
        self.sdk = sdk
        self.repo_url = repo_url
        self.interval_seconds = interval_seconds
        self._seen_vulns: set = set()

    async def start(self):
        logger.info(
            "Continuous scan started for %s (every %ds)",
            self.repo_url,
            self.interval_seconds,
        )
        print(
            f"👁️  Continuous scan started for {self.repo_url}\n"
            f"   Interval: every {self.interval_seconds}s  (Ctrl-C to stop)\n"
        )

        while True:
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            print(f"[{ts}] Running scan ...")
            try:
                result = await self.sdk.scan(self.repo_url)
                new_vulns = result.get("vulnerabilities_found", 0)
                pr = result.get("pr_url", "—")
                fixes = result.get("fixes_generated", 0)
                print(
                    f"[{ts}] ✅  PR: {pr}  |  "
                    f"vulns: {new_vulns}  |  fixes: {fixes}"
                )
            except KeyboardInterrupt:
                print("\n🛑  Watch mode stopped.")
                break
            except Exception as exc:
                logger.error("Scan error: %s", exc)
                print(f"[{ts}] ⚠️  Scan error: {exc}")

            await asyncio.sleep(self.interval_seconds)
