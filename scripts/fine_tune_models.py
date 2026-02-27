"""
Ouroboros AI - Fine-Tuning Entry Point  (Tasks 7.1 / 7.2 / 7.3)
=================================================================
Thin CLI wrapper around scripts/training/train.py.
Forwards ALL arguments directly to train.py, so every flag defined
there works here too.

Production launch command
--------------------------
  .\\venv\\Scripts\\python.exe scripts/fine_tune_models.py --preset reg_moderate

All supported flags
--------------------
  --preset   {conservative, balanced, high_rank, ablation_low, reg_light, reg_moderate}
  --config   PATH            Path to lora_config.yaml
  --lr       FLOAT           Override learning rate
  --patience INT             Early stopping patience (Task 4.1)
  --no-early-stop            Disable early stopping
  --resume-from-checkpoint   PATH|auto   Resume interrupted run (Task 4.2)
  --dry-run                  Validate config only, no training
  --sweep                    Print LR sweep table

Pre-flight usage (recommended before every full run)
------------------------------------------------------
  # 1. Run environment checks
  .\\venv\\Scripts\\python.exe scripts/training/preflight_check.py

  # 2. Run dataset sanity check
  .\\venv\\Scripts\\python.exe scripts/data_preparation/dataset_sanity_check.py

  # 3. Clear stale cache
  .\\venv\\Scripts\\python.exe scripts/utils/clear_cache.py --dry-run

  # 4. Launch training (in terminal A)
  .\\venv\\Scripts\\python.exe scripts/fine_tune_models.py --preset reg_moderate

  # 5. Watch loss live (in terminal B while training runs)
  .\\venv\\Scripts\\python.exe scripts/training/loss_monitor.py

  # 6. After training — inspect best checkpoint
  .\\venv\\Scripts\\python.exe scripts/training/checkpoint_manager.py --list
  .\\venv\\Scripts\\python.exe scripts/training/checkpoint_manager.py --export
"""

import sys
import subprocess
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def main():
    import os
    os.environ["HF_HOME"] = "D:\\huggingface_cache"
    train_script = Path(__file__).parent / "training" / "train.py"

    if not train_script.exists():
        print(f"ERROR: training script not found at {train_script}", file=sys.stderr)
        sys.exit(1)

    cmd = [sys.executable, str(train_script)] + sys.argv[1:]
    result = subprocess.run(cmd, check=False)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
