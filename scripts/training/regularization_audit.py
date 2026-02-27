"""
Ouroboros AI - Regularization Audit & Comparison  (Task 3.3)
=============================================================
Standalone tool that validates, compares, and explains the regularization
strategy used during LoRA fine-tuning of Qwen2.5-Coder-3B.

Two regularization mechanisms work together to combat overfitting:

  1. LoRA Dropout  (lora.dropout)
     ─────────────────────────────
     Applied *inside* each adapter layer (after the A down-projection,
     before the B up-projection).  During training, each activation is
     randomly zeroed with probability `dropout`, forcing the adapter
     to learn redundant, distributed representations.

     Dropout = 0.05  →  5% of adapter activations are zeroed per forward pass
     Dropout = 0.10  →  10% are zeroed

  2. Weight Decay  (training.weight_decay)
     ─────────────────────────────────────
     Applied by the AdamW optimiser as a decoupled L2 penalty:

       θ ← θ - lr × (grad + weight_decay × θ)

     This penalises large adapter weights, pulling them toward zero.
     Weight decay = 0.01 means 1% of the current weight is subtracted
     on top of the gradient step each iteration.

Usage
-----
  # Print audit for default config
  python scripts/training/regularization_audit.py

  # Compare all presets
  python scripts/training/regularization_audit.py --compare

  # Show overfitting risk estimate for a specific dataset size
  python scripts/training/regularization_audit.py --n-train 500

  # Validate a custom dropout/wd combination
  python scripts/training/regularization_audit.py --dropout 0.10 --wd 0.05
"""

import argparse
import math
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("regularization_audit")

try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

ROOT        = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = ROOT / "config" / "lora_config.yaml"


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG LOADER
# ─────────────────────────────────────────────────────────────────────────────

def load_config(path: Path = CONFIG_PATH) -> Dict:
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    if not _HAS_YAML:
        raise ImportError("pip install pyyaml")
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


# ─────────────────────────────────────────────────────────────────────────────
# REGULARIZATION PARAMETERS
# ─────────────────────────────────────────────────────────────────────────────

def extract_reg_params(config: Dict) -> Dict:
    """Pull all regularization-relevant values from the config."""
    lora   = config.get("lora", {})
    train  = config.get("training", {})
    return {
        "dropout":        float(lora.get("dropout", 0.05)),
        "weight_decay":   float(train.get("weight_decay", 0.01)),
        "max_grad_norm":  float(train.get("max_grad_norm", 1.0)),
        "warmup_ratio":   float(train.get("warmup_ratio", 0.05)),
        "r":              int(lora.get("r", 16)),
        "alpha":          int(lora.get("alpha", 32)),
    }


# ─────────────────────────────────────────────────────────────────────────────
# OVERFITTING RISK ESTIMATOR
# ─────────────────────────────────────────────────────────────────────────────

def overfitting_risk_score(
    n_train: int,
    dropout: float,
    weight_decay: float,
    r: int,
    epochs: int = 3,
) -> float:
    """
    Heuristic overfitting risk score in [0, 1].

    Factors:
      - More trainable params per sample → higher risk
      - More epochs → higher risk
      - Higher dropout → lower risk
      - Higher weight_decay → lower risk

    This is a rough guide, NOT a statistical guarantee.
    """
    # Trainable params (rough: 4 attention modules × 2 matrices × hidden × r × 36 layers)
    trainable_params = 4 * 2 * 2048 * r * 36
    params_per_sample = trainable_params / max(1, n_train)

    # Base risk from param density
    base_risk = math.tanh(params_per_sample / 50_000)

    # Epoch multiplier: more epochs → more risk
    epoch_factor = min(1.0, epochs / 5.0)

    # Regularization reduction
    dropout_reduction = dropout * 2.0          # 0.05 → 0.10 reduction, 0.10 → 0.20
    wd_reduction      = weight_decay * 1.5     # 0.01 → 0.015 reduction

    risk = base_risk * epoch_factor * (1 - dropout_reduction) * (1 - wd_reduction)
    return min(1.0, max(0.0, risk))


