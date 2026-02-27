"""
Ouroboros AI - Cache & Temp File Cleaner  (Task 6.3)
======================================================
Purges stale artifacts before a clean training run:

  1. Stale model directories in `models/` that are NOT Modelfiles or README
     (e.g. regularization audit leftover checkpoints, partial adapters)
  2. Python __pycache__ directories across the entire project
  3. Orphaned .pyc compiled bytecode files
  4. Optionally: HuggingFace model hub cache (~/.cache/huggingface/hub)

ALWAYS use --dry-run first to preview what will be deleted.

Usage
-----
  # Preview everything that would be deleted (safe)
  python scripts/utils/clear_cache.py --dry-run

  # Delete stale model dirs + pycache only
  python scripts/utils/clear_cache.py

  # Also wipe HuggingFace hub cache (frees downloaded model weights)
  python scripts/utils/clear_cache.py --all
"""

import argparse
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT       = Path(__file__).resolve().parent.parent.parent
MODELS_DIR = ROOT / "models"

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def dir_size_mb(path: Path) -> float:
    try:
        return sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) / 1e6
    except Exception:
        return 0.0


def file_size_kb(path: Path) -> float:
    try:
        return path.stat().st_size / 1e3
    except Exception:
        return 0.0


def confirm(prompt: str) -> bool:
    try:
        ans = input(f"  {prompt} [y/N]: ").strip().lower()
        return ans in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


# ─────────────────────────────────────────────────────────────────────────────
# TARGET FINDERS
# ─────────────────────────────────────────────────────────────────────────────

# Files/dirs in models/ that should NEVER be deleted
MODELS_ALLOWLIST = {
    "Modelfile.deepseek",
    "Modelfile.phi3",
    "Modelfile.phi3.new",
    "Modelfile.qwen",
    "README.md",
    # Final adapter output dirs (only stale intermediate dirs are deleted)
    "ouroboros-blue-final",
}

# Patterns that identify "stale" checkpoint or audit artifact dirs
STALE_DIR_PATTERNS = [
    "checkpoint-",          # HF SFTTrainer checkpoint dirs
    "tmp_",
    "debug_",
    "audit_",
    "test_run",
    "regularization_",
]

# Dir names that look like completed model output but are not the final one
STALE_DIR_NAME_EXACT = {
    "ouroboros-blue-lora",  # intermediate checkpoint root, may exist without final export
}


def find_stale_model_dirs() -> List[Tuple[Path, float, str]]:
    """
    Return (path, size_mb, reason) for all stale entries under models/.
    Skips anything in MODELS_ALLOWLIST.
    """
    if not MODELS_DIR.exists():
        return []

    targets = []
    for entry in MODELS_DIR.iterdir():
        if entry.name in MODELS_ALLOWLIST:
            continue

        reason = None

        # Exact stale dir names
        if entry.name in STALE_DIR_NAME_EXACT and entry.is_dir():
            reason = "intermediate training dir (safe to remove before clean run)"

        # Pattern-matched
        if not reason:
            for pat in STALE_DIR_PATTERNS:
                if pat in entry.name:
                    reason = f"matches stale pattern '{pat}'"
                    break

        # Orphaned .json / .bin files not inside a named adapter dir
        if not reason and entry.is_file() and entry.suffix in (".bin", ".pt", ".ckpt"):
            reason = "orphaned weight file at models/ root"

        if reason:
            size = dir_size_mb(entry) if entry.is_dir() else file_size_kb(entry) / 1e3
            targets.append((entry, size, reason))

    return targets


def find_pycache_dirs() -> List[Tuple[Path, float, str]]:
    """Find all __pycache__ dirs under the project root (excluding venv)."""
    targets = []
    for d in ROOT.rglob("__pycache__"):
        if "venv" in d.parts:
            continue
        if ".git" in d.parts:
            continue
        size = dir_size_mb(d)
        targets.append((d, size, "__pycache__"))
    return targets


def find_pyc_files() -> List[Tuple[Path, float, str]]:
    """Find orphaned .pyc files outside __pycache__ (unusual but possible)."""
    targets = []
    for f in ROOT.rglob("*.pyc"):
        if "venv" in f.parts:
            continue
        if "__pycache__" in f.parts:
            continue
        targets.append((f, file_size_kb(f) / 1e3, "orphaned .pyc"))
    return targets


def find_hf_cache() -> List[Tuple[Path, float, str]]:
    """Find the HuggingFace hub cache directory."""
    import os
    hf_home = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface"))
    hub     = hf_home / "hub"
    if hub.exists():
        size = dir_size_mb(hub)
        return [(hub, size, "HuggingFace hub model cache")]
    return []


