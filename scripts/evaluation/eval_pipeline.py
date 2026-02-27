"""
Ouroboros AI - Evaluation Pipeline  (Tasks 5.1 + 5.2 + 10.1 + 10.2)
======================================================================
Master orchestrator that chains:
  1. generate_patches.py  – run model inference on test.jsonl
  2. sast_check.py        – Semgrep SAST on vuln vs patch
  3. compile_check.py     – language-aware compilation check
  4. self_correct.py      – autonomous feedback loop (Tasks 10.1 / 10.2)
                             inject error logs → retry until pass or exhausted
And produces a unified JSON + text summary report.

A patch is considered FULLY SUCCESSFUL only when:
  - SAST verdict  : MITIGATED or CLEAN   (vulnerability removed)
  - Compile verdict: PASS                 (code still builds)

Self-correction (Task 10.1):
  On first FAIL, exact error logs (compiler lines + Semgrep rule IDs) are
  appended as a correction turn and sent back to the Blue Agent for a retry.
  Retries are capped at --max-retries (default 3, hard ceiling 5).

Partial credit breakdown:
  - SAST only PARTIAL but PASS compile  -> partial credit
  - SAST mitigated but FAIL compile     -> failed (code broken)
  - SAST UNCHANGED, FAIL compile        -> failed entirely

Output files:
  data/evaluation/generated_patches.jsonl
  data/evaluation/sast_results.jsonl
  data/evaluation/compile_results.jsonl
  data/evaluation/self_corrected_patches.jsonl   <- retry results (if --self-correct)
  data/evaluation/eval_report.json               <- unified report
  data/evaluation/eval_summary.txt               <- human-readable summary

Usage
-----
  # Full pipeline with self-correction (mock mode)
  python scripts/evaluation/eval_pipeline.py --mock --self-correct

  # Full pipeline, live Ollama inference, 3 retries max
  python scripts/evaluation/eval_pipeline.py --self-correct --backend ollama --max-retries 3

  # Skip self-correction
  python scripts/evaluation/eval_pipeline.py --mock

  # Skip generation (reuse existing patches)
  python scripts/evaluation/eval_pipeline.py --skip-generation

  # Just check tool availability
  python scripts/evaluation/eval_pipeline.py --dry-run
"""

import argparse
import json
import logging
import sys
import time
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
logger = logging.getLogger("eval_pipeline")

ROOT       = Path(__file__).resolve().parent.parent.parent
EVAL_DIR   = ROOT / "data" / "evaluation"
TEST_FILE  = ROOT / "data" / "splits" / "test.jsonl"
MODEL_PATH = ROOT / "models" / "ouroboros-blue-final"

# Local script imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

import generate_patches as gp
import sast_check       as sc
import compile_check    as cc
import self_correct     as scr


# ─────────────────────────────────────────────────────────────────────────────
# MERGE RESULTS
# ─────────────────────────────────────────────────────────────────────────────

SAST_SUCCESS  = {"MITIGATED", "CLEAN"}
COMPILE_SUCCESS = {"PASS"}

def compute_final_verdict(
    sast_verdict: str,
    compile_verdict: str,
) -> Dict[str, object]:
    """
    Combine SAST and compile verdicts into a final pass/fail with score.

    Score (0.0 - 1.0):
      1.0  : SAST mitigated + compile pass     — full success
      0.5  : SAST partial   + compile pass     — partial
      0.5  : SAST mitigated + compile unsup    — tool not available for lang
      0.25 : SAST unchanged + compile pass     — builds but vuln remains
      0.0  : compile fail                      — code is broken
    """
    sast_ok    = sast_verdict in SAST_SUCCESS
    compile_ok = compile_verdict == "PASS"
    compile_na = compile_verdict == "UNSUPPORTED"

    if sast_ok and compile_ok:
        verdict = "SUCCESS"
        score   = 1.0
    elif sast_ok and compile_na:
        verdict = "SUCCESS_UNVERIFIED_BUILD"
        score   = 0.5
    elif sast_verdict == "PARTIAL" and compile_ok:
        verdict = "PARTIAL_MITIGATION"
        score   = 0.5
    elif sast_ok and not compile_ok:
        verdict = "VULN_FIXED_BUILD_BROKEN"
        score   = 0.0
    elif not sast_ok and compile_ok:
        verdict = "BUILDS_VULN_REMAINS"
        score   = 0.25
    else:
        verdict = "FAIL"
        score   = 0.0

    return {
        "final_verdict": verdict,
        "score":         score,
        "sast_ok":       sast_ok,
        "compile_ok":    compile_ok,
    }


