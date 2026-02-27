"""
Ouroboros AI - Fine-Tuning Training Script  (Tasks 3.2 / 4.1 / 4.2)
=====================================================================
Full LoRA / QLoRA fine-tuning of Qwen2.5-Coder-3B-Instruct on the
Ouroboros blue-team patching dataset.

Hyperparameter highlights
--------------------------
  learning_rate      2e-4         Low enough to prevent catastrophic forgetting
  lr_scheduler       cosine       Smooth, monotone decay after warmup
  warmup_ratio       0.05         5% of total steps → linear warm-up phase
  weight_decay       0.01         L2 regularisation
  max_grad_norm      1.0          Gradient clipping
  effective_batch    16           4 devices × 4 gradient-accumulation steps

Early stopping  (Task 4.1)
---------------------------
  EarlyStoppingCallback(patience=3, threshold=1e-4)
  Evaluates every eval_steps (default: 200). Halts automatically if
  eval_loss does not improve by ≥ threshold for 3 consecutive evaluations.
  Requires: load_best_model_at_end=True, eval_strategy="steps".

Checkpoint management  (Task 4.2)
-----------------------------------
  Checkpoints are saved at every save_steps (= eval_steps = 200).
  save_total_limit=5 keeps the 5 most recent on disk.
  load_best_model_at_end restores the best-eval checkpoint after training.
  Use checkpoint_manager.py to inspect, rank, and export the best adapter.

Usage
-----
  # Dry-run: validate config, print schedule and early-stopping plan
  python scripts/training/train.py --dry-run

  # Full training
  python scripts/training/train.py

  # Resume interrupted run
  python scripts/training/train.py --resume-from-checkpoint auto

  # Custom patience
  python scripts/training/train.py --patience 5

  # Use balanced preset
  python scripts/training/train.py --preset balanced
"""

import argparse
import io
import json
import logging
import math
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Force UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("train")

# Paths
ROOT         = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH  = ROOT / "config" / "lora_config.yaml"
SCRIPTS_DIR  = ROOT / "scripts" / "training"

# ── Optional heavy deps (graceful degrade for dry-run) ────────────────────────
try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

try:
    import torch
    _HAS_TORCH = True
except ImportError:
    _HAS_TORCH = False

try:
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
        TrainingArguments,
        EarlyStoppingCallback,          # Task 4.1
    )
    _HAS_TRANSFORMERS = True
except Exception:
    _HAS_TRANSFORMERS = False
    EarlyStoppingCallback = None        # type: ignore

try:
    from peft import LoraConfig, TaskType, get_peft_model, prepare_model_for_kbit_training
    _HAS_PEFT = True
except ImportError:
    _HAS_PEFT = False

import datasets
from datasets import Dataset
import trl
from trl import SFTTrainer, DataCollatorForCompletionOnlyLM
_HAS_DATASETS = True
_HAS_TRL = True

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG LOADER
# ─────────────────────────────────────────────────────────────────────────────

def load_config(path: Path = CONFIG_PATH) -> Dict:
    """Load lora_config.yaml, return as dict."""
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    if _HAS_YAML:
        with path.open(encoding="utf-8") as f:
            return yaml.safe_load(f)
    raise ImportError("PyYAML required: pip install pyyaml")


def merge_preset(config: Dict, preset: Optional[str]) -> Dict:
    if not preset:
        return config
    presets = config.get("experiments", {})
    if preset not in presets:
        raise ValueError(f"Unknown preset '{preset}'. Available: {list(presets)}")
    overrides = {k: v for k, v in presets[preset].items() if k != "description"}
    logger.info(f"Preset '{preset}': {presets[preset].get('description', '')}")
    config["lora"] = {**config.get("lora", {}), **overrides}
    return config


# ─────────────────────────────────────────────────────────────────────────────
# LEARNING-RATE SCHEDULE UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def cosine_lr_at_step(
    step: int,
    total_steps: int,
    peak_lr: float,
    warmup_steps: int,
    min_lr_ratio: float = 0.0,
) -> float:
    """
    Return the learning rate at `step` for a linear-warmup + cosine-decay schedule.

    Args:
        step:          Current training step (0-indexed).
        total_steps:   Total number of training steps.
        peak_lr:       Maximum / peak learning rate (after warmup).
        warmup_steps:  Number of linear warm-up steps.
        min_lr_ratio:  Fraction of peak_lr used as the cosine floor (default 0).

    Returns:
        lr (float) at the given step.
    """
    min_lr = peak_lr * min_lr_ratio

    if step < warmup_steps:
        # Linear warm-up: 0 → peak_lr
        return peak_lr * (step / max(1, warmup_steps))

    # Cosine decay: peak_lr → min_lr
    progress = (step - warmup_steps) / max(1, total_steps - warmup_steps)
    cosine   = 0.5 * (1.0 + math.cos(math.pi * progress))
    return min_lr + (peak_lr - min_lr) * cosine


