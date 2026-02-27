#!/usr/bin/env python3
"""
Ouroboros Demo — copy-paste this to test the SDK end-to-end.

Prerequisites:
  1. cp config.example.yaml config.yaml  →  add GitHub token
  2. Ensure Ollama is running:  ollama serve
  3. Pull model:  ollama pull qwen2.5-coder:1.5b
"""
import asyncio
from ouroboros import Ouroboros

DEMO_REPO = "https://github.com/octocat/Hello-World"  # Replace with target repo


async def main():
    print("🚀 Starting Ouroboros demo scan ...\n")
    ouro = Ouroboros("config.yaml")
    result = await ouro.scan(DEMO_REPO)

    print("\n── Results ──────────────────────────────────────")
    print(f"Scan ID         : {result.get('scan_id', '?')}")
    print(f"Vulnerabilities : {result['vulnerabilities_found']}")
    print(f"Critical        : {result['critical_count']}")
    print(f"Fixes           : {result['fixes_generated']}")
    print(f"Risk reduction  : {result['risk_reduction_pct']}%")
    print(f"GitHub PR       : {result.get('pr_url') or '—'}")
    print(f"PDF report      : {result.get('docs_path') or '—'}")
    print("─────────────────────────────────────────────────")


if __name__ == "__main__":
    asyncio.run(main())
