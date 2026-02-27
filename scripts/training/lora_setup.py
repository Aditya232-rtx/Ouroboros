"""
Ouroboros AI - LoRA Setup & Validation  (Task 3.1)
===================================================
Loads `config/lora_config.yaml`, constructs the PEFT LoraConfig, and
optionally displays a parameter breakdown table.

This module is imported by the training script; it can also be run
standalone to validate configuration and print stats.

Usage
-----
  # Validate config and print parameter counts
  python scripts/training/lora_setup.py

  # Use an experiment preset (r=32, alpha=64)
  python scripts/training/lora_setup.py --preset balanced

  # Validate a custom r/alpha override
  python scripts/training/lora_setup.py --r 32 --alpha 64
"""

import argparse
import json
import logging
import math
import sys
from pathlib import Path
from typing import Dict, Optional

# ── Compatibility shim: tolerate missing optional deps ────────────────────────
try:
    import yaml  # type: ignore
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

try:
    from peft import LoraConfig, TaskType  # type: ignore
    _HAS_PEFT = True
except ImportError:
    _HAS_PEFT = False

try:
    import torch  # type: ignore
    _HAS_TORCH = True
except ImportError:
    _HAS_TORCH = False

# Force UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("lora_setup")

CONFIG_PATH = Path("config/lora_config.yaml")

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG LOADER
# ─────────────────────────────────────────────────────────────────────────────

def load_config(path: Path = CONFIG_PATH) -> Dict:
    """Load and return the YAML config as a plain dict."""
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path.resolve()}")

    if _HAS_YAML:
        with path.open(encoding="utf-8") as f:
            return yaml.safe_load(f)
    else:
        # Minimal YAML parser fallback (handles key: value lines only)
        logger.warning("PyYAML not installed — using minimal YAML parser. "
                       "Run: pip install pyyaml")
        config: Dict = {}
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.rstrip()
                if line.startswith("#") or not line.strip():
                    continue
                if ": " in line and not line.startswith("  "):
                    k, _, v = line.partition(": ")
                    config[k.strip()] = v.strip()
        return config


def apply_preset(config: Dict, preset_name: str) -> Dict:
    """Override lora section with a named experiment preset."""
    presets = config.get("experiments", {})
    if preset_name not in presets:
        available = list(presets.keys())
        raise ValueError(
            f"Unknown preset '{preset_name}'. Available: {available}"
        )
    preset = presets[preset_name]
    logger.info(f"Applying preset '{preset_name}': {preset.get('description', '')}")
    merged = dict(config)
    merged["lora"] = {**config.get("lora", {}), **{k: v for k, v in preset.items() if k != "description"}}
    return merged


# ─────────────────────────────────────────────────────────────────────────────
# LORA CONFIG FACTORY
# ─────────────────────────────────────────────────────────────────────────────

# Qwen2.5 attention and MLP layer names
QWEN_ATTENTION_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj"]
QWEN_MLP_MODULES       = ["gate_proj", "up_proj", "down_proj"]


def build_lora_config(config: Dict) -> Optional[object]:
    """
    Construct and return a PEFT LoraConfig from the loaded YAML dict.
    Returns None if PEFT is not installed (prints instructions).
    """
    lora_cfg  = config.get("lora", {})
    r         = int(lora_cfg.get("r", 16))
    alpha     = int(lora_cfg.get("alpha", 32))
    dropout   = float(lora_cfg.get("dropout", 0.05))
    bias      = str(lora_cfg.get("bias", "none"))
    target    = lora_cfg.get("target_modules", QWEN_ATTENTION_MODULES)
    use_rslora = bool(lora_cfg.get("use_rslora", False))

    if not _HAS_PEFT:
        logger.error(
            "PEFT library not installed. Install with:\n"
            "  pip install peft\n"
            "  # or for full training:\n"
            "  pip install peft transformers accelerate bitsandbytes"
        )
        return None

    lora_config = LoraConfig(
        r                = r,
        lora_alpha       = alpha,
        target_modules   = target,
        lora_dropout     = dropout,
        bias             = bias,
        task_type        = TaskType.CAUSAL_LM,
        inference_mode   = False,
        use_rslora       = use_rslora,
    )
    return lora_config


# ─────────────────────────────────────────────────────────────────────────────
# PARAMETER ESTIMATOR
# ─────────────────────────────────────────────────────────────────────────────

