"""
Ouroboros AI - Dataset Sanity Check  (Task 6.2)
===============================================
Counts rows and tokens in the train / val / test splits, estimates
GPU epoch time, and warns if the dataset size is out of the expected
compute budget.

Token counting strategy:
  - Primary  : transformers AutoTokenizer (Qwen2.5-Coder-3B tokenizer)
  - Fallback  : tiktoken (cl100k_base)
  - Last resort: whitespace split (word count proxy)

Epoch time estimate:
  time_per_epoch = (tokens_train / (batch_tokens_per_step * steps_per_sec))
  where:
    batch_tokens_per_step = eff_batch_size * max_seq_len
    steps_per_sec         = GPU_TFLOPS / (6 * params * seq_len)  [approx]

Usage
-----
  python scripts/data_preparation/dataset_sanity_check.py
  python scripts/data_preparation/dataset_sanity_check.py --tokenizer Qwen/Qwen2.5-Coder-3B-Instruct
  python scripts/data_preparation/dataset_sanity_check.py --output data/evaluation/sanity_report.json
"""

import argparse
import json
import math
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT        = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = ROOT / "config" / "lora_config.yaml"
SPLITS_DIR  = ROOT / "data" / "splits"
OUTPUT_FILE = ROOT / "data" / "evaluation" / "sanity_report.json"

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG LOADER
# ─────────────────────────────────────────────────────────────────────────────

def load_config(path: Path) -> Dict:
    try:
        import yaml
        with path.open(encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}

# ─────────────────────────────────────────────────────────────────────────────
# TOKENIZER LOADING  (with three-tier fallback)
# ─────────────────────────────────────────────────────────────────────────────

def load_tokenizer(model_name: Optional[str] = None):
    """Try HuggingFace tokenizer, then tiktoken, then None (word count)."""
    if model_name:
        try:
            from transformers import AutoTokenizer
            tok = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
            print(f"  Tokenizer: {model_name} (HuggingFace)")
            return ("hf", tok)
        except Exception as e:
            print(f"  HF tokenizer load failed ({e}). Trying tiktoken...")

    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        print("  Tokenizer: cl100k_base (tiktoken fallback)")
        return ("tiktoken", enc)
    except ImportError:
        pass

    print("  Tokenizer: word-count proxy (install tiktoken for accurate counts)")
    return ("wordcount", None)


def count_tokens(text: str, tokenizer_tuple) -> int:
    kind, tok = tokenizer_tuple
    if kind == "hf":
        return len(tok.encode(text, add_special_tokens=False))
    elif kind == "tiktoken":
        return len(tok.encode(text))
    else:
        return len(text.split())

# ─────────────────────────────────────────────────────────────────────────────
# JSONL STATS
# ─────────────────────────────────────────────────────────────────────────────

def load_jsonl(path: Path) -> List[Dict]:
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return rows


def text_from_entry(entry: Dict) -> str:
    """Extract all text content from a dataset entry."""
    parts = []
    for msg in entry.get("messages", []):
        parts.append(msg.get("content", ""))
    if not parts and "text" in entry:
        parts.append(entry["text"])
    return "\n".join(parts)


def compute_split_stats(rows: List[Dict], tokenizer_tuple, split_name: str) -> Dict:
    if not rows:
        return {
            "split": split_name, "rows": 0,
            "tokens_total": 0, "tokens_mean": 0,
            "tokens_min": 0, "tokens_max": 0,
            "tokens_p95": 0,
        }

    token_counts = []
    for row in rows:
        text = text_from_entry(row)
        token_counts.append(count_tokens(text, tokenizer_tuple))

    token_counts.sort()
    n     = len(token_counts)
    total = sum(token_counts)
    p95_idx = min(int(n * 0.95), n - 1)

    return {
        "split":         split_name,
        "rows":          n,
        "tokens_total":  total,
        "tokens_mean":   total // n,
        "tokens_min":    token_counts[0],
        "tokens_max":    token_counts[-1],
        "tokens_p95":    token_counts[p95_idx],
    }

# ─────────────────────────────────────────────────────────────────────────────
# EPOCH TIME ESTIMATOR
# ─────────────────────────────────────────────────────────────────────────────

# Per-GPU TFLOPS (bf16) reference values
GPU_TFLOPS: Dict[str, float] = {
    "A100":               312,
    "H100":               989,
    "RTX 4090":           165,
    "RTX 4080":           97,
    "RTX 3090":           71,
    "RTX 3080":           60,
    "RTX 3070":           40,
    "RTX 2080":           22.8,
    "V100":               125,
    "T4":                 65,
    "L4":                 121,
    "A10G":               125,
    "UNKNOWN":            50,     # conservative assumption
}

