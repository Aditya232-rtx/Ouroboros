"""
Ouroboros AI - LoRA Weight Merger  (Task 8.3)
==============================================
Merges a trained LoRA adapter permanently into the base Qwen Coder 3B
model using PEFT's merge_and_unload(), producing a self-contained model
that can be deployed without the adapter overhead.

When to use this
----------------
  Use after selecting the best checkpoint (Task 8.1) when you want to:
    - Deploy the Blue Agent as a standalone REST API (no PEFT dependency)
    - Convert to GGUF/ONNX/TensorRT for edge deployment
    - Publish the merged model to HuggingFace Hub

What it does
------------
  1. Loads the base Qwen2.5-Coder-3B-Instruct model in the specified precision
  2. Loads the LoRA adapter from models/ouroboros-blue-final
  3. Calls model.merge_and_unload() to fuse adapter weights permanently
  4. Saves the merged model + tokenizer to models/ouroboros-blue-merged/
  5. Writes merge_manifest.json with full provenance

Memory requirements
-------------------
  Merging does NOT require 4-bit quantization — it requires the full
  float16/bfloat16 weights to be in memory simultaneously.
  Minimum:  ~7 GB VRAM  (bf16)
  Use --dtype float32 on CPU if VRAM is insufficient (slow but works)

Usage
-----
  # Dry-run (prints config without loading model)
  python scripts/training/merge_adapter.py --dry-run

  # Standard merge (bf16, GPU)
  python scripts/training/merge_adapter.py

  # Custom paths
  python scripts/training/merge_adapter.py \\
      --adapter-dir models/ouroboros-blue-final \\
      --output-dir  models/ouroboros-blue-merged

  # CPU merge (slow, but works without GPU)
  python scripts/training/merge_adapter.py --device cpu --dtype float32
"""

import argparse
import json
import logging
import shutil
import sys
import time
from pathlib import Path
from typing import Dict, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("merge_adapter")

ROOT        = Path(__file__).resolve().parent.parent.parent
ADAPTER_DIR = ROOT / "models" / "ouroboros-blue-final"
MERGED_DIR  = ROOT / "models" / "ouroboros-blue-merged"
CONFIG_PATH = ROOT / "config" / "lora_config.yaml"

# Default base model — reads from adapter_manifest.json if available
DEFAULT_BASE = "Qwen/Qwen2.5-Coder-3B-Instruct"

# ─────────────────────────────────────────────────────────────────────────────
# OPTIONAL HEAVY DEPS
# ─────────────────────────────────────────────────────────────────────────────

try:
    import torch
    _HAS_TORCH = True
except ImportError:
    _HAS_TORCH = False

try:
    from transformers import AutoTokenizer, AutoModelForCausalLM
    from peft import PeftModel
    _HAS_PEFT = True
except ImportError:
    _HAS_PEFT = False


# ─────────────────────────────────────────────────────────────────────────────
# MANIFEST / PROVENANCE
# ─────────────────────────────────────────────────────────────────────────────

def load_adapter_manifest(adapter_dir: Path) -> Optional[Dict]:
    """Read adapter_manifest.json written by checkpoint_manager --export."""
    for fname in ("adapter_manifest.json", "provenance.json"):
        p = adapter_dir / fname
        if p.exists():
            for enc in ("utf-8-sig", "utf-8"):
                try:
                    with p.open(encoding=enc) as f:
                        return json.load(f)
                except (json.JSONDecodeError, OSError):
                    continue
    return None


def read_base_model_name(adapter_dir: Path, fallback: str) -> str:
    """
    Determine the base model name in priority order:
      1. adapter_manifest.json  (written by checkpoint_manager --export)
      2. adapter_config.json    (written by PEFT on save)
      3. --base-model CLI arg / fallback default
    """
    manifest = load_adapter_manifest(adapter_dir)
    if manifest and manifest.get("base_model"):
        return manifest["base_model"]

    adapter_cfg = adapter_dir / "adapter_config.json"
    if adapter_cfg.exists():
        try:
            cfg = json.loads(adapter_cfg.read_text(encoding="utf-8"))
            if cfg.get("base_model_name_or_path"):
                return cfg["base_model_name_or_path"]
        except Exception:
            pass

    return fallback


