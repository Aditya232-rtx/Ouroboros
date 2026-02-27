"""
Ouroboros AI - Self-Correction Engine  (Task 10.1 / 10.2)
===========================================================
Autonomous retry loop that feeds compiler and SAST error messages back
into the Blue Agent as a structured correction turn, then retries patch
generation until the patch passes both checks or max_retries is exhausted.

Architecture
------------
  Attempt 1: generate_patches.py  --> sast_check + compile_check
  If FAIL:
    build_correction_prompt(original_prompt, patch, sast_errors, compile_errors)
    --> inject as new user turn in ChatML conversation
    --> re-run inference
    --> re-check sast + compile
    ... (repeat up to max_retries times)

Supported inference backends
-----------------------------
  1. Ollama  (local, no VRAM management)
     Model: qwen2.5-coder:3b  (detected via `ollama list`)
     Uses:  http://localhost:11434/api/chat  (JSON streaming)

  2. PEFT LoRA adapter  (HuggingFace + GPU)
     Uses:  generate_patches.load_model() + generate_one()
     Requires:  torch, transformers, peft

  3. Mock  (testing / no GPU)
     Returns the ground-truth patch unchanged (same as --mock)

Retry exit conditions (Task 10.2)
-----------------------------------
  - Attempt passes both SAST (MITIGATED/CLEAN) and compile (PASS)  → SUCCESS
  - max_retries exhausted                                           → FAIL + exhausted_retries=True
  - Unsupported language (compile tool absent)                      → count as partial pass

Usage (standalone)
------------------
  python scripts/evaluation/self_correct.py --test-file data/splits/test.jsonl --mock
  python scripts/evaluation/self_correct.py --backend ollama --max-retries 3
  python scripts/evaluation/self_correct.py --backend lora   --max-retries 5 \\
      --adapter-path models/ouroboros-blue-final
"""

import argparse
import json
import logging
import sys
import time
import urllib.request
import urllib.error
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
logger = logging.getLogger("self_correct")

ROOT         = Path(__file__).resolve().parent.parent.parent
TEST_FILE    = ROOT / "data" / "splits" / "test.jsonl"
EVAL_DIR     = ROOT / "data" / "evaluation"
DEFAULT_ADAPTER = ROOT / "models" / "ouroboros-blue-final"

# Local script imports
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sast_check    as sc
import compile_check as cc

MAX_RETRIES_CAP = 5   # hard ceiling — enforced regardless of --max-retries

# ─────────────────────────────────────────────────────────────────────────────
# OLLAMA BACKEND
# ─────────────────────────────────────────────────────────────────────────────

OLLAMA_URL   = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "qwen2.5-coder:3b"


def _ollama_available() -> bool:
    """Check if Ollama is reachable and the model is loaded."""
    try:
        req  = urllib.request.Request("http://localhost:11434/api/tags")
        resp = urllib.request.urlopen(req, timeout=3)
        data = json.loads(resp.read())
        models = [m.get("name", "") for m in data.get("models", [])]
        return any(OLLAMA_MODEL in m for m in models)
    except Exception:
        return False