def print_lr_schedule(
    peak_lr: float,
    total_steps: int,
    warmup_ratio: float,
    n_points: int = 40,
) -> None:
    """Print an ASCII visualisation of the LR schedule."""
    warmup_steps = int(total_steps * warmup_ratio)
    steps        = [int(i * total_steps / n_points) for i in range(n_points + 1)]
    lrs          = [cosine_lr_at_step(s, total_steps, peak_lr, warmup_steps) for s in steps]
    max_lr       = max(lrs)
    bar_width    = 50

    print(f"\n  LR Schedule: linear warmup ({warmup_ratio*100:.0f}%) + cosine decay")
    print(f"  Peak LR: {peak_lr:.2e}  |  Warmup steps: {warmup_steps}  |  Total: {total_steps}")
    print("  " + "─" * (bar_width + 12))
    for step, lr in zip(steps[::2], lrs[::2]):  # every other point
        bar_len = int((lr / max_lr) * bar_width)
        bar     = "▓" * bar_len
        print(f"  step {step:>6}  {lr:.2e}  |{bar}")
    print("  " + "─" * (bar_width + 12) + "\n")


def estimate_total_steps(
    n_train: int,
    batch_size: int,
    grad_accum: int,
    epochs: int,
) -> int:
    steps_per_epoch = math.ceil(n_train / (batch_size * grad_accum))
    return steps_per_epoch * epochs


# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────────────────────────────────────

def load_jsonl(path: Path) -> List[Dict]:
    entries = []
    with path.open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries


def chatml_format(entry: Dict) -> str:
    """Format a messages entry into Qwen's ChatML string."""
    parts = []
    for msg in entry.get("messages", []):
        parts.append(f"<|im_start|>{msg['role']}\n{msg['content']}<|im_end|>\n")
    parts.append("<|im_start|>assistant\n")
    return "".join(parts)


def prepare_datasets(config: Dict):
    """Load JSONL splits and return HF Dataset objects (requires datasets lib)."""
    if not _HAS_DATASETS:
        raise ImportError("pip install datasets")
    data_cfg = config.get("data", {})
    root     = ROOT

    def _load(key: str):
        path = root / data_cfg.get(key, f"data/splits/{key.split('_')[0]}.jsonl")
        entries = load_jsonl(path)
        return Dataset.from_list([{"text": chatml_format(e)} for e in entries])

    train_ds = _load("train_file")
    val_ds   = _load("val_file")
    logger.info(f"Dataset: {len(train_ds)} train | {len(val_ds)} val")
    return train_ds, val_ds


# ─────────────────────────────────────────────────────────────────────────────
# MODEL + TOKENIZER LOADING
# ─────────────────────────────────────────────────────────────────────────────

