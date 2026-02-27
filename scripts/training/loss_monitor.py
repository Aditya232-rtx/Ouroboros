"""
Ouroboros AI - Live Loss Monitor  (Task 7.2 / 7.3)
====================================================
Watches the active training run by tailing trainer_state.json inside
the checkpoint directory. Prints a live ASCII loss curve and tracks
EarlyStoppingCallback patience progress.

What it watches
---------------
  HuggingFace Trainer writes  <output_dir>/trainer_state.json  after every
  evaluation step. This file contains log_history with all train_loss and
  eval_loss entries. The monitor polls this file every --interval seconds.

Display features
----------------
  - ASCII sparkline for train_loss and eval_loss over time
  - Current step / epoch / elapsed time
  - Early stopping patience counter (green → yellow → red)
  - "HALTED BY EARLY STOPPING" banner detection
  - Diff between last two eval_loss values (improving / degrading)

Usage
-----
  # Start monitor in a second terminal while training is running
  python scripts/training/loss_monitor.py

  # Custom output dir and refresh rate
  python scripts/training/loss_monitor.py --output-dir models/my-run --interval 15

  # One-shot (no loop, just print current state)
  python scripts/training/loss_monitor.py --once

  # Replay a completed run from saved trainer_state.json
  python scripts/training/loss_monitor.py --replay models/ouroboros-blue-lora/trainer_state.json
"""

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT       = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = ROOT / "models" / "ouroboros-blue-lora"

# ANSI colour codes (fallback to empty strings on non-colour terminals)
def _ansi(code: str) -> str:
    if os.environ.get("NO_COLOR") or not sys.stdout.isatty():
        return ""
    return f"\033[{code}m"

RESET  = _ansi("0")
GREEN  = _ansi("32")
YELLOW = _ansi("33")
RED    = _ansi("31")
CYAN   = _ansi("36")
BOLD   = _ansi("1")
DIM    = _ansi("2")


# ─────────────────────────────────────────────────────────────────────────────
# TRAINER STATE READER
# ─────────────────────────────────────────────────────────────────────────────

