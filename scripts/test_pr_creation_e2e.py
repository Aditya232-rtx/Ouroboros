#!/usr/bin/env python3
"""
End-to-end test: Fork → Clone → Branch → Commit → Push → Create PR

Target repo: https://github.com/harshita-dhande/banking-api-demo.git
"""

import sys
import os
import time
import shutil
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ── Setup logging before anything else ──────────────────────────────
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pr_test")


def main():
    from src.integrations.github_api import github_client
    from config.settings import settings

    TARGET_REPO = "harshita-dhande/banking-api-demo"
    BASE_BRANCH = "main"
    BRANCH_NAME = f"ouroboros-test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    # ── Preflight checks ────────────────────────────────────────────
    if not settings.github_token:
        logger.error("❌ GITHUB_TOKEN is not set in .env")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("Ouroboros PR Creation E2E Test")
    logger.info("=" * 60)
    logger.info(f"  Target repo : {TARGET_REPO}")
    logger.info(f"  Base branch : {BASE_BRANCH}")
    logger.info(f"  Head branch : {BRANCH_NAME}")

    user = github_client.get_authenticated_user()
    logger.info(f"  Auth user   : {user}")
    logger.info("=" * 60)

    repo_path = None
    try:
        # ── Step 1: Fork ────────────────────────────────────────────
        logger.info("\n🔱 Step 1/6: Forking repository...")
        fork_url = github_client.fork_repository(TARGET_REPO)
        logger.info(f"  ✅ Fork URL: {fork_url[:40]}...")

        # GitHub needs time to finish creating the fork
        logger.info("  ⏳ Waiting 8s for GitHub to provision fork...")
        time.sleep(8)

        # ── Step 2: Clone the fork ──────────────────────────────────
        logger.info("\n📥 Step 2/6: Cloning fork...")
        repo_path = github_client.clone_repository(
            repo_url=fork_url,
            branch=BASE_BRANCH,
        )
        logger.info(f"  ✅ Cloned to: {repo_path}")

        # ── Step 3: Create branch ──────────────────────────────────
        logger.info(f"\n🌿 Step 3/6: Creating branch {BRANCH_NAME}...")
        github_client.create_branch(repo_path, BRANCH_NAME)
        logger.info(f"  ✅ Branch created")

        # ── Step 4: Make a test change & commit ─────────────────────
        logger.info("\n📝 Step 4/6: Writing test fix & committing...")
        test_file = repo_path / "ouroboros_test_fix.md"
        test_file.write_text(
            f"# Ouroboros AI Test Fix\n\n"
            f"This file was created by the Ouroboros PR-creation E2E test.\n\n"
            f"- **Branch**: `{BRANCH_NAME}`\n"
            f"- **Timestamp**: {datetime.now().isoformat()}\n"
            f"- **Purpose**: Verify fork → clone → branch → commit → push → PR flow\n",
            encoding="utf-8",
        )
        commit_sha = github_client.commit_changes(
            repo_path,
            f"[Ouroboros Test] Verify PR creation pipeline\n\nBranch: {BRANCH_NAME}",
        )
        logger.info(f"  ✅ Commit SHA: {commit_sha}")

        # ── Step 5: Push to fork (origin) ──────────────────────────
        logger.info("\n🚀 Step 5/6: Pushing to fork (origin)...")
        github_client.push_branch(repo_path, BRANCH_NAME)
        logger.info(f"  ✅ Pushed")

        # ── Step 6: Create cross-repo PR ───────────────────────────
        logger.info(f"\n📬 Step 6/6: Creating PR on {TARGET_REPO}...")
        head_ref = f"{user}:{BRANCH_NAME}"
        logger.info(f"  Head ref: {head_ref}")

        pr_data = github_client.create_pull_request(
            repo_full_name=TARGET_REPO,
            title=f"[Ouroboros Test] E2E PR creation test",
            body=(
                f"## Ouroboros AI — Automated PR Test\n\n"
                f"This PR was created by the Ouroboros E2E test script to verify the "
                f"full fork → clone → branch → commit → push → PR pipeline.\n\n"
                f"- **Branch**: `{BRANCH_NAME}`\n"
                f"- **Commit**: `{commit_sha[:7]}`\n"
                f"- **Timestamp**: {datetime.now().isoformat()}\n\n"
                f"*Safe to close/delete — this is an automated test.*"
            ),
            head_branch=head_ref,
            base_branch=BASE_BRANCH,
        )

        logger.info("\n" + "=" * 60)
        logger.info("🎉 SUCCESS — PR Created!")
        logger.info(f"  PR #{pr_data['pr_number']}: {pr_data['pr_url']}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"\n❌ FAILED: {e}", exc_info=True)
        sys.exit(1)

    finally:
        # Cleanup temp dir
        if repo_path and repo_path.exists() and str(repo_path).startswith("/tmp/"):
            logger.info(f"\n🧹 Cleaning up {repo_path}")
            shutil.rmtree(repo_path, ignore_errors=True)


if __name__ == "__main__":
    main()