def _ollama_chat(messages: List[Dict], timeout: int = 120) -> str:
    """
    POST to Ollama /api/chat with the given messages list.
    Returns the assistant content string.
    """
    payload = json.dumps({
        "model":    OLLAMA_MODEL,
        "messages": messages,
        "stream":   False,
        "options":  {
            "temperature":   0.2,
            "repeat_penalty": 1.1,
            "num_predict":   512,
        },
    }).encode("utf-8")

    req = urllib.request.Request(
        OLLAMA_URL,
        data    = payload,
        headers = {"Content-Type": "application/json"},
        method  = "POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        data = json.loads(resp.read())
        return data.get("message", {}).get("content", "").strip()
    except urllib.error.URLError as e:
        raise RuntimeError(f"Ollama request failed: {e}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Ollama JSON parse error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# LORA BACKEND (optional heavy deps)
# ─────────────────────────────────────────────────────────────────────────────

try:
    import generate_patches as gp
    _HAS_GP = True
except ImportError:
    _HAS_GP = False


# ─────────────────────────────────────────────────────────────────────────────
# ERROR EXTRACTION HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def extract_sast_errors(sast_result: Dict) -> List[str]:
    """
    Pull the most actionable SAST signals from a sast_check result dict.
    Returns a list of short error strings for injection into the correction prompt.
    """
    errors = []
    verdict = sast_result.get("verdict", "UNKNOWN")
    details = sast_result.get("details", "")

    if verdict not in ("MITIGATED", "CLEAN"):
        errors.append(f"SAST verdict: {verdict}")
        if details:
            errors.append(f"Details: {details}")

        # Include the exact rule IDs that are still firing (Task 9.1 audit trail)
        rule_ids_after = sast_result.get("rule_ids_after", [])
        if rule_ids_after:
            errors.append(f"Active Semgrep rules still triggered: {', '.join(rule_ids_after)}")

        for finding in sast_result.get("patch_findings", [])[:3]:
            rule  = finding.get("rule_id", "")
            msg   = finding.get("message", "")
            line  = finding.get("line", "?")
            sev   = finding.get("severity", "")
            if rule or msg:
                errors.append(f"  [{sev}] {rule} @ line {line}: {msg[:100]}")

    if sast_result.get("syntax_error"):
        errors.append(f"Syntax error: {sast_result['syntax_error']}")

    return errors


def extract_compile_errors(compile_result: Dict) -> List[str]:
    """
    Pull compiler error messages from a compile_check result dict.
    Returns a list of short error strings for injection into the correction prompt.
    """
    errors = []
    if compile_result.get("verdict") == "FAIL":
        checker = compile_result.get("checker", "compiler")
        errors.append(f"Compilation FAILED via {checker} (exit code non-zero)")
        for err in compile_result.get("errors", [])[:5]:
            if err.strip():
                errors.append(f"  {err.strip()[:120]}")
        if not compile_result.get("errors"):
            # Timeout or tool error
            errors.append("  (No error output — possible timeout or tool crash)")
    return errors


# ─────────────────────────────────────────────────────────────────────────────
# CORRECTION PROMPT BUILDER
# ─────────────────────────────────────────────────────────────────────────────

CORRECTION_SYSTEM = """\
You are the Ouroboros Blue Agent — an autonomous vulnerability patch generator.
You previously generated a code patch that FAILED one or more quality checks.
Study the error feedback below carefully and produce a corrected patch that:
  1. Fixes the exact vulnerability described in the original task
  2. Compiles without errors (no syntax errors, no type errors)
  3. Is not flagged by any SAST security rule
Output ONLY the corrected code — no explanations, no markdown fences."""


def build_correction_prompt(
    original_user_turn: str,
    failed_patch:       str,
    sast_errors:        List[str],
    compile_errors:     List[str],
    attempt:            int,
) -> List[Dict]:
    """
    Build a ChatML messages list for the correction attempt.
    Format:
      [system]  → correction instructions
      [user]    → original vulnerability task
      [assistant] → the failed patch
      [user]    → structured error feedback asking for a fix
    """
    # Build the error feedback block
    error_lines = [f"=== Correction Attempt {attempt} — Error Feedback ==="]

    if compile_errors:
        error_lines.append("\n[COMPILE ERRORS — the patch failed to compile]")
        error_lines.extend(compile_errors)

    if sast_errors:
        error_lines.append("\n[SAST SECURITY ERRORS — the vulnerability was not fixed]")
        error_lines.extend(sast_errors)

    error_lines.append(
        "\nPlease output a corrected version of the patch that fixes all errors above."
    )
    feedback_turn = "\n".join(error_lines)

    messages = [
        {"role": "system",    "content": CORRECTION_SYSTEM},
        {"role": "user",      "content": original_user_turn},
        {"role": "assistant", "content": failed_patch},
        {"role": "user",      "content": feedback_turn},
    ]
    return messages


# ─────────────────────────────────────────────────────────────────────────────
# SINGLE-PASS VERDICT (sast + compile on a patch string)
# ─────────────────────────────────────────────────────────────────────────────

SAST_SUCCESS    = {"MITIGATED", "CLEAN"}
COMPILE_SUCCESS = {"PASS", "UNSUPPORTED"}


def evaluate_patch(patch_entry: Dict) -> Tuple[Dict, Dict]:
    """
    Run SAST + compile on a single patch entry dict.
    Returns (sast_result, compile_result).
    """
    sast_r    = sc.analyze_patch(patch_entry)
    lang      = patch_entry.get("language", "unknown")
    patch_str = patch_entry.get("generated_patch", "")
    ok, checker, errors, warnings = cc.check_code(patch_str, lang)
    verdict   = "UNSUPPORTED" if checker == "unsupported" else ("PASS" if ok else "FAIL")
    compile_r = {
        "id":         patch_entry.get("id", "?"),
        "language":   lang,
        "compile_ok": ok,
        "checker":    checker,
        "errors":     errors[:5],
        "warnings":   warnings[:3],
        "verdict":    verdict,
    }
    return sast_r, compile_r


def patch_passed(sast_r: Dict, compile_r: Dict) -> bool:
    """Return True if this patch fully passes both checks."""
    return (
        sast_r.get("verdict") in SAST_SUCCESS
        and compile_r.get("verdict") in COMPILE_SUCCESS
    )


# ─────────────────────────────────────────────────────────────────────────────
# INFERENCE ROUTER
# ─────────────────────────────────────────────────────────────────────────────

def generate_correction(
    messages:     List[Dict],
    backend:      str,
    mock:         bool,
    adapter_path: str,
    _model_cache: dict,
) -> str:
    """
    Route generation to the correct backend.
    _model_cache is a mutable dict used to cache the loaded LoRA model
    across retries to avoid re-loading on every attempt.
    """
    if mock:
        # In mock mode, just return the existing assistant content (last [assistant] turn)
        for m in reversed(messages):
            if m["role"] == "assistant":
                return m["content"]
        return ""

    if backend == "ollama":
        logger.info(f"    Calling Ollama ({OLLAMA_MODEL})…")
        return _ollama_chat(messages)

    if backend == "lora":
        if not _HAS_GP:
            raise ImportError("pip install transformers peft torch")
        if "model" not in _model_cache:
            logger.info(f"    Loading LoRA adapter: {adapter_path}")
            model, tokenizer = gp.load_model(adapter_path)
            _model_cache["model"]     = model
            _model_cache["tokenizer"] = tokenizer
        model     = _model_cache["model"]
        tokenizer = _model_cache["tokenizer"]
        # Build a single prompt from the messages list using ChatML format
        prompt = ""
        for m in messages:
            role    = m["role"]
            content = m["content"]
            prompt += f"<|im_start|>{role}\n{content}<|im_end|>\n"
        prompt += "<|im_start|>assistant\n"
        return gp.generate_one(model, tokenizer, prompt)

    raise ValueError(f"Unknown backend: {backend!r}. Use 'ollama', 'lora', or 'mock'.")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN RETRY LOOP (Task 10.1 + 10.2)
# ─────────────────────────────────────────────────────────────────────────────

def retry_until_pass(
    patch_entry:  Dict,
    original_user_turn: str,
    backend:      str,
    mock:         bool,
    adapter_path: str,
    max_retries:  int,
    _model_cache: dict,
) -> Dict:
    """
    Core self-correction loop (Tasks 10.1 + 10.2).

    Attempt 0: evaluate the initial patch as-is.
    Attempts 1..max_retries: build correction prompt from error feedback → re-generate → re-evaluate.

    Returns a result dict with:
      - final_patch, sast_result, compile_result, final_verdict, score
      - attempts_history: list of per-attempt dicts
      - exhausted_retries: bool
    """
    # Cap retries at the hard ceiling
    max_retries = min(max_retries, MAX_RETRIES_CAP)

    current_patch   = patch_entry.copy()
    attempts_history = []
    exhausted        = False

    for attempt in range(max_retries + 1):
        t_start   = time.time()
        logger.info(f"  [Attempt {attempt}/{max_retries}] {patch_entry.get('id', '?')}  "
                    f"patch_len={len(current_patch.get('generated_patch',''))}")

        sast_r, compile_r = evaluate_patch(current_patch)
        elapsed = time.time() - t_start

        sast_v    = sast_r.get("verdict", "UNKNOWN")
        compile_v = compile_r.get("verdict", "UNKNOWN")
        passed    = patch_passed(sast_r, compile_r)

        attempt_record = {
            "attempt":         attempt,
            "patch_snippet":   current_patch.get("generated_patch", "")[:120],
            "sast_verdict":    sast_v,
            "compile_verdict": compile_v,
            "passed":          passed,
            "elapsed_s":       round(elapsed, 2),
        }

        if sast_r.get("rule_ids_after"):
            attempt_record["active_rule_ids"] = sast_r["rule_ids_after"]
        if compile_r.get("errors"):
            attempt_record["compile_errors"] = compile_r["errors"][:3]

        attempts_history.append(attempt_record)

        status = "PASS" if passed else "FAIL"
        logger.info(f"    SAST={sast_v}  compile={compile_v}  → {status}")

        if passed:
            logger.info(f"    SUCCESS on attempt {attempt}")
            break

        if attempt == max_retries:
            exhausted = True
            logger.warning(
                f"    Max retries ({max_retries}) exhausted for "
                f"{patch_entry.get('id', '?')} — final verdict: FAIL"
            )
            break

        # ── Build correction prompt and retry ────────────────────────────
        sast_errors    = extract_sast_errors(sast_r)
        compile_errors = extract_compile_errors(compile_r)

        if not sast_errors and not compile_errors:
            logger.info("    No actionable errors to correct — stopping early")
            break

        logger.info(
            f"    Injecting {len(sast_errors)} SAST + "
            f"{len(compile_errors)} compile error(s) into correction prompt…"
        )

        messages = build_correction_prompt(
            original_user_turn = original_user_turn,
            failed_patch       = current_patch.get("generated_patch", ""),
            sast_errors        = sast_errors,
            compile_errors     = compile_errors,
            attempt            = attempt + 1,
        )

        try:
            new_patch_text = generate_correction(
                messages, backend, mock, adapter_path, _model_cache
            )
        except Exception as e:
            logger.error(f"    Inference error on retry {attempt + 1}: {e}")
            exhausted = True
            break

        # Update the current patch entry for the next evaluation
        current_patch = current_patch.copy()
        current_patch["generated_patch"] = new_patch_text
        current_patch["source"]          = f"self_corrected_attempt_{attempt + 1}"

    # ── Compute final combined verdict ───────────────────────────────────
    from eval_pipeline import compute_final_verdict
    final = compute_final_verdict(sast_v, compile_v)

    return {
        "id":               patch_entry.get("id", "?"),
        "language":         patch_entry.get("language", "unknown"),
        "vulnerability":    patch_entry.get("vulnerability", "unknown"),
        "final_patch":      current_patch.get("generated_patch", ""),
        "attempts":         len(attempts_history),
        "attempts_history": attempts_history,
        "exhausted_retries": exhausted,
        "sast_result":      sast_r,
        "compile_result":   compile_r,
        **final,
    }


# ─────────────────────────────────────────────────────────────────────────────
# BATCH RUNNER
# ─────────────────────────────────────────────────────────────────────────────

def run_self_correction(
    patches_file: Path,
    output_file:  Path,
    backend:      str,
    mock:         bool,
    adapter_path: str,
    max_retries:  int,
) -> List[Dict]:
    """
    Run the self-correction loop over all patches in patches_file.
    Writes per-entry results to output_file (JSONL).
    """
    if not patches_file.exists():
        raise FileNotFoundError(
            f"Patches file not found: {patches_file}\n"
            "  Run: python scripts/evaluation/generate_patches.py --mock"
        )

    entries = []
    with patches_file.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    logger.info(f"Self-correction: {len(entries)} patches  backend={backend}  "
                f"max_retries={min(max_retries, MAX_RETRIES_CAP)}")

    _model_cache = {}   # Shared model cache across all patches
    results      = []

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as out_f:
        for entry in entries:
            # Reconstruct the original user turn so we can replay it in corrections
            turns = {
                m["role"]: m["content"]
                for m in entry.get("_messages_raw", [])
            }
            # Fallback: build user turn from patch entry fields if _messages_raw missing
            if not turns.get("user"):
                user_turn = (
                    f"Vulnerability: {entry.get('vulnerability', 'unknown')}\n"
                    f"Language: {entry.get('language', 'unknown')}\n"
                    f"Code:\n{entry.get('vuln_code', '')}"
                )
            else:
                user_turn = turns["user"]

            result = retry_until_pass(
                patch_entry        = entry,
                original_user_turn = user_turn,
                backend            = backend,
                mock               = mock,
                adapter_path       = adapter_path,
                max_retries        = max_retries,
                _model_cache       = _model_cache,
            )
            results.append(result)
            out_f.write(json.dumps(result) + "\n")

    return results


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY PRINTER
# ─────────────────────────────────────────────────────────────────────────────

def print_retry_summary(results: List[Dict]) -> None:
    total      = len(results)
    succeeded  = sum(1 for r in results if r["score"] >= 1.0)
    exhausted  = sum(1 for r in results if r.get("exhausted_retries"))
    avg_att    = sum(r.get("attempts", 1) for r in results) / total if total else 0
    needed_retry = sum(1 for r in results if r.get("attempts", 1) > 1)

    print(f"\n{'=' * 66}")
    print(f"  SELF-CORRECTION SUMMARY  (Tasks 10.1 / 10.2)")
    print(f"{'─' * 66}")
    print(f"  Total patches        : {total}")
    print(f"  Fully succeeded      : {succeeded}  ({succeeded/total*100:.0f}%)")
    print(f"  Needed retry         : {needed_retry}")
    print(f"  Exhausted retries    : {exhausted}")
    print(f"  Avg attempts/patch   : {avg_att:.1f}")
    print(f"{'─' * 66}")
    for r in results:
        att   = r.get("attempts", 1)
        icon  = "OK" if r["score"] >= 1.0 else ("~~" if r.get("exhausted_retries") else "?!")
        print(
            f"  [{icon}] {r['id']:<14}  {r['language']:<12}  "
            f"attempts={att}  score={r['score']:.2f}  {r['final_verdict']}"
        )
        for h in r.get("attempts_history", []):
            if not h["passed"]:
                rids = h.get("active_rule_ids", [])
                cerr = (h.get("compile_errors") or [""])[0][:50]
                print(
                    f"        attempt {h['attempt']}:  SAST={h['sast_verdict']}  "
                    f"compile={h['compile_verdict']}"
                    + (f"  rules={rids}" if rids else "")
                    + (f"  err={cerr}" if cerr else "")
                )
    print(f"{'=' * 66}\n")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Ouroboros - Self-Correction Engine (Tasks 10.1 / 10.2)",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--patches",      type=Path, default=EVAL_DIR / "generated_patches.jsonl",
                        help="Input patches JSONL file")
    parser.add_argument("--output",       type=Path, default=EVAL_DIR / "self_corrected_patches.jsonl",
                        help="Output self-corrected results JSONL")
    parser.add_argument("--backend",      type=str,  default="ollama",
                        choices=["ollama", "lora", "mock"],
                        help="Inference backend (default: ollama)")
    parser.add_argument("--adapter-path", type=str,  default=str(DEFAULT_ADAPTER),
                        help=f"LoRA adapter dir (for --backend lora, default: {DEFAULT_ADAPTER})")
    parser.add_argument("--max-retries",  type=int,  default=3,
                        help=f"Max retry attempts per patch (default: 3, max: {MAX_RETRIES_CAP})")
    parser.add_argument("--mock",         action="store_true",
                        help="Mock mode: no inference, use ground-truth patch unchanged")
    parser.add_argument("--check-ollama", action="store_true",
                        help="Check if Ollama is reachable and exit")
    return parser.parse_args()


def main():
    args = parse_args()
    logger.info("=" * 60)
    logger.info("Ouroboros -- Self-Correction Engine  (Tasks 10.1 / 10.2)")
    logger.info("=" * 60)

    if args.check_ollama:
        ok = _ollama_available()
        print(f"  Ollama ({OLLAMA_MODEL}): {'AVAILABLE' if ok else 'NOT FOUND'}")
        print(f"  URL: {OLLAMA_URL}")
        return

    if args.backend == "ollama" and not args.mock:
        ok = _ollama_available()
        if not ok:
            logger.warning(
                f"Ollama not reachable or model '{OLLAMA_MODEL}' not loaded.\n"
                f"  Start Ollama:  ollama serve\n"
                f"  Pull model:    ollama pull {OLLAMA_MODEL}\n"
                f"  Falling back to --mock mode."
            )
            args.mock = True

    results = run_self_correction(
        patches_file = args.patches,
        output_file  = args.output,
        backend      = args.backend,
        mock         = args.mock,
        adapter_path = args.adapter_path,
        max_retries  = args.max_retries,
    )

    print_retry_summary(results)
    print(f"  Results: {args.output}\n")


if __name__ == "__main__":
    main()