def write_merge_manifest(
    output_dir:  Path,
    adapter_dir: Path,
    base_model:  str,
    dtype:       str,
    adapter_manifest: Optional[Dict],
) -> None:
    """Write merge_manifest.json to the output directory."""
    manifest = {
        "schema_version":  "1.0",
        "merged_at":       time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model_type":      "merged_lora",
        "base_model":      base_model,
        "adapter_dir":     str(adapter_dir),
        "output_dir":      str(output_dir),
        "dtype":           dtype,
        "peft_method":     "LoRA",
        "merge_method":    "merge_and_unload",
        # Inherit provenance from the adapter manifest if available
        "adapter_step":    (adapter_manifest or {}).get("step"),
        "adapter_eval_loss": (adapter_manifest or {}).get("eval_loss"),
        "adapter_epoch":   (adapter_manifest or {}).get("epoch"),
        "adapter_exported_at": (adapter_manifest or {}).get("exported_at"),
        "ready_for_inference": True,
        "note": (
            "This is a MERGED model (no adapter files needed). "
            "Load with AutoModelForCausalLM.from_pretrained() directly."
        ),
    }
    out_path = output_dir / "merge_manifest.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    logger.info(f"Merge manifest: {out_path}")


# ─────────────────────────────────────────────────────────────────────────────
# MERGE LOGIC
# ─────────────────────────────────────────────────────────────────────────────

