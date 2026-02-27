"""
Ouroboros AI - Checkpoint Manager  (Task 4.2)
=============================================
Inspect, rank, and manage training checkpoints saved by the SFTTrainer.
Identifies the best checkpoint by lowest eval_loss, supports resuming
interrupted runs, and exports the winning adapter to a clean output path.

Usage
-----
  # List all checkpoints + their eval_loss
  python scripts/training/checkpoint_manager.py --list

  # Print only the best checkpoint path (for scripting)
  python scripts/training/checkpoint_manager.py --best

  # Print the latest checkpoint path (for --resume-from-checkpoint)
  python scripts/training/checkpoint_manager.py --resume

  # Copy best checkpoint to a clean export directory
  python scripts/training/checkpoint_manager.py --export

  # Point at a custom checkpoint directory
  python scripts/training/checkpoint_manager.py --list --ckpt-dir models/my-run
"""

import argparse
import json
import logging
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("checkpoint_manager")

ROOT         = Path(__file__).resolve().parent.parent.parent
DEFAULT_DIR  = ROOT / "models" / "ouroboros-blue-lora"
EXPORT_DIR   = ROOT / "models" / "ouroboros-blue-final"

# ─────────────────────────────────────────────────────────────────────────────
# CHECKPOINT DISCOVERY
# ─────────────────────────────────────────────────────────────────────────────

def find_checkpoints(ckpt_dir: Path) -> List[Path]:
    """
    Return all checkpoint subdirectories, sorted by global_step ascending.
    HuggingFace names them: checkpoint-<step>
    """
    if not ckpt_dir.exists():
        return []
    ckpts = sorted(
        [d for d in ckpt_dir.iterdir()
         if d.is_dir() and d.name.startswith("checkpoint-")],
        key=lambda p: _step_from_name(p.name),
    )
    return ckpts


def _step_from_name(name: str) -> int:
    """Extract the step number from 'checkpoint-1234'."""
    try:
        return int(name.split("-")[-1])
    except ValueError:
        return 0


def read_trainer_state(ckpt: Path) -> Optional[Dict]:
    """
    Read trainer_state.json from a checkpoint directory.
    Contains: log_history (list of dicts with eval_loss, step, epoch…)
    """
    state_file = ckpt / "trainer_state.json"
    if not state_file.exists():
        return None
    # Use utf-8-sig to strip BOM if present (PowerShell Out-File adds one)
    for enc in ("utf-8-sig", "utf-8"):
        try:
            with state_file.open(encoding=enc) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
    return None


def get_eval_loss(ckpt: Path) -> Optional[float]:
    """
    Extract the eval_loss recorded for this checkpoint.
    Looks in trainer_state.json log_history for the entry matching the step.
    """
    step = _step_from_name(ckpt.name)
    state = read_trainer_state(ckpt)
    if state is None:
        return None

    # Walk log_history: find latest entry at or before this step with eval_loss
    best_loss = None
    for entry in state.get("log_history", []):
        if entry.get("step", 0) <= step and "eval_loss" in entry:
            best_loss = entry["eval_loss"]
    return best_loss


def get_checkpoint_info(ckpts: List[Path]) -> List[Dict]:
    """Return enriched info dicts for each checkpoint."""
    infos = []
    for ckpt in ckpts:
        step     = _step_from_name(ckpt.name)
        ev_loss  = get_eval_loss(ckpt)
        state    = read_trainer_state(ckpt)
        epoch    = None
        if state and state.get("log_history"):
            # Last log entry at or before this step
            for entry in reversed(state.get("log_history", [])):
                if entry.get("step", 0) <= step:
                    epoch = entry.get("epoch")
                    break

        size_mb = sum(f.stat().st_size for f in ckpt.rglob("*") if f.is_file()) / 1e6

        infos.append({
            "path":      ckpt,
            "name":      ckpt.name,
            "step":      step,
            "epoch":     epoch,
            "eval_loss": ev_loss,
            "size_mb":   size_mb,
        })
    return infos


# ─────────────────────────────────────────────────────────────────────────────
# BEST CHECKPOINT SELECTION
# ─────────────────────────────────────────────────────────────────────────────

