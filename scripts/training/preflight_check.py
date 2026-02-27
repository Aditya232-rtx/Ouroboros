"""
Ouroboros AI - Pre-Flight Check  (Task 6.1)
===========================================
Verifies that the compute environment is ready for a full training run.

Checks:
  1. GPU / VRAM availability and free memory
  2. RAM available
  3. Optimizer setting (must be paged_adamw_8bit or paged_adamw_32bit)
  4. bitsandbytes availability (required for QLoRA + paged optimizer)
  5. Key training hyperparameters and estimated peak VRAM
  6. Dataset file existence
  7. Python packages

Exits with:
  0  Everything is PASS or WARN
  1  At least one FAIL (training will likely OOM or crash)

Usage
-----
  python scripts/training/preflight_check.py
  python scripts/training/preflight_check.py --config config/lora_config.yaml
"""

import argparse
import importlib
import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT        = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = ROOT / "config" / "lora_config.yaml"

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG LOADER (copied-inline so script is self-contained)
# ─────────────────────────────────────────────────────────────────────────────

def load_config(path: Path) -> Dict:
    try:
        import yaml
        with path.open(encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        pass
    # Minimal fallback parser
    cfg: Dict = {}
    try:
        with path.open(encoding="utf-8") as f:
            current_key = None
            for line in f:
                line = line.rstrip()
                if not line or line.lstrip().startswith("#"):
                    continue
                if line and not line[0].isspace():
                    current_key = line.split(":")[0].strip()
                    cfg[current_key] = {}
                elif current_key and ":" in line:
                    k, _, v = line.strip().partition(":")
                    v = v.strip()
                    if current_key not in cfg:
                        cfg[current_key] = {}
                    cfg[current_key][k.strip()] = v
    except Exception:
        pass
    return cfg

# ─────────────────────────────────────────────────────────────────────────────
# CHECK RESULT TYPES
# ─────────────────────────────────────────────────────────────────────────────

PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"

CheckResult = Tuple[str, str, str]   # (status, name, message)


def result(status: str, name: str, msg: str) -> CheckResult:
    return (status, name, msg)

# ─────────────────────────────────────────────────────────────────────────────
# INDIVIDUAL CHECKS
# ─────────────────────────────────────────────────────────────────────────────

def check_packages() -> List[CheckResult]:
    """Verify all required Python packages are importable."""
    required = {
        "torch":          "pip install torch",
        "transformers":   "pip install transformers",
        "peft":           "pip install peft",
        "trl":            "pip install trl",
        "bitsandbytes":   "pip install bitsandbytes",
        "accelerate":     "pip install accelerate",
        "datasets":       "pip install datasets",
    }
    results = []
    for pkg, install_tip in required.items():
        try:
            m = importlib.import_module(pkg)
            ver = getattr(m, "__version__", "?")
            results.append(result(PASS, f"pkg:{pkg}", f"v{ver}"))
        except ImportError:
            results.append(result(FAIL, f"pkg:{pkg}", f"NOT INSTALLED.  {install_tip}"))
    return results


def check_gpu() -> List[CheckResult]:
    """Check GPU VRAM availability."""
    results_list = []
    try:
        import torch
        if not torch.cuda.is_available():
            results_list.append(result(
                WARN, "GPU",
                "CUDA not available. Training will run on CPU (extremely slow). "
                "Ensure NVIDIA drivers and torch+cuda are installed."
            ))
            return results_list

        n_gpus = torch.cuda.device_count()
        results_list.append(result(PASS, "CUDA", f"{n_gpus} GPU(s) available"))

        for i in range(n_gpus):
            props     = torch.cuda.get_device_properties(i)
            total_gb  = props.total_memory / 1e9
            free_mem  = torch.cuda.mem_get_info(i)[0] / 1e9
            name      = props.name

            if total_gb < 8:
                status = FAIL
                note   = "< 8 GB — insufficient even for QLoRA"
            elif total_gb < 16:
                status = WARN
                note   = "8-16 GB — reduce batch size to 1-2"
            else:
                status = PASS
                note   = "sufficient for QLoRA training"

            results_list.append(result(
                status, f"GPU[{i}]",
                f"{name}  total={total_gb:.1f} GB  free={free_mem:.1f} GB  ({note})"
            ))
    except ImportError:
        results_list.append(result(FAIL, "GPU", "torch not installed — cannot check GPU"))
    return results_list


def check_ram() -> List[CheckResult]:
    """Check system RAM."""
    try:
        import psutil
        vm       = psutil.virtual_memory()
        total_gb = vm.total / 1e9
        free_gb  = vm.available / 1e9
        if total_gb < 16:
            return [result(WARN, "RAM",
                f"total={total_gb:.1f} GB  available={free_gb:.1f} GB  "
                "(< 16 GB — paged optimizer offload may be slow)")]
        return [result(PASS, "RAM",
            f"total={total_gb:.1f} GB  available={free_gb:.1f} GB")]
    except ImportError:
        return [result(WARN, "RAM", "psutil not installed — skipping RAM check  (pip install psutil)")]


def check_optimizer(config: Dict) -> List[CheckResult]:
    """
    Task 6.1 core check: verify optimizer is paged_adamw_8bit or paged_adamw_32bit.
    These are the only two options that use NVIDIA page migration to prevent OOM.
    """
    t     = config.get("training", {})
    optim = t.get("optim", "NOT SET")

    safe_optimizers = {"paged_adamw_8bit", "paged_adamw_32bit", "adamw_8bit", "adamw_bnb_8bit"}
    risky_optimizers = {"adamw_torch", "adamw_hf", "sgd", "adam"}

    if optim in {"paged_adamw_8bit", "paged_adamw_32bit"}:
        return [result(PASS, "optimizer",
            f"{optim}  ← paged optimizer active, OOM risk mitigated")]
    elif optim in {"adamw_8bit", "adamw_bnb_8bit"}:
        return [result(WARN, "optimizer",
            f"{optim}  ← 8-bit optimizer but NOT paged. "
            "May OOM during backward on ≤16 GB VRAM. "
            "Recommend: optim: paged_adamw_8bit")]
    elif optim == "NOT SET":
        return [result(FAIL, "optimizer",
            "optim not set in config!  "
            "Add  optim: paged_adamw_8bit  to lora_config.yaml training section")]
    elif optim in risky_optimizers:
        return [result(FAIL, "optimizer",
            f"{optim}  ← 32-bit optimizer. HIGH OOM risk on QLoRA with ≤24 GB VRAM. "
            "Change to: optim: paged_adamw_8bit")]
    else:
        return [result(WARN, "optimizer",
            f"{optim}  ← unknown optimizer. Verify it supports 8-bit paged states.")]


def check_bitsandbytes() -> List[CheckResult]:
    """bitsandbytes is required both for 4-bit quantization and paged optimizer."""
    try:
        import bitsandbytes as bnb
        ver = getattr(bnb, "__version__", "?")
        # Check that CUDA ops are compiled
        try:
            _ = bnb.optim.PagedAdamW8bit
            return [result(PASS, "bitsandbytes", f"v{ver}  PagedAdamW8bit available")]
        except AttributeError:
            return [result(WARN, "bitsandbytes",
                f"v{ver} installed but PagedAdamW8bit not found. "
                "Upgrade: pip install -U bitsandbytes")]
    except ImportError:
        return [result(FAIL, "bitsandbytes",
            "NOT INSTALLED.  pip install bitsandbytes  (required for QLoRA + paged optimizer)")]


def estimate_vram(config: Dict) -> List[CheckResult]:
    """
    Rough VRAM estimate for QLoRA training.

    Formula (4-bit QLoRA with LoRA r=16):
      model_4bit   = params * 0.5B  (4-bit storage)
      lora_adapter = 2 * r * hidden * n_layers * 4B  (float32 grads)
      activations  = batch * seq_len * hidden * layers * 2B  (bf16)
      optim_8bit   = lora_params * 2B  (8-bit m,v tensors)
    """
    t     = config.get("training", {})
    lora  = config.get("lora", {})
    qlora = config.get("qlora", {})

    # Qwen2.5-Coder-3B-Instruct architecture constants
    PARAMS_B   = 3.09          # billion parameters
    HIDDEN     = 2048          # hidden dim
    LAYERS     = 36            # transformer layers
    HEADS      = 16            # attention heads

    batch      = int(t.get("per_device_train_batch_size", 4))
    grad_accum = int(t.get("gradient_accumulation_steps", 4))
    seq_len    = int(config.get("data", {}).get("max_seq_length", 4096))
    r          = int(lora.get("r", 16))
    quant_4bit = qlora.get("enabled", True)

    # Model storage
    bytes_per_param = 0.5 if quant_4bit else 4.0
    model_gb  = PARAMS_B * 1e9 * bytes_per_param / 1e9

    # LoRA adapter (float32 weights + grads)
    n_target_modules = 4   # q,k,v,o projections
    lora_params  = 2 * r * HIDDEN * LAYERS * n_target_modules
    lora_gb      = lora_params * 4 / 1e9          # float32

    # Activation memory (gradient checkpointing halves this)
    grad_ckpt    = bool(t.get("gradient_checkpointing", True))
    act_gb_full  = batch * seq_len * HIDDEN * LAYERS * 2 / 1e9
    act_gb       = act_gb_full * (0.5 if grad_ckpt else 1.0)

    # Optimizer states
    optim        = t.get("optim", "paged_adamw_8bit")
    if "8bit" in optim:
        optim_bytes_per_param = 1    # 8-bit quantized
    elif "paged" in optim:
        optim_bytes_per_param = 2    # pages to CPU, minimal VRAM footprint
    else:
        optim_bytes_per_param = 8    # 32-bit m + v

    optim_gb = lora_params * optim_bytes_per_param / 1e9

    total_est = model_gb + lora_gb + act_gb + optim_gb
    overhead  = total_est * 0.15   # cuda kernels, misc buffers

    results_list = [
        result(PASS, "vram_estimate", (
            f"~{total_est + overhead:.1f} GB peak  "
            f"(model={model_gb:.1f} GB  lora={lora_gb:.2f} GB  "
            f"act={act_gb:.1f} GB  optim={optim_gb:.2f} GB  overhead=15%)"
        ))
    ]

    # Recommend action based on estimate
    if total_est + overhead > 24:
        results_list.append(result(WARN, "vram_action",
            f"Estimated {total_est+overhead:.1f} GB > 24 GB. "
            "Reduce batch_size to 1 and gradient_accumulation_steps to match."))
    elif total_est + overhead > 16:
        results_list.append(result(WARN, "vram_action",
            f"Estimated {total_est+overhead:.1f} GB. "
            "Fits on 24 GB GPU with some headroom. Watch for CUDA OOM."))
    else:
        results_list.append(result(PASS, "vram_action",
            f"Estimated {total_est+overhead:.1f} GB should fit on ≥16 GB VRAM"))

    return results_list


def check_data_files(config: Dict) -> List[CheckResult]:
    """Verify training data files exist."""
    data    = config.get("data", {})
    results_list = []
    for key in ("train_file", "val_file", "test_file"):
        path = data.get(key, "")
        full = ROOT / path if path else None
        if full and full.exists():
            size_kb = full.stat().st_size // 1024
            results_list.append(result(PASS, f"data:{key}", f"{full}  ({size_kb} KB)"))
        elif full:
            results_list.append(result(FAIL, f"data:{key}",
                f"NOT FOUND: {full}  — run data preparation scripts first"))
        else:
            results_list.append(result(WARN, f"data:{key}", f"Not configured in {CONFIG_PATH.name}"))
    return results_list


def check_gradient_checkpointing(config: Dict) -> List[CheckResult]:
    t = config.get("training", {})
    gc = bool(t.get("gradient_checkpointing", True))
    if gc:
        return [result(PASS, "grad_checkpoint",
            "enabled  — saves ~40% VRAM at cost of ~20% speed")]
    else:
        return [result(WARN, "grad_checkpoint",
            "DISABLED  — will use more VRAM. Enable: gradient_checkpointing: true")]


def check_bf16_fp16(config: Dict) -> List[CheckResult]:
    t    = config.get("training", {})
    bf16 = bool(t.get("bf16", True))
    fp16 = bool(t.get("fp16", False))
    if bf16 and not fp16:
        return [result(PASS, "precision", "bf16=True, fp16=False  — correct for Ampere+ GPUs")]
    elif fp16 and not bf16:
        return [result(WARN, "precision",
            "fp16=True — may cause NaN on large models. Prefer bf16 on Ampere+.")]
    elif bf16 and fp16:
        return [result(FAIL, "precision",
            "Both bf16 and fp16 are True! This will error. Set one to false.")]
    else:
        return [result(WARN, "precision",
            "Both bf16 and fp16 are False. Training in float32 — slow and memory intensive.")]


# ─────────────────────────────────────────────────────────────────────────────
# RUNNER
# ─────────────────────────────────────────────────────────────────────────────

def run_all_checks(config: Dict) -> List[CheckResult]:
    all_results = []
    all_results += check_packages()
    all_results += check_gpu()
    all_results += check_ram()
    all_results += check_optimizer(config)
    all_results += check_bitsandbytes()
    all_results += check_gradient_checkpointing(config)
    all_results += check_bf16_fp16(config)
    all_results += estimate_vram(config)
    all_results += check_data_files(config)
    return all_results


def print_report(checks: List[CheckResult]) -> int:
    """Print a formatted preflight report. Returns 1 if any FAIL, else 0."""
    ICON = {PASS: "OK  ", WARN: "WARN", FAIL: "FAIL"}

    fails  = [c for c in checks if c[0] == FAIL]
    warns  = [c for c in checks if c[0] == WARN]
    passes = [c for c in checks if c[0] == PASS]

    print(f"\n{'=' * 70}")
    print(f"  PREFLIGHT CHECK  (Task 6.1 - Pre-Flight Environment)")
    print(f"{'─' * 70}")
    for status, name, msg in checks:
        icon = ICON.get(status, "????")
        print(f"  [{icon}]  {name:<22}  {msg}")
    print(f"{'─' * 70}")
    print(f"  PASS: {len(passes)}   WARN: {len(warns)}   FAIL: {len(fails)}")
    print(f"{'─' * 70}")

    if fails:
        print(f"  PREFLIGHT STATUS: *** FAIL ***  ({len(fails)} critical issue(s) to resolve)")
        print(f"  Training is likely to crash. Fix FAIL items before proceeding.")
    elif warns:
        print(f"  PREFLIGHT STATUS: WARN  ({len(warns)} warning(s))")
        print(f"  Training may work but monitor VRAM carefully.")
    else:
        print(f"  PREFLIGHT STATUS: ALL CLEAR — ready to train")
    print(f"{'=' * 70}\n")

    return 1 if fails else 0


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Ouroboros - Pre-Flight Check (Task 6.1)",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--config",    type=Path, default=CONFIG_PATH)
    parser.add_argument("--json",      action="store_true",
                        help="Output results as JSON")
    return parser.parse_args()


def main():
    args   = parse_args()
    config = load_config(args.config)

    checks = run_all_checks(config)

    if args.json:
        import json as _json
        print(_json.dumps([
            {"status": s, "check": n, "message": m} for s, n, m in checks
        ], indent=2))
    else:
        exit_code = print_report(checks)
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