def risk_label(score: float) -> str:
    if score < 0.15:
        return "LOW          (high regularisation coverage)"
    elif score < 0.35:
        return "MODERATE     (reasonable, monitor val_loss)"
    elif score < 0.60:
        return "ELEVATED     (consider dropout=0.10 or more epochs with early stop)"
    else:
        return "HIGH         (strongly consider stronger regularisation)"


# ─────────────────────────────────────────────────────────────────────────────
# EFFECTIVE DROPOUT ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def expected_active_fraction(dropout: float) -> float:
    """Fraction of adapter activations that are NOT zeroed per forward pass."""
    return 1.0 - dropout


def expected_weight_decay_step(weight_decay: float, lr: float) -> str:
    """Fraction of weight magnitude subtracted per step due to L2 penalty."""
    step = weight_decay * lr
    return f"{step:.2e}  (= {weight_decay} × lr{lr:.0e})"


# ─────────────────────────────────────────────────────────────────────────────
# PRINT HELPERS
# ─────────────────────────────────────────────────────────────────────────────

PRESETS = [
    # (label, dropout, weight_decay)
    ("light   (default)", 0.05, 0.01),
    ("moderate",          0.10, 0.01),
    ("strong",            0.10, 0.05),
    ("ablation (no reg)", 0.00, 0.00),
]


def print_audit(params: Dict, n_train: int, config: Dict) -> None:
    train = config.get("training", {})
    lr    = float(train.get("learning_rate", 2e-4))

    print("\n" + "=" * 64)
    print("  Regularization Audit  —  Ouroboros LoRA (Task 3.3)")
    print("=" * 64)
    print(f"\n  Dataset size           : {n_train:,} training samples")
    print(f"\n  ── LoRA Dropout ─────────────────────────────────────────")
    print(f"  dropout                : {params['dropout']}")
    print(f"  active fraction/step   : {expected_active_fraction(params['dropout']):.0%}")
    print(f"  zeroed fraction/step   : {params['dropout']:.0%}")
    print(f"  mechanism              : applied after A-matrix, before B-matrix")
    print(f"  scope                  : adapter layers only (base model frozen)")
    print(f"\n  ── Weight Decay (AdamW L2) ──────────────────────────────")
    print(f"  weight_decay           : {params['weight_decay']}")
    print(f"  L2 subtracted/step     : {expected_weight_decay_step(params['weight_decay'], lr)}")
    print(f"  formula                : theta -= lr * (grad + wd * theta)")
    print(f"  scope                  : all non-frozen, non-bias parameters")
    print(f"\n  ── Gradient Clipping ────────────────────────────────────")
    print(f"  max_grad_norm          : {params['max_grad_norm']}")
    print(f"  prevents               : exploding gradients from noisy batches")
    print(f"\n  ── Overfitting Risk Estimate ────────────────────────────")
    risk = overfitting_risk_score(
        n_train, params["dropout"], params["weight_decay"], params["r"]
    )
    bar_len = int(risk * 30)
    bar     = "[" + "█" * bar_len + "." * (30 - bar_len) + "]"
    print(f"  risk score             : {risk:.3f}  {bar}")
    print(f"  assessment             : {risk_label(risk)}")
    print("=" * 64 + "\n")


def print_comparison(n_train: int, r: int) -> None:
    """Compare dropout/wd preset combinations side-by-side."""
    print("\n" + "=" * 78)
    print("  Regularization Preset Comparison  (Task 3.3)")
    print(f"  n_train={n_train:,}   r={r}")
    print("-" * 78)
    print(f"  {'Preset':<26}  {'dropout':>8}  {'wd':>6}  {'active%':>8}  "
          f"{'risk':>6}  Assessment")
    print("-" * 78)
    for label, do, wd in PRESETS:
        active = expected_active_fraction(do)
        risk   = overfitting_risk_score(n_train, do, wd, r)
        rlabel = risk_label(risk).split()[0]
        print(f"  {label:<26}  {do:>8.2f}  {wd:>6.3f}  "
              f"{active:>8.0%}  {risk:>6.3f}  {rlabel}")
    print("=" * 78 + "\n")
    print("  Recommendation for current dataset:")
    print(f"    n_train = {n_train:,}")
    if n_train < 5_000:
        print("    → Use  dropout=0.05, weight_decay=0.01  (light preset)")
        print("    → Monitor val_loss; if train/val gap > 0.3, switch to dropout=0.10")
    elif n_train < 50_000:
        print("    → Use  dropout=0.05 or 0.10, weight_decay=0.01  (light or moderate)")
    else:
        print("    → Use  dropout=0.10, weight_decay=0.01  (moderate preset)")
    print()