def find_best(infos: List[Dict]) -> Optional[Dict]:
    """
    Return the checkpoint info with the lowest eval_loss.
    Falls back to the latest step if no eval_loss is recorded anywhere.
    """
    with_loss = [i for i in infos if i["eval_loss"] is not None]
    if with_loss:
        return min(with_loss, key=lambda x: x["eval_loss"])
    # Fallback: return the latest checkpoint
    return infos[-1] if infos else None


def find_latest(infos: List[Dict]) -> Optional[Dict]:
    """Return the most recent checkpoint (highest step)."""
    return infos[-1] if infos else None


# ─────────────────────────────────────────────────────────────────────────────
# DISPLAY
# ─────────────────────────────────────────────────────────────────────────────

def print_checkpoint_table(infos: List[Dict], best: Optional[Dict]) -> None:
    """Pretty-print the checkpoint table with the best one highlighted."""
    if not infos:
        print("  No checkpoints found.")
        return

    print(f"\n{'=' * 74}")
    print(f"  Checkpoint Directory: {infos[0]['path'].parent}")
    print(f"  Total checkpoints   : {len(infos)}")
    print(f"{'─' * 74}")
    print(f"  {'Checkpoint':<22}  {'Step':>6}  {'Epoch':>6}  "
          f"{'eval_loss':>10}  {'Size(MB)':>9}  {'':>4}")
    print(f"{'─' * 74}")

    for info in infos:
        is_best = best and info["name"] == best["name"]
        marker  = " <-- BEST" if is_best else ""
        epoch   = f"{info['epoch']:.2f}" if info["epoch"] is not None else "  N/A"
        loss    = f"{info['eval_loss']:.6f}" if info["eval_loss"] is not None else "      N/A"
        print(
            f"  {info['name']:<22}  {info['step']:>6,}  {epoch:>6}  "
            f"{loss:>10}  {info['size_mb']:>8.1f}  {marker}"
        )

    print(f"{'─' * 74}")
    if best:
        print(f"  Best checkpoint : {best['name']}  "
              f"(eval_loss = {best['eval_loss']:.6f})" if best["eval_loss"] else
              f"  Best checkpoint : {best['name']}  (fallback to latest)")
    print(f"{'=' * 74}\n")


# ─────────────────────────────────────────────────────────────────────────────
# EXPORT
# ─────────────────────────────────────────────────────────────────────────────

def export_best(best: Dict, export_dir: Path, dry_run: bool = False) -> None:
    """
    Copy the best checkpoint to a clean export directory.
    Writes adapter_manifest.json alongside the adapter files so that
    generate_patches.py and merge_adapter.py can read provenance metadata.
    """
    import time as _time
    src = best["path"]

    if dry_run:
        logger.info(f"[DRY-RUN] Would copy {src} -> {export_dir}")
        logger.info(f"[DRY-RUN] Would write adapter_manifest.json")
        return

    if export_dir.exists():
        logger.info(f"Removing existing export dir: {export_dir}")
        shutil.rmtree(export_dir)

    logger.info(f"Copying {src} -> {export_dir}")
    shutil.copytree(src, export_dir)

    # Write a rich manifest file (Task 8.1)
    # This is read by generate_patches.py and merge_adapter.py
    manifest = {
        "schema_version":    "1.0",
        "exported_at":       _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime()),
        "adapter_type":      "LoRA",
        "base_model":        "Qwen/Qwen2.5-Coder-3B-Instruct",
        "source_checkpoint": str(src),
        "step":              best["step"],
        "eval_loss":         best["eval_loss"],
        "epoch":             best["epoch"],
        "export_dir":        str(export_dir),
        "ready_for_inference": True,
        "ready_for_merge":     True,
    }
    manifest_path = export_dir / "adapter_manifest.json"
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    logger.info(f"Exported to {export_dir}")
    logger.info(f"  eval_loss = {best.get('eval_loss', 'N/A')}")
    logger.info(f"  Manifest  : {manifest_path}")


# ─────────────────────────────────────────────────────────────────────────────
# EARLY STOPPING AUDIT
# ─────────────────────────────────────────────────────────────────────────────