def load_model_and_tokenizer(config: Dict):
    """
    Load Qwen2.5-Coder-3B in 4-bit (QLoRA) and apply LoRA adapters.
    """
    if not _HAS_TRANSFORMERS or not _HAS_PEFT:
        raise ImportError(
            "Missing training libraries:\n"
            "  pip install transformers peft accelerate bitsandbytes"
        )

    model_cfg = config.get("model", {})
    qlora_cfg = config.get("qlora", {})
    lora_cfg  = config.get("lora", {})

    model_path = (
        os.environ.get("OUROBOROS_MODEL_PATH")
        or model_cfg.get("local_path")
        or model_cfg.get("name")
    )
    logger.info(f"Loading base model: {model_path}")

    # ── QLoRA BitsAndBytes configuration ─────────────────────────────────────
    bnb_config = None
    if qlora_cfg.get("enabled", True) and qlora_cfg.get("load_in_4bit", True):
        compute_dtype = (
            torch.bfloat16
            if model_cfg.get("dtype", "bfloat16") == "bfloat16"
            else torch.float16
        )
        bnb_config = BitsAndBytesConfig(
            load_in_4bit              = True,
            bnb_4bit_compute_dtype    = compute_dtype,
            bnb_4bit_quant_type       = qlora_cfg.get("bnb_4bit_quant_type", "nf4"),
            bnb_4bit_use_double_quant = qlora_cfg.get("bnb_4bit_use_double_quant", True),
        )

    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        quantization_config     = bnb_config,
        device_map              = "auto",
        trust_remote_code       = True,
        attn_implementation     = model_cfg.get("attn_implementation", "eager"),
    )

    # Prepare for k-bit training (disables KV cache, enables grad checkpointing)
    if bnb_config is not None:
        model = prepare_model_for_kbit_training(
            model,
            use_gradient_checkpointing = config.get("training", {}).get(
                "gradient_checkpointing", True
            ),
        )

    # ── Apply LoRA adapters ───────────────────────────────────────────────────
    peft_config = LoraConfig(
        r              = int(lora_cfg.get("r", 16)),
        lora_alpha     = int(lora_cfg.get("alpha", 32)),
        target_modules = lora_cfg.get("target_modules",
                                       ["q_proj", "k_proj", "v_proj", "o_proj"]),
        lora_dropout   = float(lora_cfg.get("dropout", 0.05)),
        bias           = str(lora_cfg.get("bias", "none")),
        task_type      = TaskType.CAUSAL_LM,
        inference_mode = False,
        use_rslora     = bool(lora_cfg.get("use_rslora", False)),
    )
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()

    # ── Tokenizer ─────────────────────────────────────────────────────────────
    tokenizer = AutoTokenizer.from_pretrained(
        model_path,
        trust_remote_code  = True,
        padding_side       = "right",   # right-padding for causal LM
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    return model, tokenizer


# ─────────────────────────────────────────────────────────────────────────────
# TRAINING ARGUMENTS  (Task 3.2 focus)
# ─────────────────────────────────────────────────────────────────────────────

def build_training_args(config: Dict, lr_override: Optional[float] = None) -> "TrainingArguments":
    """
    Construct HuggingFace TrainingArguments from the YAML config.

    Key hyperparameters:
      learning_rate      2e-4        (or --lr override)
      lr_scheduler_type  cosine      Smooth monotone decay
      warmup_ratio       0.05        Linear warm-up for first 5% of steps
      weight_decay       0.01        L2 regularisation
      max_grad_norm      1.0         Gradient clipping
    """
    if not _HAS_TRANSFORMERS:
        raise ImportError("pip install transformers")

    t  = config.get("training", {})
    lr = lr_override or float(t.get("learning_rate", 2e-4))

    return TrainingArguments(
        output_dir                  = str(ROOT / t.get("output_dir", "models/ouroboros-blue-lora")),
        num_train_epochs            = int(t.get("num_train_epochs", 3)),
        per_device_train_batch_size = int(t.get("per_device_train_batch_size", 4)),
        per_device_eval_batch_size  = int(t.get("per_device_eval_batch_size", 4)),
        gradient_accumulation_steps = int(t.get("gradient_accumulation_steps", 4)),
        gradient_checkpointing      = bool(t.get("gradient_checkpointing", True)),

        # ── LR + scheduler (Task 3.2) ─────────────────────────────────────────
        learning_rate               = lr,
        lr_scheduler_type           = t.get("lr_scheduler_type", "cosine"),
        warmup_ratio                = float(t.get("warmup_ratio", 0.05)),

        # ── Regularisation ────────────────────────────────────────────────────
        weight_decay                = float(t.get("weight_decay", 0.01)),
        max_grad_norm               = float(t.get("max_grad_norm", 1.0)),

        # ── Precision ─────────────────────────────────────────────────────────
        fp16                        = bool(t.get("fp16", False)),
        bf16                        = bool(t.get("bf16", False)),
        use_cpu                     = True,

        # ── Logging + checkpointing ───────────────────────────────────────────
        logging_steps               = int(t.get("logging_steps", 10)),
        eval_strategy               = t.get("eval_strategy", "steps"),
        eval_steps                  = int(t.get("eval_steps", 100)),
        save_strategy               = t.get("save_strategy", "steps"),
        save_steps                  = int(t.get("save_steps", 100)),
        save_total_limit            = int(t.get("save_total_limit", 3)),
        load_best_model_at_end      = bool(t.get("load_best_model_at_end", True)),
        metric_for_best_model       = t.get("metric_for_best_model", "eval_loss"),
        greater_is_better           = bool(t.get("greater_is_better", False)),
        report_to                   = t.get("report_to", "none"),
        seed                        = int(t.get("seed", 42)),

        # ── Optimizer  (Task 6.1) ─────────────────────────────────────────────
        # paged_adamw_8bit pages optimizer states (m, v tensors) to CPU RAM
        # via NVIDIA unified memory, preventing OOM on the backward pass.
        # See lora_config.yaml training.optim for full option guide.
        optim                       = t.get("optim", "paged_adamw_8bit"),

        dataloader_pin_memory       = False,   # safe for QLoRA
    )

# ─────────────────────────────────────────────────────────────────────────────
# EARLY STOPPING CALLBACK  (Task 4.1)
# ─────────────────────────────────────────────────────────────────────────────

def build_early_stopping_callback(
    config: Dict,
    patience_override: Optional[int] = None,
) -> Optional[object]:
    """
    Build a HuggingFace EarlyStoppingCallback from the YAML config.

    Halts training if eval_loss does not improve by >= threshold for
    `patience` consecutive evaluations.

    Requirements (enforced by HF Trainer):
      - TrainingArguments.load_best_model_at_end = True
      - TrainingArguments.eval_strategy != "no"

    Args:
        config:           Full config dict.
        patience_override: If set, overrides config early_stopping.patience.

    Returns:
        EarlyStoppingCallback instance, or None if disabled / unavailable.
    """
    es_cfg = config.get("Early_stopping", {})
    if not es_cfg.get("enabled", True):
        logger.info("Early stopping: disabled in config")
        return None

    if EarlyStoppingCallback is None:
        logger.warning(
            "EarlyStoppingCallback not available (transformers not installed). "
            "Install with: pip install transformers"
        )
        return None

    patience  = patience_override if patience_override is not None \
                else int(es_cfg.get("patience",  3))
    threshold = float(es_cfg.get("threshold", 1e-4))

    logger.info(
        f"Early stopping: patience={patience}, threshold={threshold:.1e}  "
        f"(halts after {patience} evals with no improvement)"
    )
    return EarlyStoppingCallback(
        early_stopping_patience  = patience,
        early_stopping_threshold = threshold,
    )



def build_trainer(
    model,
    tokenizer,
    train_dataset,
    val_dataset,
    training_args: "TrainingArguments",
    config: Dict,
    callbacks: Optional[List] = None,
) -> "SFTTrainer":
    """
    Build a TRL SFTTrainer with response-only loss masking.

    DataCollatorForCompletionOnlyLM masks the system + user tokens with -100
    so only the assistant turn contributes to the cross-entropy loss.
    """
    # Qwen2.5 ChatML response template (marks start of assistant turn)
    response_template = "<|im_start|>assistant\n"
    collator = DataCollatorForCompletionOnlyLM(
        response_template = response_template,
        tokenizer         = tokenizer,
    )

    training_args.push_to_hub_token = False
    original_to_dict = training_args.to_dict
    
    def to_dict_with_push_to_hub_token():
        d = original_to_dict()
        d["push_to_hub_token"] = False
        return d
        
    training_args.to_dict = to_dict_with_push_to_hub_token

    return SFTTrainer(
        model             = model,
        tokenizer         = tokenizer,
        train_dataset     = train_dataset,
        eval_dataset      = val_dataset,
        args              = training_args,
        data_collator     = collator,
        callbacks         = callbacks,
    )


# ─────────────────────────────────────────────────────────────────────────────
# SWEEP MODE  (Task 3.2)
# ─────────────────────────────────────────────────────────────────────────────

LR_SWEEP = [5e-5, 1e-4, 2e-4, 3e-4, 5e-4]

def run_sweep(config: Dict, dry_run: bool = True) -> None:
    """
    Print a comparison table of LR options with their schedule parameters.
    In dry-run mode just prints; in live mode runs a short warm-up eval for each.
    """
    t           = config.get("training", {})
    warmup_r    = float(t.get("warmup_ratio", 0.05))
    n_train_est = 10_000  # estimated total training entries for table
    bs          = int(t.get("per_device_train_batch_size", 4))
    accum       = int(t.get("gradient_accumulation_steps", 4))
    epochs      = int(t.get("num_train_epochs", 3))
    total_steps = estimate_total_steps(n_train_est, bs, accum, epochs)

    print(f"\n{'═' * 70}")
    print(f"  LR Sweep Comparison  |  total_steps ≈ {total_steps:,} (est. {n_train_est:,} samples)")
    print(f"{'─' * 70}")
    print(f"  {'LR':>10}  {'Warmup steps':>14}  {'LR@10%':>10}  {'LR@50%':>10}  {'LR@90%':>10}")
    print(f"{'─' * 70}")
    ws = int(total_steps * warmup_r)
    for lr in LR_SWEEP:
        lr_10 = cosine_lr_at_step(int(total_steps * 0.10), total_steps, lr, ws)
        lr_50 = cosine_lr_at_step(int(total_steps * 0.50), total_steps, lr, ws)
        lr_90 = cosine_lr_at_step(int(total_steps * 0.90), total_steps, lr, ws)
        marker = " <-- default" if abs(lr - 2e-4) < 1e-10 else ""
        print(f"  {lr:>10.2e}  {ws:>14,}  {lr_10:>10.2e}  {lr_50:>10.2e}  {lr_90:>10.2e}{marker}")
    print(f"{'═' * 70}\n")


# ─────────────────────────────────────────────────────────────────────────────
# DRY-RUN  (validation only, no GPU needed)
# ─────────────────────────────────────────────────────────────────────────────

def dry_run(config: Dict) -> None:
    """
    Print config summary, LR schedule, and sweep table without loading weights.
    """
    t           = config.get("training", {})
    lora        = config.get("lora", {})
    lr          = float(t.get("learning_rate", 2e-4))
    warmup_r    = float(t.get("warmup_ratio", 0.05))
    n_train_est = 18
    bs          = int(t.get("per_device_train_batch_size", 4))
    accum       = int(t.get("gradient_accumulation_steps", 4))
    epochs      = int(t.get("num_train_epochs", 3))
    total_steps = estimate_total_steps(n_train_est, bs, accum, epochs)
    ws          = int(total_steps * warmup_r)

    print("\n" + "═" * 60)
    print("  Training Configuration (dry-run)")
    print("─" * 60)
    print(f"  learning_rate       : {lr:.2e}")
    print(f"  lr_scheduler        : {t.get('lr_scheduler_type', 'cosine')}")
    print(f"  warmup_ratio        : {warmup_r}  ({ws} steps)")
    print(f"  weight_decay        : {t.get('weight_decay', 0.01)}")
    print(f"  max_grad_norm       : {t.get('max_grad_norm', 1.0)}")
    print(f"  num_epochs          : {epochs}")
    print(f"  eff. batch_size     : {bs * accum}  ({bs} × {accum} accum)")
    print(f"  total_steps (est.)  : {total_steps}")
    print(f"  LoRA r / alpha      : {lora.get('r', 16)} / {lora.get('alpha', 32)}")
    print(f"  target_modules      : {lora.get('target_modules', [])}")
    print(f"  QLoRA 4-bit         : {config.get('qlora', {}).get('enabled', True)}")

    # Early stopping (Task 4.1)
    es = config.get("Early_stopping", {})
    print(f"\n  Early Stopping (Task 4.1):")
    print(f"  enabled             : {es.get('enabled', True)}")
    print(f"  patience            : {es.get('patience', 3)}  evaluations")
    print(f"  threshold           : {es.get('threshold', 1e-4):.1e}")
    print(f"  eval every          : {t.get('eval_steps', 200)} steps  "
          f"(= {es.get('patience', 3) * int(t.get('eval_steps', 200))} steps of patience)")
    # Checkpoint (Task 4.2)
    print(f"\n  Checkpointing (Task 4.2):")
    print(f"  save_steps          : {t.get('save_steps', 200)}")
    print(f"  save_total_limit    : {t.get('save_total_limit', 5)} checkpoints")
    print(f"  load_best_at_end    : {t.get('load_best_model_at_end', True)}")
    print(f"  output_dir          : {t.get('output_dir', 'models/ouroboros-blue-lora')}")
    print("=" * 60 + "\n")

    print_lr_schedule(lr, max(total_steps, 200), warmup_r, n_points=30)
    run_sweep(config)

    # Check deps
    print("  Dependency check:")
    for name, flag in [
        ("yaml",         _HAS_YAML),
        ("torch",        _HAS_TORCH),
        ("transformers", _HAS_TRANSFORMERS),
        ("peft",         _HAS_PEFT),
        ("trl",          _HAS_TRL),
        ("datasets",     _HAS_DATASETS),
    ]:
        status = "OK" if flag else "MISSING"
        print(f"    {name:<16} {status}")
    print()

    missing = [n for n, f in [
        ("peft", _HAS_PEFT), ("trl", _HAS_TRL), ("accelerate", False),
        ("bitsandbytes", False), ("datasets", _HAS_DATASETS),
    ] if not f]
    if missing:
        print("  Install missing packages:")
        print(f"    pip install {' '.join(missing)}")
        print()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ouroboros – Fine-Tuning Training Script (Tasks 3.2 / 4.1 / 4.2)",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--config",  type=Path, default=CONFIG_PATH)
    parser.add_argument("--preset",  type=str,  default=None,
                        choices=["conservative", "balanced", "high_rank", "ablation_low",
                                 "reg_light", "reg_moderate"],
                        help="LoRA experiment preset")
    parser.add_argument("--lr",      type=float, default=None,
                        help="Override learning rate (e.g. 1e-4)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate config, show schedule preview, no training")
    parser.add_argument("--sweep",   action="store_true",
                        help="Show LR sweep comparison table (dry-run only)")
    # Task 4.1
    parser.add_argument("--patience", type=int, default=None,
                        help="Early stopping patience (overrides config; default: 3)")
    parser.add_argument("--no-early-stop", action="store_true",
                        help="Disable early stopping entirely")
    # Task 4.2
    parser.add_argument("--resume-from-checkpoint", type=str, default=None,
                        metavar="PATH_OR_AUTO",
                        help="Resume from checkpoint. Pass a path or 'auto' to use "
                             "the latest checkpoint in output_dir.")
    return parser.parse_args()


