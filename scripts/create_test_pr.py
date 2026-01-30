import os
import sys
import logging
import subprocess
import shutil
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.integrations.github_api import GitHubClient
from config.settings import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_pr")

def main():
    target_repo_name = "Aditya232-rtx/vul"
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    branch_name = f"test-pr-agent-{timestamp}"
    
    logger.info(f"Starting Fork-based PR test for {target_repo_name} on branch {branch_name}")
    
    # Initialize client
    client = GitHubClient()
    if not client.client:
        logger.error("GitHub client not initialized (check token)")
        sys.exit(1)
        
    target_dir = Path("/tmp") / f"vul_test_{timestamp}"
    
    try:
        # 1. Fork Repository
        logger.info(f"Forking {target_repo_name}...")
        fork_clone_url = client.fork_repository(target_repo_name)
        # Give GitHub a moment to process the fork
        time.sleep(5)
        
        # 2. Clone Fork
        # Construct authenticated URL for pushing
        clean_url = fork_clone_url.replace("https://", "")
        auth_repo_url = f"https://{settings.github_token}@{clean_url}"
        
        logger.info(f"Cloning fork to {target_dir}...")
        subprocess.run(["git", "clone", auth_repo_url, str(target_dir)], check=True)
        
        # 3. Create Branch
        logger.info(f"Creating branch {branch_name}...")
        subprocess.run(["git", "-C", str(target_dir), "checkout", "-b", branch_name], check=True)
        
        # 4. Make Edit
        file_path = target_dir / "agent_test_edit.txt"
        with open(file_path, "w") as f:
            f.write(f"Test edit by Ouroboros Agent (Fork Workflow) at {timestamp}\n")
        
        # 5. Commit
        logger.info("Committing changes...")
        subprocess.run(["git", "-C", str(target_dir), "add", "agent_test_edit.txt"], check=True)
        subprocess.run(["git", "-C", str(target_dir), "commit", "-m", "chore: test edit from agent via fork"], check=True)
        
        # 6. Push to Fork
        logger.info("Pushing changes to fork...")
        # Since we cloned the fork, 'origin' is the fork
        subprocess.run(["git", "-C", str(target_dir), "push", "-u", "origin", branch_name], check=True)
        
        # 7. Create PR
        logger.info("Creating Pull Request...")
        
        # Determine username for head ref
        username = client.client.get_user().login
        # Cross-repo PR format: "username:branch_name"
        head_ref = f"{username}:{branch_name}"
        
        pr_result = client.create_pull_request(
            repo_full_name=target_repo_name,  # PR against original repo
            title=f"Test PR: Agent Verification {timestamp}",
            body="This is a test PR created automatically by Ouroboros AI via fork workflow.",
            head_branch=head_ref,
            base_branch="main"
        )
        
        print(f"\nSUCCESS! PR Created: {pr_result['pr_url']}")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Git command failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        if target_dir.exists():
            shutil.rmtree(target_dir)
            logger.info("Cleaned up temp directory")

if __name__ == "__main__":
    main()