def merge_results(
    patches:  List[Dict],
    sast:     List[Dict],
    compiles: List[Dict],
) -> List[Dict]:
    """Merge all three result lists by ID."""
    sast_by_id    = {r["id"]: r for r in sast}
    compile_by_id = {r["id"]: r for r in compiles}

    merged = []
    for p in patches:
        pid = p["id"]
        s   = sast_by_id.get(pid, {})
        c   = compile_by_id.get(pid, {})

        final = compute_final_verdict(
            s.get("verdict", "UNKNOWN"),
            c.get("verdict", "UNSUPPORTED"),
        )

        merged.append({
            # Patch metadata
            "id":              pid,
            "language":        p.get("language", "unknown"),
            "vulnerability":   p.get("vulnerability", "unknown"),
            "criticality":     p.get("criticality", "unknown"),
            "source":          p.get("source", "unknown"),
            # SAST
            "sast_tool":           s.get("sast_tool", "none"),
            "sast_verdict":        s.get("verdict", "UNKNOWN"),
            "sast_mitigated":      s.get("mitigated", False),
            "sast_details":        s.get("details", ""),
            "vuln_sec_count":      s.get("vuln_sec_count", 0),
            "patch_sec_count":     s.get("patch_sec_count", 0),
            # Compile
            "compile_checker":     c.get("checker", "none"),
            "compile_verdict":     c.get("verdict", "UNSUPPORTED"),
            "compile_ok":          c.get("compile_ok", True),
            "compile_errors":      c.get("errors", []),
            # Final
            **final,
        })
    return merged


# ─────────────────────────────────────────────────────────────────────────────
# REPORT GENERATION
# ─────────────────────────────────────────────────────────────────────────────

def compute_metrics(merged: List[Dict]) -> Dict:
    n = len(merged)
    if n == 0:
        return {}
    return {
        "total":               n,
        "success":             sum(1 for r in merged if r["final_verdict"] == "SUCCESS"),
        "partial":             sum(1 for r in merged if "PARTIAL" in r["final_verdict"]),
        "fail":                sum(1 for r in merged if r["score"] == 0.0),
        "build_broken":        sum(1 for r in merged if not r["compile_ok"]),
        "vuln_mitigated":      sum(1 for r in merged if r["sast_mitigated"]),
        "avg_score":           sum(r["score"] for r in merged) / n,
        "sast_mitigation_rate":sum(1 for r in merged if r["sast_mitigated"]) / n,
        "compile_pass_rate":   sum(1 for r in merged
                                   if r["compile_verdict"] in ("PASS", "UNSUPPORTED")) / n,
        # Retry stats (Task 10.2) — only meaningful when --self-correct is used
        "needed_retry":        sum(1 for r in merged if r.get("attempts", 1) > 1),
        "exhausted_retries":   sum(1 for r in merged if r.get("exhausted_retries", False)),
        "avg_attempts":        sum(r.get("attempts", 1) for r in merged) / n,
    }