def main():
    args = parse_args()

    logger.info("=" * 60)
    logger.info("Ouroboros -- Fine-Tuning  (Tasks 3.2 / 4.1 / 4.2)")
    logger.info("=" * 60)

    # Load + merge config
    config = load_config(args.config)
    config = merge_preset(config, args.preset)
    if args.lr:
        config.setdefault("training", {})["learning_rate"] = args.lr

    # Propagate --no-early-stop
    if args.no_early_stop:
        config.setdefault("Early_stopping", {})["enabled"] = False

    # Dry-run
    if args.dry_run or args.sweep:
        dry_run(config)
        if args.sweep:
            run_sweep(config)
        return

    # ── Live training ─────────────────────────────────────────────────────────
    logger.info("Loading model and tokenizer…")
    model, tokenizer = load_model_and_tokenizer(config)

    logger.info("Loading datasets…")
    train_ds, val_ds = prepare_datasets(config)

    logger.info("Building TrainingArguments…")
    training_args = build_training_args(config, lr_override=args.lr)

    # Print LR schedule preview
    print_lr_schedule(
        training_args.learning_rate,
        total_steps=1000,
        warmup_ratio=training_args.warmup_ratio,
    )

    # Task 4.1: Early stopping callback
    es_callback = build_early_stopping_callback(config, patience_override=args.patience)
    callbacks   = [es_callback] if es_callback is not None else []

    logger.info("Building SFTTrainer…")
    trainer = build_trainer(
        model, tokenizer, train_ds, val_ds,
        training_args, config,
        callbacks=callbacks,
    )

    # Task 4.2: Resume from checkpoint
    resume_ckpt = args.resume_from_checkpoint
    if resume_ckpt == "auto":
        out_dir = Path(training_args.output_dir)
        ckpts   = sorted(out_dir.glob("checkpoint-*"),
                         key=lambda p: int(p.name.split("-")[-1]))
        resume_ckpt = str(ckpts[-1]) if ckpts else None
        if resume_ckpt:
            logger.info(f"Auto-resume: {resume_ckpt}")
        else:
            logger.warning("--resume-from-checkpoint auto: no checkpoints found, starting fresh")
            resume_ckpt = None

    logger.info("Starting training…")
    trainer.train(resume_from_checkpoint=resume_ckpt)

    logger.info("Saving final LoRA adapter…")
    out_dir = Path(training_args.output_dir)
    trainer.save_model(str(out_dir))
    tokenizer.save_pretrained(str(out_dir))
    logger.info(f"Saved to {out_dir}")
    logger.info("Run checkpoint_manager.py --best to find the optimal adapter.")


if __name__ == "__main__":
    main()