def print_early_stopping_analysis(infos: List[Dict], patience: int = 3) -> None:
    """
    Simulate the early-stopping decision over the checkpoint history.
    Shows at which step training would have halted with the given patience.
    """
    print(f"\n  Early-Stopping Simulation  (patience = {patience})")
    print(f"  {'Step':>6}  {'eval_loss':>10}  {'Delta':>10}  Action")
    print(f"  {'─' * 50}")

    losses = [(i["step"], i["eval_loss"]) for i in infos if i["eval_loss"] is not None]
    if not losses:
        print("  No eval_loss data available.")
        return

    best_loss    = losses[0][1]
    no_improve   = 0
    stopped_step = None

    for step, loss in losses:
        delta = loss - best_loss
        if loss < best_loss - 1e-4:          # meaningful improvement
            best_loss  = loss
            no_improve = 0
            action = "improved"
        else:
            no_improve += 1
            action = f"no improvement ({no_improve}/{patience})"

        if no_improve >= patience and stopped_step is None:
            stopped_step = step
            action += "  --> STOP"

        print(f"  {step:>6,}  {loss:>10.6f}  {delta:>+10.6f}  {action}")

    print()
    if stopped_step:
        print(f"  Early stopping would have triggered at step {stopped_step:,}")
    else:
        print(f"  No early stop triggered (ran to end)")
    print()


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ouroboros – Checkpoint Manager (Task 4.2)",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--ckpt-dir", type=Path, default=DEFAULT_DIR,
                        help=f"Checkpoint base directory (default: {DEFAULT_DIR})")
    parser.add_argument("--export-dir", type=Path, default=EXPORT_DIR,
                        help=f"Export destination (default: {EXPORT_DIR})")
    parser.add_argument("--list",    action="store_true",
                        help="List all checkpoints with eval_loss")
    parser.add_argument("--best",    action="store_true",
                        help="Print path of best checkpoint (lowest eval_loss)")
    parser.add_argument("--resume",  action="store_true",
                        help="Print path of latest checkpoint (for --resume-from-checkpoint)")
    parser.add_argument("--export",  action="store_true",
                        help="Copy best checkpoint to --export-dir")
    parser.add_argument("--simulate-early-stop", action="store_true",
                        help="Show what early stopping would have done")
    parser.add_argument("--patience", type=int, default=3,
                        help="Early stopping patience for simulation (default: 3)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print actions without making filesystem changes")
    return parser.parse_args()


def main():
    args = parse_args()

    logger.info("=" * 60)
    logger.info("Ouroboros -- Checkpoint Manager  (Task 4.2)")
    logger.info("=" * 60)

    ckpts = find_checkpoints(args.ckpt_dir)
    infos = get_checkpoint_info(ckpts)
    best  = find_best(infos)
    latest = find_latest(infos)

    if not ckpts:
        logger.warning(
            f"No checkpoints found in {args.ckpt_dir}\n"
            "  This directory is created during training.\n"
            "  Run:  python scripts/fine_tune_models.py  to start training."
        )
        # Print expected structure as a guide
        print(f"\n  Expected checkpoint structure:")
        print(f"  {args.ckpt_dir}/")
        print(f"    checkpoint-200/   (after 200 steps)")
        print(f"    checkpoint-400/   (after 400 steps)")
        print(f"    checkpoint-600/   (after 600 steps, may be best)")
        print(f"    checkpoint-800/   ...")
        print()
        return

    if args.list or (not args.best and not args.resume and not args.export):
        print_checkpoint_table(infos, best)

    if args.simulate_early_stop:
        print_early_stopping_analysis(infos, patience=args.patience)

    if args.best:
        if best:
            print(str(best["path"]))
        else:
            logger.error("No best checkpoint found.")

    if args.resume:
        if latest:
            print(str(latest["path"]))
        else:
            logger.error("No checkpoint to resume from.")

    if args.export:
        if best:
            export_best(best, args.export_dir, dry_run=args.dry_run)
        else:
            logger.error("No checkpoint to export.")


if __name__ == "__main__":
    main()