# Qwen2.5-Coder-3B architecture constants
# Source: HuggingFace model card + config.json
QWEN_3B_ARCH = {
    "num_layers":       36,
    "hidden_size":      2048,
    "num_heads":        16,
    "num_kv_heads":     8,          # GQA: 8 KV heads, 16 Q heads
    "head_dim":         128,
    "intermediate_size": 11008,     # MLP intermediate
    "total_params_M":  3090,        # Million params (non-embedding)
}

def estimate_trainable_params(config: Dict) -> Dict:
    """
    Estimate the number of trainable LoRA parameters for Qwen2.5-Coder-3B.

    For each targeted module, a LoRA adapter adds:
      A matrix: (in_features × r)   — down-projection
      B matrix: (r × out_features)  — up-projection

    Total per module = r × (in_features + out_features)
    """
    lora     = config.get("lora", {})
    r        = int(lora.get("r", 16))
    targets  = lora.get("target_modules", QWEN_ATTENTION_MODULES)
    arch     = QWEN_3B_ARCH
    layers   = arch["num_layers"]
    d        = arch["hidden_size"]          # 2048
    h        = arch["head_dim"]             # 128
    n_q      = arch["num_heads"]            # 16 heads
    n_kv     = arch["num_kv_heads"]         # 8 kv heads
    inter    = arch["intermediate_size"]    # 11008

    # Projection shapes for Qwen2.5 (GQA aware)
    SHAPES = {
        "q_proj":    (d, n_q * h),          # 2048 → 2048
        "k_proj":    (d, n_kv * h),         # 2048 → 1024
        "v_proj":    (d, n_kv * h),         # 2048 → 1024
        "o_proj":    (n_q * h, d),          # 2048 → 2048
        "gate_proj": (d, inter),            # 2048 → 11008
        "up_proj":   (d, inter),            # 2048 → 11008
        "down_proj": (inter, d),            # 11008 → 2048
    }

    breakdown = []
    total = 0
    for mod in targets:
        if mod not in SHAPES:
            logger.warning(f"Unknown module '{mod}' — skipping estimate")
            continue
        in_f, out_f = SHAPES[mod]
        params_per_layer = r * (in_f + out_f)
        params_total     = params_per_layer * layers
        total           += params_total
        breakdown.append({
            "module":          mod,
            "shape":           f"({in_f}, {out_f})",
            "params_per_layer": params_per_layer,
            "layers":          layers,
            "total_params":    params_total,
        })

    base_total_M = arch["total_params_M"]
    pct = total / (base_total_M * 1e6) * 100

    return {
        "r":           r,
        "breakdown":   breakdown,
        "total":       total,
        "total_M":     total / 1e6,
        "base_M":      base_total_M,
        "pct_of_base": pct,
    }


def print_param_table(stats: Dict) -> None:
    """Pretty-print the trainable parameter breakdown."""
    r = stats["r"]
    print(f"\n{'=' * 72}")
    print(f"  LoRA Parameter Breakdown  |  r = {r}  |  Qwen2.5-Coder-3B")
    print(f"{'─' * 72}")
    print(f"  {'Module':<12}  {'Shape':<18}  {'Per Layer':>12}  {'Layers':>6}  {'Total':>12}")
    print(f"{'─' * 72}")
    for row in stats["breakdown"]:
        print(
            f"  {row['module']:<12}  {row['shape']:<18}  "
            f"{row['params_per_layer']:>12,}  {row['layers']:>6}  "
            f"{row['total_params']:>12,}"
        )
    print(f"{'─' * 72}")
    print(f"  {'TOTAL TRAINABLE':<12}  {'':18}  {'':12}  {'':6}  {stats['total']:>12,}")
    print(f"  {'= ':<12}  {stats['total_M']:.2f}M params  /  "
          f"{stats['base_M']:,}M base  ({stats['pct_of_base']:.2f}% of model)")
    print(f"{'=' * 72}\n")