MODEL_PARAMS_B = 3.09    # Qwen2.5-Coder-3B


def detect_gpu_tflops() -> Tuple[str, float]:
    try:
        import torch
        if not torch.cuda.is_available():
            return "CPU", 0.5
        name = torch.cuda.get_device_name(0)
        for key, tflops in GPU_TFLOPS.items():
            if key.upper() in name.upper():
                return name, tflops
        return name, GPU_TFLOPS["UNKNOWN"]
    except ImportError:
        return "CPU (torch not installed)", 0.5


def estimate_epoch_time(
    tokens_train: int,
    batch_size: int,
    grad_accum: int,
    seq_len: int,
    gpu_tflops: float,
) -> Dict:
    """
    Estimates training throughput using the 6*N*D/T formula:
      FLOPs per token ≈ 6 * params
      time = total_tokens * 6 * params / (tflops * 1e12)
    Also accounts for gradient computation (forward + backward ≈ 3x forward).
    """
    eff_batch        = batch_size * grad_accum
    tokens_per_step  = eff_batch * seq_len
    total_steps      = math.ceil(tokens_train / tokens_per_step)

    # FLOPs per forward pass token: 6N (model) + small LoRA overhead
    flops_per_token  = 6 * MODEL_PARAMS_B * 1e9

    # Total FLOPs = forward + backward (≈ 2 × forward) = 3 × forward total
    total_flops      = tokens_train * flops_per_token * 3

    if gpu_tflops <= 0:
        seconds = float("inf")
    else:
        seconds = total_flops / (gpu_tflops * 1e12)

    hours   = seconds / 3600
    minutes = (seconds % 3600) / 60

    return {
        "total_steps":       total_steps,
        "eff_batch_size":    eff_batch,
        "tokens_per_step":   tokens_per_step,
        "estimated_seconds": round(seconds, 0),
        "estimated_hm":      f"{int(hours)}h {int(minutes)}m",
        "gpu_tflops":        gpu_tflops,
        "note": ("GPU not available — CPU estimate" if gpu_tflops < 5 else
                 "Estimate assumes 40-60% MFU (model FLOP utilization)"),
    }

# ─────────────────────────────────────────────────────────────────────────────
# WARNINGS
# ─────────────────────────────────────────────────────────────────────────────

def generate_warnings(
    stats: List[Dict],
    config: Dict,
    gpu_name: str,
    epoch_est: Dict,
) -> List[str]:
    warnings = []
    t   = config.get("training", {})
    seq = int(config.get("data", {}).get("max_seq_length", 4096))

    train_stat = next((s for s in stats if s["split"] == "train"), {})
    val_stat   = next((s for s in stats if s["split"] == "val"), {})

    n_train = train_stat.get("rows", 0)
    n_val   = val_stat.get("rows", 0)
    max_tok = train_stat.get("tokens_max", 0)
    p95_tok = train_stat.get("tokens_p95", 0)

    # Size warnings
    if n_train < 100:
        warnings.append(
            f"Very small training set ({n_train} rows). Model may overfit or underfit. "
            "Consider augmentation or more data."
        )
    if n_train < 1000:
        warnings.append(
            f"Small dataset ({n_train} rows). For production quality, aim for 5,000+ VQL pairs."
        )

    # Val split check
    if n_val == 0:
        warnings.append("No validation data found! Early stopping cannot function.")
    elif n_val < 5:
        warnings.append(
            f"Only {n_val} validation sample(s). eval_loss will be noisy. "
            "Early stopping recommendations may be unreliable."
        )

    # Token length vs max_seq_length
    if max_tok > seq:
        warnings.append(
            f"Max token count in training ({max_tok:,}) exceeds max_seq_length ({seq:,}). "
            "Some samples will be truncated."
        )
    if p95_tok > seq * 0.85:
        warnings.append(
            f"P95 token count ({p95_tok:,}) is {p95_tok/seq*100:.0f}% of max_seq_length. "
            "Many samples near truncation boundary."
        )

    # Epoch time
    est_h = epoch_est.get("estimated_seconds", 0) / 3600
    n_epochs = int(t.get("num_train_epochs", 3))
    if est_h > 8:
        warnings.append(
            f"Estimated epoch time {epoch_est['estimated_hm']} × {n_epochs} epochs "
            f"= {est_h*n_epochs:.1f}h total. Consider reducing epochs or batch-size."
        )
    elif est_h < 0.1 and n_train > 0:
        warnings.append(
            "Epoch estimated < 6 min. Dataset may be too small for meaningful training."
        )

    return warnings

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def print_report(stats: List[Dict], epoch_est: Dict, gpu_name: str,
                 warnings: List[str], tokenizer_kind: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"  DATASET SANITY CHECK  (Task 6.2)")
    print(f"{'─' * 70}")
    print(f"  Tokenizer  : {tokenizer_kind}")
    print(f"  GPU        : {gpu_name}  ({epoch_est['gpu_tflops']:.0f} TFLOPS bf16)")
    print(f"{'─' * 70}")
    print(f"  {'Split':<8}  {'Rows':>6}  {'Tokens':>10}  {'Mean':>7}  {'P95':>7}  {'Max':>7}")
    print(f"  {'─'*60}")
    for s in stats:
        print(f"  {s['split']:<8}  {s['rows']:>6,}  "
              f"{s['tokens_total']:>10,}  {s['tokens_mean']:>7,}  "
              f"{s['tokens_p95']:>7,}  {s['tokens_max']:>7,}")
    print(f"{'─' * 70}")

    ep = epoch_est
    print(f"\n  Epoch Time Estimate:")
    print(f"    Effective batch size  : {ep['eff_batch_size']}")
    print(f"    Tokens per step       : {ep['tokens_per_step']:,}")
    print(f"    Total gradient steps  : {ep['total_steps']:,}")
    print(f"    Estimated 1 epoch     : {ep['estimated_hm']}")
    print(f"    Note                  : {ep['note']}")

    if warnings:
        print(f"\n  Warnings ({len(warnings)}):")
        for w in warnings:
            print(f"    !! {w}")
    else:
        print(f"\n  No warnings — dataset looks healthy.")

    print(f"{'=' * 70}\n")