def format_text_report(merged: List[Dict], metrics: Dict, elapsed: float) -> str:
    lines = []
    lines.append("=" * 70)
    lines.append("  OUROBOROS EVALUATION REPORT  (Tasks 5.1 + 5.2 + 10.1 + 10.2)")
    lines.append("=" * 70)
    lines.append(f"  Total patches    : {metrics['total']}")
    lines.append(f"  SUCCESS          : {metrics['success']}  "
                 f"(SAST mitigated + builds)")
    lines.append(f"  PARTIAL          : {metrics['partial']}")
    lines.append(f"  FAIL             : {metrics['fail']}")
    lines.append(f"  Average score    : {metrics['avg_score']:.2f} / 1.00")
    lines.append(f"  SAST mit. rate   : {metrics['sast_mitigation_rate']*100:.0f}%")
    lines.append(f"  Compile pass rate: {metrics['compile_pass_rate']*100:.0f}%")
    # Retry stats (Task 10.2)
    if metrics.get("avg_attempts", 1) > 1 or metrics.get("needed_retry", 0) > 0:
        lines.append(f"  Needed retry     : {metrics.get('needed_retry', 0)}")
        lines.append(f"  Retries exhausted: {metrics.get('exhausted_retries', 0)}")
        lines.append(f"  Avg attempts     : {metrics.get('avg_attempts', 1):.1f}")
    lines.append(f"  Elapsed          : {elapsed:.1f}s")
    lines.append("─" * 70)
    lines.append(f"  {'ID':<16}  {'Lang':<12}  {'Vuln':<28}  {'Attempts':>7}  {'Score':>5}  Verdict")
    lines.append("─" * 70)
    for r in merged:
        att = r.get("attempts", 1)
        lines.append(
            f"  {r['id']:<16}  {r['language']:<12}  "
            f"{r['vulnerability'][:26]:<28}  {att:>7}  {r['score']:>5.2f}  "
            f"{r['final_verdict']}"
        )
        if r.get("sast_details"):
            lines.append(f"    SAST    : {r['sast_details']}")
        if r.get("compile_errors"):
            lines.append(f"    Compile : {r['compile_errors'][0][:66]}")
        # Retry history (Task 10.2)
        for h in r.get("attempts_history", [])[1:]:   # skip attempt 0 (initial)
            rids = h.get("active_rule_ids", [])
            cerr = (h.get("compile_errors") or [""])[0][:50]
            lines.append(
                f"    Retry {h['attempt']}: SAST={h['sast_verdict']}  "
                f"compile={h['compile_verdict']}  passed={h['passed']}"
                + (f"  rules={rids}" if rids else "")
                + (f"  err={cerr}" if cerr else "")
            )
    lines.append("=" * 70)
    lines.append("")
    lines.append("  Verdict guide:")
    lines.append("    SUCCESS                 : Vuln fixed, code compiles")
    lines.append("    SUCCESS_UNVERIFIED_BUILD: Vuln fixed, no compiler for language")
    lines.append("    PARTIAL_MITIGATION      : Vuln partially fixed, code compiles")
    lines.append("    VULN_FIXED_BUILD_BROKEN : Vuln fixed but patch breaks build")
    lines.append("    BUILDS_VULN_REMAINS     : Code compiles, vuln not fixed")
    lines.append("    FAIL                    : Both checks failed")
    lines.append("=" * 70)
    return "\n".join(lines)


def save_report(merged: List[Dict], metrics: Dict, elapsed: float) -> None:
    EVAL_DIR.mkdir(parents=True, exist_ok=True)

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_seconds": round(elapsed, 2),
        "metrics": metrics,
        "results": merged,
    }
    json_path = EVAL_DIR / "eval_report.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    txt_path = EVAL_DIR / "eval_summary.txt"
    with txt_path.open("w", encoding="utf-8") as f:
        f.write(format_text_report(merged, metrics, elapsed))

    logger.info(f"Report saved: {json_path}")
    logger.info(f"Summary saved: {txt_path}")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Ouroboros - Evaluation Pipeline (Tasks 5.1 + 5.2 + 10.1 + 10.2)",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--test-file",       type=Path, default=TEST_FILE)
    parser.add_argument("--model-path",      type=str,  default=str(MODEL_PATH))
    parser.add_argument("--mock",            action="store_true",
                        help="Use ground-truth patches (no GPU needed)")
    parser.add_argument("--skip-generation", action="store_true",
                        help="Skip patch generation, reuse generated_patches.jsonl")
    parser.add_argument("--skip-sast",       action="store_true",
                        help="Skip SAST analysis")
    parser.add_argument("--skip-compile",    action="store_true",
                        help="Skip compilation check")
    # Self-correction flags (Tasks 10.1 / 10.2)
    parser.add_argument("--self-correct",    action="store_true",
                        help="Enable autonomous self-correction retry loop (Task 10.1)")
    parser.add_argument("--max-retries",     type=int,  default=3,
                        help=f"Max self-correction retries per patch (default: 3, "
                             f"hard ceiling: {scr.MAX_RETRIES_CAP})")
    parser.add_argument("--backend",         type=str,  default="ollama",
                        choices=["ollama", "lora", "mock"],
                        help="Inference backend for self-correction (default: ollama)")
    parser.add_argument("--adapter-path",    type=str,  default=str(MODEL_PATH),
                        help="LoRA adapter path (for --backend lora)")
    parser.add_argument("--dry-run",         action="store_true",
                        help="Print tool status and exit")
    return parser.parse_args()