def print_config_summary(config: Dict, stats: Dict) -> None:
    """Print a readable summary of the full LoRA config."""
    lora    = config.get("lora", {})
    qlora   = config.get("qlora", {})
    train   = config.get("training", {})
    model   = config.get("model", {})

    print(f"\n{'═' * 55}")
    print(f"  Ouroboros LoRA Configuration Summary")
    print(f"{'═' * 55}")
    print(f"  Base model     : {model.get('name', 'N/A')}")
    print(f"  dtype          : {model.get('dtype', 'bfloat16')}")
    print()
    print(f"  ── LoRA ──────────────────────────────────────────")
    print(f"  r (rank)       : {lora.get('r', 16)}")
    print(f"  alpha          : {lora.get('alpha', 32)}")
    print(f"  alpha/r ratio  : {int(lora.get('alpha', 32)) / int(lora.get('r', 16)):.1f}x  "
          f"({'recommended' if int(lora.get('alpha', 32)) / int(lora.get('r', 16)) == 2 else 'non-standard'})")
    print(f"  dropout        : {lora.get('dropout', 0.05)}")
    print(f"  bias           : {lora.get('bias', 'none')}")
    print(f"  target_modules : {lora.get('target_modules', [])}")
    print(f"  use_rslora     : {lora.get('use_rslora', False)}")
    print()
    print(f"  ── Trainable parameters ──────────────────────────")
    print(f"  Total          : {stats['total']:,}  ({stats['total_M']:.2f}M)")
    print(f"  % of model     : {stats['pct_of_base']:.2f}%")
    print()
    print(f"  ── QLoRA ─────────────────────────────────────────")
    print(f"  enabled        : {qlora.get('enabled', False)}")
    print(f"  4-bit quant    : {qlora.get('load_in_4bit', False)}")
    print(f"  quant type     : {qlora.get('bnb_4bit_quant_type', 'nf4')}")
    print(f"  double quant   : {qlora.get('bnb_4bit_use_double_quant', True)}")
    print()
    print(f"  ── Training ──────────────────────────────────────")
    print(f"  epochs         : {train.get('num_train_epochs', 3)}")
    print(f"  lr             : {train.get('learning_rate', 2e-4)}")
    print(f"  scheduler      : {train.get('lr_scheduler_type', 'cosine')}")
    eff_batch = (int(train.get("per_device_train_batch_size", 4)) *
                 int(train.get("gradient_accumulation_steps", 4)))
    print(f"  eff. batch     : {eff_batch}  "
          f"({train.get('per_device_train_batch_size', 4)} × "
          f"{train.get('gradient_accumulation_steps', 4)} accum)")
    print(f"  output_dir     : {train.get('output_dir', 'N/A')}")
    print(f"{'═' * 55}\n")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ouroboros – LoRA Setup & Validation (Task 3.1)",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--config", type=Path, default=CONFIG_PATH,
                        help="Path to lora_config.yaml")
    parser.add_argument("--preset", type=str, default=None,
                        help="Experiment preset: conservative | balanced | "
                             "high_rank | ablation_low")
    parser.add_argument("--r",     type=int, default=None, help="Override LoRA rank r")
    parser.add_argument("--alpha", type=int, default=None, help="Override LoRA alpha")
    parser.add_argument("--json-out", action="store_true",
                        help="Emit config summary as JSON (useful for CI)")
    return parser.parse_args()


def main():
    args = parse_args()

    logger.info("═" * 55)
    logger.info("Ouroboros — LoRA Setup & Validation  (Task 3.1)")
    logger.info("═" * 55)

    # Load config
    config = load_config(args.config)

    # Apply preset or CLI overrides
    if args.preset:
        config = apply_preset(config, args.preset)
    if args.r is not None:
        config.setdefault("lora", {})["r"] = args.r
    if args.alpha is not None:
        config.setdefault("lora", {})["alpha"] = args.alpha

    # Parameter estimate
    stats = estimate_trainable_params(config)

    # Print
    if args.json_out:
        summary = {
            "r":               config["lora"]["r"],
            "alpha":           config["lora"]["alpha"],
            "target_modules":  config["lora"].get("target_modules"),
            "trainable_M":     round(stats["total_M"], 3),
            "pct_of_base":     round(stats["pct_of_base"], 3),
        }
        print(json.dumps(summary, indent=2))
    else:
        print_config_summary(config, stats)
        print_param_table(stats)

    # Build PEFT config (validates PEFT is installed)
    lora_config = build_lora_config(config)
    if lora_config is not None:
        logger.info("✅ LoraConfig object constructed successfully via PEFT.")

    return config, lora_config


if __name__ == "__main__":
    main()