def run_merge(
    adapter_dir: Path,
    output_dir:  Path,
    base_model:  str,
    dtype:       str,
    device:      str,
    force:       bool,
) -> None:
    """
    Core merge pipeline:
      1. Load base model in specified precision
      2. Attach LoRA adapter via PeftModel
      3. merge_and_unload() → fuses weights permanently
      4. Save merged model + tokenizer
      5. Write merge_manifest.json
    """
    if not _HAS_TORCH:
        raise ImportError("pip install torch")
    if not _HAS_PEFT:
        raise ImportError("pip install transformers peft")

    t0 = time.time()

    # Validate adapter dir
    if not adapter_dir.exists():
        raise FileNotFoundError(
            f"Adapter directory not found: {adapter_dir}\n"
            "  Run: python scripts/training/checkpoint_manager.py --export"
        )

    adapter_cfg = adapter_dir / "adapter_config.json"
    if not adapter_cfg.exists():
        raise FileNotFoundError(
            f"adapter_config.json not found in {adapter_dir}\n"
            "  This does not look like a valid PEFT adapter directory."
        )

    # Resolve base model
    base_model = read_base_model_name(adapter_dir, base_model)
    adapter_manifest = load_adapter_manifest(adapter_dir)
    logger.info(f"Base model     : {base_model}")
    logger.info(f"Adapter dir    : {adapter_dir}")
    logger.info(f"Output dir     : {output_dir}")
    logger.info(f"Dtype          : {dtype}   Device: {device}")

    # Guard: output dir already exists
    if output_dir.exists() and not force:
        logger.warning(
            f"Output dir already exists: {output_dir}\n"
            "  Use --force to overwrite, or --output-dir to choose another path."
        )
        return
    if output_dir.exists() and force:
        logger.info(f"Removing existing dir: {output_dir}")
        shutil.rmtree(output_dir)

    # Map dtype string → torch.dtype
    dtype_map = {
        "float16":  torch.float16,
        "bfloat16": torch.bfloat16,
        "float32":  torch.float32,
    }
    torch_dtype = dtype_map.get(dtype, torch.bfloat16)

    # 1. Load base model
    logger.info("Loading base model...")
    base = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype  = torch_dtype,
        device_map   = device if device != "cpu" else None,
        trust_remote_code = True,
    )
    if device == "cpu":
        base = base.to("cpu")

    # 2. Load tokenizer
    logger.info("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)

    # 3. Attach LoRA adapter
    logger.info("Attaching LoRA adapter...")
    model = PeftModel.from_pretrained(
        base,
        str(adapter_dir),
        torch_dtype = torch_dtype,
    )

    # 4. Merge weights permanently
    logger.info("Merging LoRA weights into base (merge_and_unload)...")
    model = model.merge_and_unload()

    # 5. Save merged model + tokenizer
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Saving merged model to {output_dir}...")
    model.save_pretrained(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    # 6. Write manifest
    write_merge_manifest(output_dir, adapter_dir, base_model, dtype, adapter_manifest)

    elapsed = time.time() - t0
    logger.info(f"Merge complete in {elapsed:.1f}s")
    logger.info(f"Merged model saved to: {output_dir}")
    logger.info(
        f"\n  To use the merged model:\n"
        f"    from transformers import AutoModelForCausalLM, AutoTokenizer\n"
        f"    model     = AutoModelForCausalLM.from_pretrained('{output_dir}')\n"
        f"    tokenizer = AutoTokenizer.from_pretrained('{output_dir}')\n"
        f"\n  To run evaluation on the merged model:\n"
        f"    python scripts/evaluation/generate_patches.py \\\\\n"
        f"        --adapter-path {output_dir}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# DRY RUN
# ─────────────────────────────────────────────────────────────────────────────

def dry_run(adapter_dir: Path, output_dir: Path, base_model: str, dtype: str, device: str) -> None:
    """Print merge configuration without loading anything."""
    resolved_base = read_base_model_name(adapter_dir, base_model)
    manifest      = load_adapter_manifest(adapter_dir)

    print(f"\n{'=' * 64}")
    print(f"  MERGE ADAPTER  Dry-Run  (Task 8.3)")
    print(f"{'─' * 64}")
    print(f"  Adapter dir    : {adapter_dir}")
    print(f"    exists       : {adapter_dir.exists()}")
    cfg_ok = (adapter_dir / "adapter_config.json").exists()
    print(f"    adapter_config.json: {'found' if cfg_ok else 'MISSING'}")

    if manifest:
        print(f"\n  Adapter manifest (from checkpoint_manager --export):")
        print(f"    base_model   : {manifest.get('base_model', 'N/A')}")
        print(f"    eval_loss    : {manifest.get('eval_loss', 'N/A')}")
        print(f"    step         : {manifest.get('step', 'N/A')}")
        print(f"    epoch        : {manifest.get('epoch', 'N/A')}")
        print(f"    exported_at  : {manifest.get('exported_at', 'N/A')}")
    else:
        print(f"\n  adapter_manifest.json: not found")
        print(f"    Run: python scripts/training/checkpoint_manager.py --export")

    print(f"\n  Merge config:")
    print(f"    Base model   : {resolved_base}")
    print(f"    Output dir   : {output_dir}")
    print(f"    Dtype        : {dtype}")
    print(f"    Device       : {device}")

    print(f"\n  Dependencies:")
    for pkg, ok in [("torch", _HAS_TORCH), ("peft", _HAS_PEFT)]:
        print(f"    {pkg:<16} {'OK' if ok else 'NOT INSTALLED'}")

    print(f"\n  Estimated VRAM needed: ~7 GB (bf16) | ~14 GB (float32)")
    print(f"  Note: merge_and_unload() cannot be done in 4-bit QLoRA.")
    print(f"        Base model must be loaded in float16 or bfloat16.")
    print(f"{'=' * 64}\n")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Ouroboros - LoRA Weight Merger (Task 8.3)",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--adapter-dir",  type=Path, default=ADAPTER_DIR,
                        help=f"LoRA adapter directory (default: {ADAPTER_DIR})")
    parser.add_argument("--output-dir",   type=Path, default=MERGED_DIR,
                        help=f"Save merged model here (default: {MERGED_DIR})")
    parser.add_argument("--base-model",   type=str,  default=DEFAULT_BASE,
                        help="Base HF model repo (overridden by adapter_manifest.json)")
    parser.add_argument("--dtype",        type=str,  default="bfloat16",
                        choices=["bfloat16", "float16", "float32"],
                        help="Weight dtype for loading (default: bfloat16)")
    parser.add_argument("--device",       type=str,  default="auto",
                        help="Device map: 'auto', 'cpu', 'cuda:0' (default: auto)")
    parser.add_argument("--force",        action="store_true",
                        help="Overwrite existing output dir")
    parser.add_argument("--dry-run",      action="store_true",
                        help="Print config without loading model")
    return parser.parse_args()


def main():
    args = parse_args()
    logger.info("=" * 60)
    logger.info("Ouroboros -- LoRA Weight Merger  (Task 8.3)")
    logger.info("=" * 60)

    if args.dry_run:
        dry_run(args.adapter_dir, args.output_dir, args.base_model, args.dtype, args.device)
        return

    run_merge(
        adapter_dir = args.adapter_dir,
        output_dir  = args.output_dir,
        base_model  = args.base_model,
        dtype       = args.dtype,
        device      = args.device,
        force       = args.force,
    )


if __name__ == "__main__":
    main()