def run_sanity_check(
    config: Dict,
    tokenizer_name: Optional[str],
    output_file: Optional[Path],
) -> Dict:
    t = config.get("training", {})

    # Load tokenizer
    tok_tuple = load_tokenizer(tokenizer_name)
    tok_kind  = tok_tuple[0]

    # Per-split stats
    stats = []
    for split_name in ("train", "val", "test"):
        key  = f"{split_name}_file"
        path_str = config.get("data", {}).get(key, f"data/splits/{split_name}.jsonl")
        path = ROOT / path_str
        rows = load_jsonl(path)
        s    = compute_split_stats(rows, tok_tuple, split_name)
        stats.append(s)
        print(f"  Loaded {split_name}: {s['rows']} rows  "
              f"({s['tokens_total']:,} tokens  mean={s['tokens_mean']:,})")

    # Epoch time estimate
    train_tokens = next((s["tokens_total"] for s in stats if s["split"] == "train"), 0)
    gpu_name, gpu_tflops = detect_gpu_tflops()
    epoch_est = estimate_epoch_time(
        tokens_train = train_tokens,
        batch_size   = int(t.get("per_device_train_batch_size", 4)),
        grad_accum   = int(t.get("gradient_accumulation_steps", 4)),
        seq_len      = int(config.get("data", {}).get("max_seq_length", 4096)),
        gpu_tflops   = gpu_tflops,
    )

    warnings = generate_warnings(stats, config, gpu_name, epoch_est)
    print_report(stats, epoch_est, gpu_name, warnings, tok_kind)

    report = {
        "timestamp":    time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tokenizer":    tok_kind,
        "gpu":          gpu_name,
        "splits":       stats,
        "epoch_estimate": epoch_est,
        "warnings":     warnings,
    }

    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with output_file.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"  Report saved: {output_file}\n")

    return report


def parse_args():
    parser = argparse.ArgumentParser(
        description="Ouroboros - Dataset Sanity Check (Task 6.2)",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--config",     type=Path,  default=CONFIG_PATH)
    parser.add_argument("--tokenizer",  type=str,   default=None,
                        metavar="MODEL_NAME",
                        help="HF tokenizer repo (e.g. Qwen/Qwen2.5-Coder-3B-Instruct)")
    parser.add_argument("--output",     type=Path,  default=OUTPUT_FILE)
    parser.add_argument("--no-output",  action="store_true",
                        help="Skip writing JSON report")
    return parser.parse_args()


def main():
    args   = parse_args()
    print("=" * 70)
    print("  Ouroboros -- Dataset Sanity Check  (Task 6.2)")
    print("=" * 70)
    config = load_config(args.config)
    run_sanity_check(
        config         = config,
        tokenizer_name = args.tokenizer,
        output_file    = None if args.no_output else args.output,
    )


if __name__ == "__main__":
    main()