# ─────────────────────────────────────────────────────────────────────────────
# EARLY STOPPING GUIDE
# ─────────────────────────────────────────────────────────────────────────────

def print_early_stopping_guide(config: Dict) -> None:
    train = config.get("training", {})
    print("  ── Early Stopping Guide ────────────────────────────────────────")
    print(f"  eval_steps       : {train.get('eval_steps', 100)}")
    print(f"  eval_strategy    : {train.get('eval_strategy', 'steps')}")
    print(f"  load_best_model  : {train.get('load_best_model_at_end', True)}")
    print()
    print("  Interpretation of eval_loss trajectory:")
    print("  ┌───────────────────────────────────────────────────────────┐")
    print("  │ train_loss ↓  eval_loss ↓  → Good. Normal learning.      │")
    print("  │ train_loss ↓  eval_loss →  → OK.  Monitor for 2-3 evals. │")
    print("  │ train_loss ↓  eval_loss ↑  → Overfitting! Increase reg.  │")
    print("  │ train_loss →  eval_loss →  → Underfit. Lower LR or more  │")
    print("  │                              epochs.                      │")
    print("  └───────────────────────────────────────────────────────────┘")
    print()
    print("  Countermeasures when overfitting is detected:")
    print("  1. Increase  lora.dropout : 0.05 → 0.10")
    print("  2. Increase  training.weight_decay : 0.01 → 0.05")
    print("  3. Reduce    lora.r : 16 → 8  (fewer trainable params)")
    print("  4. Add more  general coding data (inject_general_coding.py)")
    print("  5. Reduce    num_train_epochs : 3 → 2")
    print()


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ouroboros – Regularization Audit (Task 3.3)",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--config",  type=Path, default=CONFIG_PATH)
    parser.add_argument("--compare", action="store_true",
                        help="Print side-by-side comparison of all presets")
    parser.add_argument("--n-train", type=int, default=None,
                        help="Dataset size override (default: from train.jsonl)")
    parser.add_argument("--dropout", type=float, default=None,
                        help="Override lora.dropout for audit")
    parser.add_argument("--wd",      type=float, default=None,
                        help="Override training.weight_decay for audit")
    parser.add_argument("--json-out", action="store_true",
                        help="Emit audit summary as JSON")
    return parser.parse_args()


def _count_train_samples(config: Dict) -> int:
    """Count lines in train.jsonl to get actual n_train."""
    root = ROOT
    data_cfg = config.get("data", {})
    train_path = root / data_cfg.get("train_file", "data/splits/train.jsonl")
    if train_path.exists():
        with train_path.open(encoding="utf-8", errors="ignore") as f:
            return sum(1 for line in f if line.strip())
    return 1_000  # fallback estimate


def main():
    args = parse_args()

    logger.info("=" * 64)
    logger.info("Ouroboros -- Regularization Audit  (Task 3.3)")
    logger.info("=" * 64)

    config = load_config(args.config)
    params = extract_reg_params(config)

    # CLI overrides
    if args.dropout is not None:
        params["dropout"] = args.dropout
    if args.wd is not None:
        params["weight_decay"] = args.wd

    # Dataset size
    n_train = args.n_train or _count_train_samples(config)

    if args.json_out:
        risk = overfitting_risk_score(
            n_train, params["dropout"], params["weight_decay"], params["r"]
        )
        print(json.dumps({
            "dropout":      params["dropout"],
            "weight_decay": params["weight_decay"],
            "max_grad_norm": params["max_grad_norm"],
            "n_train":      n_train,
            "risk_score":   round(risk, 4),
            "risk_label":   risk_label(risk).split("(")[0].strip(),
        }, indent=2))
        return

    print_audit(params, n_train, config)
    print_early_stopping_guide(config)

    if args.compare:
        print_comparison(n_train, params["r"])

    logger.info("Audit complete.")


if __name__ == "__main__":
    main()