# ─────────────────────────────────────────────────────────────────────────────
# DELETION
# ─────────────────────────────────────────────────────────────────────────────

def delete_target(path: Path, dry_run: bool) -> bool:
    """Delete a file or directory. Returns True on success."""
    if dry_run:
        return True
    try:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        return True
    except Exception as e:
        print(f"    ERROR deleting {path}: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# REPORT
# ─────────────────────────────────────────────────────────────────────────────

def print_targets(
    label: str,
    targets: List[Tuple[Path, float, str]],
    dry_run: bool,
) -> None:
    if not targets:
        print(f"\n  {label}: nothing to clean")
        return
    total_mb = sum(t[1] for t in targets)
    print(f"\n  {label}  ({len(targets)} item(s), {total_mb:.1f} MB):")
    for path, size_mb, reason in targets:
        tag = "[DRY-RUN] Would delete" if dry_run else "Deleted"
        print(f"    {size_mb:>7.1f} MB  {path.relative_to(ROOT)}  ({reason})")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

def run_clear_cache(
    dry_run: bool = True,
    include_hf: bool = False,
    skip_confirm: bool = False,
) -> Dict:
    t0 = time.time()

    print(f"\n{'=' * 66}")
    print(f"  CACHE CLEANER  (Task 6.3)  {'[DRY-RUN - nothing will be deleted]' if dry_run else ''}")
    print(f"{'─' * 66}")

    # Gather all targets
    stale_models  = find_stale_model_dirs()
    pycache_dirs  = find_pycache_dirs()
    pyc_files     = find_pyc_files()
    hf_cache      = find_hf_cache() if include_hf else []

    all_targets   = stale_models + pycache_dirs + pyc_files + hf_cache
    total_mb      = sum(t[1] for t in all_targets)

    # Print before-delete summary
    print_targets("Stale model dirs", stale_models, dry_run)
    print_targets("Python __pycache__", pycache_dirs, dry_run)
    if pyc_files:
        print_targets("Orphaned .pyc files", pyc_files, dry_run)
    if include_hf:
        print_targets("HuggingFace hub cache", hf_cache, dry_run)

    print(f"\n{'─' * 66}")
    print(f"  Total reclaimable: {total_mb:.1f} MB  across {len(all_targets)} item(s)")

    if not all_targets:
        print("  Nothing to clean. Project is already tidy.")
        print(f"{'=' * 66}\n")
        return {"deleted": 0, "reclaimed_mb": 0, "dry_run": dry_run}

    # Confirm if not dry-run
    if not dry_run and not skip_confirm:
        print()
        if not confirm(f"Delete {len(all_targets)} item(s) ({total_mb:.1f} MB)?"):
            print("  Aborted. No files were deleted.")
            print(f"{'=' * 66}\n")
            return {"deleted": 0, "reclaimed_mb": 0, "dry_run": dry_run}

    # Execute deletions
    deleted_count = 0
    for path, size_mb, reason in all_targets:
        ok = delete_target(path, dry_run)
        if ok:
            action = "Would delete" if dry_run else "Deleted"
            print(f"  [{action}] {path.relative_to(ROOT)}  ({size_mb:.1f} MB)")
            deleted_count += 1

    print(f"\n{'─' * 66}")
    verb = "Would reclaim" if dry_run else "Reclaimed"
    print(f"  {verb} {total_mb:.1f} MB from {deleted_count} item(s)  ({time.time()-t0:.1f}s)")
    if dry_run:
        print("  Re-run without --dry-run to actually delete.")
    print(f"{'=' * 66}\n")

    return {"deleted": deleted_count, "reclaimed_mb": round(total_mb, 1), "dry_run": dry_run}


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Ouroboros - Cache Cleaner (Task 6.3)",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--dry-run",    action="store_true",
                        help="Preview what would be deleted (safe, default for safety)")
    parser.add_argument("--all",        action="store_true",
                        help="Also clear HuggingFace hub cache (~/.cache/huggingface/hub)")
    parser.add_argument("--yes",        action="store_true",
                        help="Skip confirmation prompt (use with caution)")
    return parser.parse_args()


def main():
    args = parse_args()
    print("=" * 66)
    print("  Ouroboros -- Cache & Temp File Cleaner  (Task 6.3)")
    print("=" * 66)
    run_clear_cache(
        dry_run      = args.dry_run,
        include_hf   = args.all,
        skip_confirm = args.yes,
    )


if __name__ == "__main__":
    main()
