"""
Ouroboros AI - Patch Generator  (Task 5.1)
==========================================
Runs inference on the test set to generate patches from the fine-tuned
LoRA model.  Falls back to the ground-truth assistant turn (dry-run /
mock mode) when the model is not yet available.

Output format: `data/evaluation/generated_patches.jsonl`
Each line:
  {
    "id":            str,
    "language":      str,
    "vulnerability": str,
    "criticality":   str,
    "vuln_code":     str,   # original vulnerable code from user prompt
    "expected_patch":str,   # ground-truth assistant turn
    "generated_patch":str,  # model output (or ground-truth in mock mode)
    "source":        "model" | "mock" | "ground_truth"
  }

Usage
-----
  # Mock mode (no GPU, uses ground-truth as generated output)
  python scripts/evaluation/generate_patches.py --mock

  # Live inference (requires trained model + GPU)
  python scripts/evaluation/generate_patches.py

  # Custom model path
  python scripts/evaluation/generate_patches.py --model-path models/ouroboros-blue-final
"""

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("generate_patches")

ROOT        = Path(__file__).resolve().parent.parent.parent
TEST_FILE   = ROOT / "data" / "splits" / "test.jsonl"
OUTPUT_DIR  = ROOT / "data" / "evaluation"
OUTPUT_FILE = OUTPUT_DIR / "generated_patches.jsonl"

DEFAULT_MODEL_PATH = (
    os.environ.get("OUROBOROS_MODEL_PATH")
    or str(ROOT / "models" / "ouroboros-blue-final")
)

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
    _HAS_INFERENCE = True
except Exception:
    _HAS_INFERENCE = False


# ─────────────────────────────────────────────────────────────────────────────
# PARSING HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def parse_user_prompt(user_content: str) -> Dict[str, str]:
    """Extract structured fields from a user turn."""
    result: Dict[str, str] = {}
    for field in ("Vulnerability", "Language", "Criticality"):
        match = re.search(rf"^{field}:\s*(.+)$", user_content, re.MULTILINE)
        if match:
            result[field.lower()] = match.group(1).strip()
    code_match = re.search(r"Code:\n(.+)", user_content, re.DOTALL)
    if code_match:
        result["code"] = code_match.group(1).strip()
    return result


def extract_turns(entry: Dict) -> Dict[str, str]:
    """Return system, user, assistant content from a messages entry."""
    turns = {m["role"]: m["content"] for m in entry.get("messages", [])}
    return turns


def build_prompt(system: str, user: str) -> str:
    """Format into Qwen ChatML inference prompt."""
    return (
        f"<|im_start|>system\n{system}<|im_end|>\n"
        f"<|im_start|>user\n{user}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )


# ─────────────────────────────────────────────────────────────────────────────
# MODEL INFERENCE
# ─────────────────────────────────────────────────────────────────────────────

def load_adapter_manifest(adapter_path: str) -> Optional[Dict]:
    """
    Load adapter_manifest.json written by checkpoint_manager --export.
    Returns None if not found (e.g. manually copied adapter).
    """
    manifest_path = Path(adapter_path) / "adapter_manifest.json"
    if not manifest_path.exists():
        return None
    for enc in ("utf-8-sig", "utf-8"):
        try:
            with manifest_path.open(encoding=enc) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
    return None


def print_adapter_banner(adapter_path: str) -> None:
    """Print a clear info block showing which adapter is being used."""
    manifest = load_adapter_manifest(adapter_path)
    print(f"\n  {'─' * 58}")
    print(f"  ADAPTER INFO  (Task 8.2)")
    print(f"  {'─' * 58}")
    print(f"  Adapter path   : {adapter_path}")
    if manifest:
        print(f"  Base model     : {manifest.get('base_model', 'unknown')}")
        print(f"  Adapter type   : {manifest.get('adapter_type', 'LoRA')}")
        print(f"  Trained step   : {manifest.get('step', 'N/A')}")
        print(f"  Eval loss      : {manifest.get('eval_loss', 'N/A')}")
        print(f"  Epoch          : {manifest.get('epoch', 'N/A')}")
        print(f"  Exported at    : {manifest.get('exported_at', 'N/A')}")
    else:
        print(f"  Manifest       : not found (run checkpoint_manager --export)")
    print(f"  {'─' * 58}\n")


def load_model(model_path: str):
    """Load PEFT adapter on top of the base model."""
    if not _HAS_INFERENCE:
        raise ImportError("pip install transformers peft")

    # Print provenance before loading (Task 8.2)
    print_adapter_banner(model_path)

    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Check if this is a PEFT adapter dir (has adapter_config.json)
    adapter_cfg_path = Path(model_path) / "adapter_config.json"
    if adapter_cfg_path.exists():
        adapter_cfg      = json.loads(adapter_cfg_path.read_text(encoding="utf-8"))
        base_model_name  = adapter_cfg.get(
            "base_model_name_or_path", "Qwen/Qwen2.5-Coder-3B-Instruct"
        )
        logger.info(f"Loading base: {base_model_name}")
        base_model = AutoModelForCausalLM.from_pretrained(
            base_model_name, device_map="auto", trust_remote_code=True,
        )
        logger.info(f"Loading LoRA adapter: {model_path}")
        model = PeftModel.from_pretrained(base_model, model_path)
    else:
        # Merged / standalone model
        logger.info(f"Loading standalone model: {model_path}")
        model = AutoModelForCausalLM.from_pretrained(
            model_path, device_map="auto", trust_remote_code=True,
        )
    model.eval()
    return model, tokenizer


def generate_one(model, tokenizer, prompt: str, max_new_tokens: int = 512) -> str:
    """Run inference on a single prompt and return the generated text."""
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens    = max_new_tokens,
            do_sample         = False,
            temperature       = 1.0,
            repetition_penalty= 1.1,
            pad_token_id      = tokenizer.pad_token_id,
            eos_token_id      = tokenizer.eos_token_id,
        )
    # Decode only the newly generated tokens
    new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
    return tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