def main():
    args = parse_args()
    t0   = time.time()

    logger.info("=" * 60)
    logger.info("Ouroboros -- Evaluation Pipeline  (Tasks 5.1 + 5.2)")
    logger.info("=" * 60)

    patches_file  = EVAL_DIR / "generated_patches.jsonl"
    sast_file     = EVAL_DIR / "sast_results.jsonl"
    compile_file  = EVAL_DIR / "compile_results.jsonl"

    # ── Tool status ───────────────────────────────────────────────────────
    print("\n  SAST Tools:")
    for tool, ok in sc.TOOL_STATUS.items():
        print(f"    {tool:<12} {'OK' if ok else 'NOT FOUND'}")

    print("\n  Compilation Tools:")
    for tool, path in cc.TOOLS.items():
        print(f"    {tool:<12} {path or 'NOT FOUND'}")
    print()

    if args.dry_run:
        logger.info("Dry-run complete. Use --mock to run without a trained model.")
        return

    # ── Step 1: Generate patches ──────────────────────────────────────────
    if not args.skip_generation:
        logger.info("Step 1/3: Generating patches…")
        gp.run_generation(
            test_file      = args.test_file,
            output_file    = patches_file,
            model_path     = args.model_path,
            mock           = args.mock,
            max_new_tokens = 512,
        )
    else:
        logger.info("Step 1/3: Skipping generation (--skip-generation)")

    # ── Step 2: SAST ──────────────────────────────────────────────────────
    sast_results = []
    if not args.skip_sast:
        logger.info("Step 2/3: Running SAST…")
        sast_results = sc.run_sast_check(patches_file, sast_file)
        sc.print_summary(sast_results)
    else:
        logger.info("Step 2/3: Skipping SAST (--skip-sast)")
        if sast_file.exists():
            with sast_file.open(encoding="utf-8") as f:
                sast_results = [json.loads(l) for l in f if l.strip()]

    # ── Step 3: Compile ───────────────────────────────────────────────────
    compile_results = []
    if not args.skip_compile:
        logger.info("Step 3/3: Running compilation checks…")
        compile_results = cc.run_compile_check(patches_file, compile_file)
        cc.print_summary(compile_results)
    else:
        logger.info("Step 3/3: Skipping compile (--skip-compile)")
        if compile_file.exists():
            with compile_file.open(encoding="utf-8") as f:
                compile_results = [json.loads(l) for l in f if l.strip()]

    # ── Step 4: Self-correction loop (Tasks 10.1 / 10.2) ─────────────────
    sc_results = None
    if args.self_correct:
        logger.info(f"Step 4/4: Self-correction loop (backend={args.backend}, "
                    f"max_retries={min(args.max_retries, scr.MAX_RETRIES_CAP)})…")

        # Check Ollama availability before committing
        if args.backend == "ollama" and not args.mock:
            if not scr._ollama_available():
                logger.warning(
                    f"Ollama not reachable. Falling back to mock mode for self-correction.\n"
                    f"  To use Ollama: ollama serve  &&  ollama pull {scr.OLLAMA_MODEL}"
                )
                args.backend = "mock"

        sc_file = EVAL_DIR / "self_corrected_patches.jsonl"
        sc_results = scr.run_self_correction(
            patches_file = patches_file,
            output_file  = sc_file,
            backend      = args.backend,
            mock         = args.mock,
            adapter_path = args.adapter_path,
            max_retries  = args.max_retries,
        )
        scr.print_retry_summary(sc_results)

        # Merge self-corrected SAST/compile results back into the main result set
        # so the final report reflects retried patches, not just first attempts.
        sc_by_id = {r["id"]: r for r in sc_results}
        for i, entry in enumerate(merged):
            pid = entry["id"]
            if pid in sc_by_id:
                sc_r = sc_by_id[pid]
                # Update with self-correction outcome fields
                merged[i]["final_verdict"]   = sc_r.get("final_verdict", entry["final_verdict"])
                merged[i]["score"]           = sc_r.get("score",         entry["score"])
                merged[i]["sast_ok"]         = sc_r.get("sast_ok",       entry["sast_ok"])
                merged[i]["compile_ok"]      = sc_r.get("compile_ok",    entry["compile_ok"])
                merged[i]["attempts"]        = sc_r.get("attempts",      1)
                merged[i]["exhausted_retries"] = sc_r.get("exhausted_retries", False)
                merged[i]["attempts_history"]  = sc_r.get("attempts_history", [])
    else:
        logger.info("Step 4/4: Self-correction skipped (use --self-correct to enable)")

    # ── Merge + Report ────────────────────────────────────────────────────
    patches = []
    if patches_file.exists():
        with patches_file.open(encoding="utf-8") as f:
            patches = [json.loads(l) for l in f if l.strip()]

    merged  = merge_results(patches, sast_results, compile_results)
    metrics = compute_metrics(merged)
    elapsed = time.time() - t0

    save_report(merged, metrics, elapsed)

    # Print to console
    print(format_text_report(merged, metrics, elapsed))


if __name__ == "__main__":
    main()