def find_trainer_state(output_dir: Path) -> Optional[Path]:
    """
    Find the most-recently-modified trainer_state.json under output_dir.
    Checks both the root (final state) and inside checkpoint-* subdirs.
    """
    candidates = list(output_dir.glob("trainer_state.json"))
    candidates += list(output_dir.glob("checkpoint-*/trainer_state.json"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def load_trainer_state(path: Path) -> Optional[Dict]:
    # Use utf-8-sig to automatically strip BOM if present
    # (PowerShell Out-File -Encoding UTF8 adds a BOM)
    for enc in ("utf-8-sig", "utf-8"):
        try:
            with path.open(encoding=enc) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
    return None


# ─────────────────────────────────────────────────────────────────────────────
# LOG HISTORY PARSING
# ─────────────────────────────────────────────────────────────────────────────

def parse_log_history(log_history: List[Dict]) -> Tuple[List, List]:
    """
    Split log_history into:
      train_entries: [{step, epoch, loss, learning_rate}]
      eval_entries:  [{step, epoch, eval_loss, eval_runtime}]
    """
    train_entries = []
    eval_entries  = []
    for entry in log_history:
        if "loss" in entry and "eval_loss" not in entry:
            train_entries.append({
                "step":          entry.get("step", 0),
                "epoch":         entry.get("epoch", 0),
                "loss":          entry.get("loss", None),
                "learning_rate": entry.get("learning_rate", None),
            })
        if "eval_loss" in entry:
            eval_entries.append({
                "step":         entry.get("step", 0),
                "epoch":        entry.get("epoch", 0),
                "eval_loss":    entry.get("eval_loss", None),
                "eval_runtime": entry.get("eval_runtime", None),
            })
    return train_entries, eval_entries


# ─────────────────────────────────────────────────────────────────────────────
# ASCII SPARKLINE
# ─────────────────────────────────────────────────────────────────────────────

SPARK_CHARS = " ▁▂▃▄▅▆▇█"

def sparkline(values: List[float], width: int = 40) -> str:
    """Render a list of float values as an ASCII sparkline of given width."""
    if not values:
        return " " * width
    # Sample down to `width` points
    if len(values) > width:
        step  = len(values) / width
        sampled = [values[int(i * step)] for i in range(width)]
    else:
        sampled = values + [values[-1]] * (width - len(values))

    mn, mx = min(sampled), max(sampled)
    rng    = mx - mn if mx != mn else 1.0
    chars  = []
    for v in sampled:
        idx = int((v - mn) / rng * (len(SPARK_CHARS) - 1))
        chars.append(SPARK_CHARS[idx])
    return "".join(chars)


# ─────────────────────────────────────────────────────────────────────────────
# EARLY STOPPING TRACKER
# ─────────────────────────────────────────────────────────────────────────────

def compute_early_stopping_state(
    eval_entries: List[Dict],
    patience: int = 3,
    threshold: float = 1e-4,
) -> Dict:
    """
    Simulate EarlyStoppingCallback logic over eval history.
    Returns dict with: best_loss, best_step, no_improve_count, would_stop, stop_step
    """
    if not eval_entries:
        return {
            "best_loss": None, "best_step": None,
            "no_improve_count": 0, "would_stop": False,
            "stop_step": None, "patience": patience,
        }

    best_loss       = eval_entries[0]["eval_loss"]
    best_step       = eval_entries[0]["step"]
    no_improve      = 0
    stop_step       = None

    for entry in eval_entries[1:]:
        loss = entry.get("eval_loss")
        if loss is None:
            continue
        if loss < best_loss - threshold:
            best_loss  = loss
            best_step  = entry["step"]
            no_improve = 0
        else:
            no_improve += 1
            if no_improve >= patience and stop_step is None:
                stop_step = entry["step"]

    return {
        "best_loss":        best_loss,
        "best_step":        best_step,
        "no_improve_count": no_improve,
        "would_stop":       stop_step is not None,
        "stop_step":        stop_step,
        "patience":         patience,
    }


# ─────────────────────────────────────────────────────────────────────────────
# DISPLAY
# ─────────────────────────────────────────────────────────────────────────────

def patience_bar(count: int, patience: int) -> str:
    """Render a colour-coded patience progress bar."""
    ratio = count / patience if patience > 0 else 0
    if ratio >= 1.0:
        colour = RED
    elif ratio >= 0.67:
        colour = YELLOW
    else:
        colour = GREEN

    filled = min(count, patience)
    empty  = max(patience - filled, 0)
    bar    = "[" + ("█" * filled) + ("░" * empty) + "]"
    return f"{colour}{bar}{RESET}  {count}/{patience}"


def format_loss_delta(prev: Optional[float], curr: float) -> str:
    if prev is None:
        return ""
    delta = curr - prev
    if delta < -1e-4:
        return f"  {GREEN}▼ {abs(delta):.6f}{RESET}"
    elif delta > 1e-4:
        return f"  {RED}▲ {abs(delta):.6f}{RESET}"
    else:
        return f"  {DIM}~ {abs(delta):.6f}{RESET}"


def render_display(
    state:         Dict,
    train_entries: List[Dict],
    eval_entries:  List[Dict],
    es_state:      Dict,
    state_path:    Path,
    total_steps:   int,
) -> str:
    lines = []
    W = 70

    def hr(c="─"): return c * W

    lines.append(f"\n{BOLD}{CYAN}{'=' * W}{RESET}")
    lines.append(f"  {BOLD}OUROBOROS  LIVE LOSS MONITOR{RESET}  "
                 f"(Tasks 7.2 / 7.3)  {DIM}{time.strftime('%H:%M:%S')}{RESET}")
    lines.append(hr())

    # Training progress
    cur_step  = state.get("global_step", 0)
    cur_epoch = state.get("epoch", 0.0)
    pct       = (cur_step / total_steps * 100) if total_steps > 0 else 0
    bar_width = 30
    filled    = int(bar_width * pct / 100)
    prog_bar  = f"{GREEN}{'█' * filled}{DIM}{'░' * (bar_width - filled)}{RESET}"
    lines.append(
        f"  Progress  {prog_bar}  "
        f"{cur_step:,} / {total_steps:,} steps  "
        f"epoch {cur_epoch:.2f}  ({pct:.1f}%)"
    )
    lines.append(hr())

    # Latest train loss
    if train_entries:
        last_t = train_entries[-1]
        prev_t = train_entries[-2]["loss"] if len(train_entries) > 1 else None
        delta  = format_loss_delta(prev_t, last_t["loss"])
        lr_str = f"  lr={last_t['learning_rate']:.2e}" if last_t.get("learning_rate") else ""
        lines.append(
            f"  Train loss  : {BOLD}{last_t['loss']:.6f}{RESET}{delta}{lr_str}"
        )

    # Latest eval loss
    if eval_entries:
        last_e   = eval_entries[-1]
        prev_e   = eval_entries[-2]["eval_loss"] if len(eval_entries) > 1 else None
        delta_e  = format_loss_delta(prev_e, last_e["eval_loss"])
        lines.append(
            f"  Eval  loss  : {BOLD}{last_e['eval_loss']:.6f}{RESET}{delta_e}"
        )
        if es_state["best_loss"] is not None:
            lines.append(
                f"  Best eval   : {GREEN}{es_state['best_loss']:.6f}{RESET}"
                f"  @ step {es_state['best_step']:,}"
            )
    lines.append(hr())

    # Sparklines
    train_losses = [e["loss"] for e in train_entries if e.get("loss") is not None]
    eval_losses  = [e["eval_loss"] for e in eval_entries if e.get("eval_loss") is not None]

    if train_losses:
        spark = sparkline(train_losses, width=W - 16)
        lines.append(f"  train_loss  {DIM}{spark}{RESET}")
    if eval_losses:
        spark = sparkline(eval_losses, width=W - 16)
        lines.append(f"  eval_loss   {DIM}{spark}{RESET}")
    if train_losses or eval_losses:
        lines.append(hr())

    # Early stopping panel
    es = es_state
    lines.append(f"  {BOLD}Early Stopping{RESET}  (patience={es['patience']})")
    lines.append(
        f"  Patience bar  : {patience_bar(es['no_improve_count'], es['patience'])}"
    )

    if es["would_stop"]:
        lines.append(f"\n  {RED}{BOLD}{'!' * W}{RESET}")
        lines.append(f"  {RED}{BOLD}  TRAINING HALTED BY EARLY STOPPING "
                     f"at step {es['stop_step']:,}{RESET}")
        lines.append(f"  {RED}{BOLD}{'!' * W}{RESET}")
        lines.append(f"  Best checkpoint → {GREEN}checkpoint-{es['best_step']}{RESET}")
        lines.append(f"  Run: python scripts/training/checkpoint_manager.py --best")
    elif es["no_improve_count"] == 0:
        lines.append(f"  Status : {GREEN}IMPROVING — loss is decreasing{RESET}")
    elif es["no_improve_count"] < es["patience"]:
        lines.append(
            f"  Status : {YELLOW}STAGNATING — {es['patience'] - es['no_improve_count']} "
            f"eval(s) before early stop{RESET}"
        )
    else:
        lines.append(f"  Status : {RED}PATIENCE EXHAUSTED (stop imminent){RESET}")

    lines.append(hr())
    lines.append(f"  Watching : {DIM}{state_path}{RESET}")
    lines.append(f"{BOLD}{CYAN}{'=' * W}{RESET}\n")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# MONITOR LOOP
# ─────────────────────────────────────────────────────────────────────────────

def run_monitor(
    output_dir:  Path,
    interval:    int,
    once:        bool,
    replay_path: Optional[Path],
    patience:    int,
    threshold:   float,
) -> None:
    print(f"  Watching: {output_dir}")
    print(f"  Refresh : every {interval}s  (Ctrl+C to quit)\n")

    last_mtime = 0.0

    while True:
        # Locate the trainer_state.json
        if replay_path:
            state_path = replay_path
        else:
            state_path = find_trainer_state(output_dir)

        if not state_path or not state_path.exists():
            print(f"  {YELLOW}Waiting for training to start...{RESET}  "
                  f"(no trainer_state.json yet in {output_dir})")
            if once:
                break
            time.sleep(interval)
            continue

        # Only re-render if file changed
        try:
            mtime = state_path.stat().st_mtime
        except OSError:
            mtime = 0.0

        if mtime == last_mtime and not once:
            time.sleep(interval)
            continue
        last_mtime = mtime

        state = load_trainer_state(state_path)
        if not state:
            time.sleep(interval)
            continue

        log_history  = state.get("log_history", [])
        train_entries, eval_entries = parse_log_history(log_history)
        es_state     = compute_early_stopping_state(eval_entries, patience, threshold)
        total_steps  = state.get("max_steps", 0)

        # Clear screen between refreshes (skip in once/replay mode)
        if not once and not replay_path:
            print("\033[2J\033[H", end="")

        display = render_display(
            state, train_entries, eval_entries, es_state, state_path, total_steps
        )
        print(display)

        if once or replay_path:
            break

        # Exit when training done
        if es_state["would_stop"] or state.get("global_step", 0) >= total_steps > 0:
            print("  Training completed. Monitor exiting.")
            break

        time.sleep(interval)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Ouroboros - Live Loss Monitor (Tasks 7.2 / 7.3)",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR,
                        help=f"Training output dir (default: {OUTPUT_DIR})")
    parser.add_argument("--interval",   type=int,  default=10,
                        help="Refresh interval in seconds (default: 10)")
    parser.add_argument("--once",       action="store_true",
                        help="Print current state once and exit")
    parser.add_argument("--replay",     type=Path,  default=None,
                        metavar="PATH",
                        help="Replay a saved trainer_state.json (implies --once)")
    parser.add_argument("--patience",   type=int,  default=3,
                        help="Early stopping patience to simulate (default: 3)")
    parser.add_argument("--threshold",  type=float, default=1e-4,
                        help="Early stopping threshold (default: 1e-4)")
    return parser.parse_args()


def main():
    args = parse_args()
    print(f"\n{'=' * 70}")
    print("  Ouroboros -- Live Loss Monitor  (Tasks 7.2 / 7.3)")
    print(f"{'=' * 70}")
    run_monitor(
        output_dir  = args.output_dir,
        interval    = args.interval,
        once        = args.once,
        replay_path = args.replay,
        patience    = args.patience,
        threshold   = args.threshold,
    )


if __name__ == "__main__":
    main()