# ─────────────────────────────────────────────────────────────────────────────
# MOCK GENERATOR (dry-run / pre-training)
# ─────────────────────────────────────────────────────────────────────────────

def mock_generate(turns: Dict[str, str]) -> str:
    """Return the ground-truth assistant turn as a stand-in for model output."""
    return turns.get("assistant", "")


# ─────────────────────────────────────────────────────────────────────────────
# CORE LOOP
# ─────────────────────────────────────────────────────────────────────────────

def run_generation(
    test_file: Path,
    output_file: Path,
    model_path: str,
    mock: bool = False,
    max_new_tokens: int = 512,
) -> List[Dict]:
    if not test_file.exists():
        raise FileNotFoundError(f"Test file not found: {test_file}")

    entries = []
    with test_file.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    logger.info(f"Loaded {len(entries)} test entries from {test_file}")

    model = tokenizer = None
    if not mock:
        if not _HAS_INFERENCE:
            logger.warning(
                "transformers/peft not installed. Falling back to mock mode.\n"
                "  pip install transformers peft accelerate"
            )
            mock = True
        elif not Path(model_path).exists():
            logger.warning(
                f"Model path not found: {model_path}\n"
                "  Run training first:  python scripts/fine_tune_models.py\n"
                "  Falling back to mock mode."
            )
            mock = True
        else:
            logger.info(f"Loading model from {model_path}")
            model, tokenizer = load_model(model_path)

    output_dir = output_file.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    with output_file.open("w", encoding="utf-8") as out_f:
        for i, entry in enumerate(entries):
            turns   = extract_turns(entry)
            meta    = parse_user_prompt(turns.get("user", ""))
            entry_id = f"test_{i:04d}"

            if mock:
                generated = mock_generate(turns)
                source    = "mock_ground_truth"
            else:
                prompt    = build_prompt(turns.get("system", ""), turns.get("user", ""))
                generated = generate_one(model, tokenizer, prompt, max_new_tokens)
                source    = "model"

            result = {
                "id":              entry_id,
                "language":        meta.get("language", "unknown"),
                "vulnerability":   meta.get("vulnerability", "unknown"),
                "criticality":     meta.get("criticality", "unknown"),
                "vuln_code":       meta.get("code", ""),
                "expected_patch":  turns.get("assistant", ""),
                "generated_patch": generated,
                "source":          source,
            }
            results.append(result)
            out_f.write(json.dumps(result) + "\n")

            logger.info(
                f"[{i+1}/{len(entries)}] {entry_id}  "
                f"{meta.get('vulnerability', '?')} ({meta.get('language', '?')})  "
                f"source={source}"
            )

    logger.info(f"Wrote {len(results)} results to {output_file}")
    return results


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ouroboros – Patch Generator (Tasks 5.1 / 8.2)",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--test-file",      type=Path,  default=TEST_FILE)
    parser.add_argument("--output-file",    type=Path,  default=OUTPUT_FILE)
    # --model-path and --adapter-path are identical; adapter-path is the
    # canonical Task 8.2 name pointing to the checkpoint_manager export dir.
    parser.add_argument("--model-path",     type=str,   default=DEFAULT_MODEL_PATH,
                        help=f"Path to model or LoRA adapter (default: {DEFAULT_MODEL_PATH})")
    parser.add_argument("--adapter-path",   type=str,   default=None,
                        help="Alias for --model-path (Task 8.2: use exported adapter dir)")
    parser.add_argument("--mock",           action="store_true",
                        help="Use ground-truth patch as mock model output (no GPU)")
    parser.add_argument("--max-new-tokens", type=int,   default=512)
    return parser.parse_args()


def main():
    args = parse_args()
    logger.info("=" * 60)
    logger.info("Ouroboros -- Patch Generator  (Tasks 5.1 / 8.2)")
    logger.info("=" * 60)

    # --adapter-path overrides --model-path (Task 8.2)
    model_path = args.adapter_path or args.model_path
    if args.adapter_path:
        logger.info(f"Using --adapter-path: {args.adapter_path}")

    results = run_generation(
        args.test_file,
        args.output_file,
        model_path,
        mock           = args.mock,
        max_new_tokens = args.max_new_tokens,
    )
    print(f"\n  Generated {len(results)} patches -> {args.output_file}\n")


if __name__ == "__main__":
    main()
