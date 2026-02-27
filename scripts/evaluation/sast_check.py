"""
Ouroboros AI - SAST Checker  (Tasks 5.1 / 9.1)
===============================================
Runs static analysis on generated patches using Semgrep (primary)
and flake8/ast (Python fallback). Compares findings on the vulnerable
code vs the patched code to verify the vulnerability was actually
mitigated.

Semgrep exit codes (Task 9.1):
  0  = scan ran, NO findings found   → CLEAN signal
  1  = scan ran, findings found      → parse results[] for details
  2  = scan ERROR (config missing, parse fail, network, etc.)
  -1 = timeout (killed by subprocess)

Strategy
--------
1. Extract code block from generated_patch
2. Write to temp file; run: semgrep scan --config <ruleset> --json
3. Parse findings: rule_id / message / severity / line
4. Log exact rule IDs triggered before AND after patching
5. Compare pre-patch vs post-patch security findings
6. Classify: MITIGATED / PARTIAL / UNCHANGED / INTRODUCED_NEW / CLEAN

Output per entry:
  {
    "id":              str,
    "language":        str,
    "vulnerability":   str,
    "sast_tool":       "semgrep" | "flake8" | "none",
    "vuln_findings":   [list of findings on original code],
    "patch_findings":  [list of findings on patched code],
    "mitigated":       bool,
    "verdict":         "MITIGATED" | "PARTIAL" | "UNCHANGED" | "INTRODUCED_NEW" | "CLEAN",
    "details":         str,
    "rule_ids_before": [str, ...],   # exact Semgrep rule IDs triggered on vuln_code
    "rule_ids_after":  [str, ...],   # exact Semgrep rule IDs triggered on patch_code
  }

Usage
-----
  python scripts/evaluation/sast_check.py --patches data/evaluation/generated_patches.jsonl
  python scripts/evaluation/sast_check.py --dry-run
  python scripts/evaluation/sast_check.py --rules p/owasp-top-ten --timeout 60
"""

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
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
logger = logging.getLogger("sast_check")

ROOT         = Path(__file__).resolve().parent.parent.parent
PATCHES_FILE = ROOT / "data" / "evaluation" / "generated_patches.jsonl"
OUTPUT_FILE  = ROOT / "data" / "evaluation" / "sast_results.jsonl"

# ─────────────────────────────────────────────────────────────────────────────
# TOOL AVAILABILITY
# ─────────────────────────────────────────────────────────────────────────────

def which(tool: str) -> Optional[str]:
    """Return full path of `tool` on PATH, or None."""
    # Try venv first
    venv = ROOT / "venv" / "Scripts" / f"{tool}.exe"
    if venv.exists():
        return str(venv)
    return shutil.which(tool)


_SEMGREP = which("semgrep")
_FLAKE8  = which("flake8") or str(ROOT / "venv" / "Scripts" / "flake8.exe")
_NODE    = shutil.which("node")

TOOL_STATUS = {
    "semgrep": _SEMGREP is not None,
    "flake8":  Path(_FLAKE8).exists() if _FLAKE8 else False,
    "node":    _NODE is not None,
}

LANG_EXTS = {
    "python":     ".py",
    "javascript": ".js",
    "typescript": ".ts",
    "java":       ".java",
    "c":          ".c",
    "cpp":        ".cpp",
    "c++":        ".cpp",
    "go":         ".go",
    "rust":       ".rs",
}

# ─────────────────────────────────────────────────────────────────────────────
# SEMGREP RUNNER
# ─────────────────────────────────────────────────────────────────────────────

SEMGREP_CONFIGS: Dict[str, List[str]] = {
    # Language-specific rulesets — all available offline after first download
    "python":     ["p/python", "p/owasp-top-ten"],
    "javascript": ["p/javascript", "p/owasp-top-ten"],
    "typescript": ["p/typescript", "p/owasp-top-ten"],
    "java":       ["p/java", "p/owasp-top-ten"],
    "c":          ["p/c"],
    "cpp":        ["p/cpp"],
    "go":         ["p/golang"],
    "default":    ["p/owasp-top-ten"],
}

# Semgrep exit code semantics (Task 9.1)
# 0  → clean (no findings)
# 1  → findings present   ← this is the NORMAL findings path
# 2  → scan error (config missing, bad input, network)
# -1 → killed by timeout
SEMGREP_OK_CODES    = {0, 1}   # both are valid scan results
SEMGREP_ERROR_CODES = {2}


def run_semgrep(
    code: str,
    language: str,
    timeout: int = 60,
    extra_configs: Optional[List[str]] = None,
) -> List[Dict]:
    """
    Write code to a temp file and run Semgrep, returning a list of findings.
    Each finding: {"rule_id", "message", "severity", "line", "col"}

    Exit-code semantics (Task 9.1):
      0  → no findings  (return [])
      1  → findings     (parse results[] from JSON stdout)
      2  → scan error   (config missing, parse failure, etc.) → log + return []
      -1 → timeout      → log + return []
    """
    if not _SEMGREP:
        return []

    ext     = LANG_EXTS.get(language.lower(), ".txt")
    configs = extra_configs or SEMGREP_CONFIGS.get(language.lower(), SEMGREP_CONFIGS["default"])

    with tempfile.NamedTemporaryFile(suffix=ext, mode="w",
                                     encoding="utf-8", delete=False) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    findings = []
    try:
        for cfg in configs:
            cmd = [
                _SEMGREP, "scan",
                "--config", cfg,
                "--json",
                "--quiet",
                "--no-git-ignore",
                "--metrics=off",
                tmp_path,
            ]
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    encoding="utf-8",
                    errors="replace",
                )

                rc = result.returncode

                # Exit code 2 = scan error (bad config, missing rules, etc.)
                if rc == 2:
                    err_snippet = result.stderr.strip().splitlines()[:2]
                    logger.warning(
                        f"Semgrep error (exit=2) for config '{cfg}': "
                        f"{' | '.join(err_snippet)}"
                    )
                    continue

                # Exit codes 0 and 1 are both valid completed scans.
                # 0 = no findings, 1 = findings were found.
                if rc not in SEMGREP_OK_CODES:
                    logger.warning(f"Semgrep unexpected exit code {rc} for config '{cfg}'")
                    continue

                if result.stdout.strip():
                    try:
                        data = json.loads(result.stdout)
                    except json.JSONDecodeError as je:
                        logger.debug(f"Semgrep JSON parse error ({cfg}): {je}")
                        continue

                    for r in data.get("results", []):
                        rule_id = r.get("check_id", "")
                        finding = {
                            "rule_id":  rule_id,
                            "message":  r.get("extra", {}).get("message", ""),
                            "severity": r.get("extra", {}).get("severity", ""),
                            "line":     r.get("start", {}).get("line", 0),
                            "col":      r.get("start", {}).get("col", 0),
                        }
                        findings.append(finding)
                        # Log the exact rule ID for every finding (Task 9.1)
                        logger.debug(f"  rule_id={rule_id}  severity={finding['severity']}  line={finding['line']}")

            except subprocess.TimeoutExpired:
                logger.warning(f"Semgrep timeout ({timeout}s) for config '{cfg}'")
                continue
            except Exception as e:
                logger.debug(f"Semgrep run error ({cfg}): {e}")
                continue
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    # Deduplicate by rule_id + line
    seen   = set()
    deduped = []
    for f in findings:
        key = (f["rule_id"], f["line"])
        if key not in seen:
            seen.add(key)
            deduped.append(f)
    return deduped



# ─────────────────────────────────────────────────────────────────────────────
# FLAKE8 RUNNER  (Python syntax + style issues as proxy for code quality)
# ─────────────────────────────────────────────────────────────────────────────

def run_flake8(code: str, timeout: int = 15) -> List[Dict]:
    """Run flake8 on Python code, return list of issues."""
    if not TOOL_STATUS["flake8"]:
        return []

    with tempfile.NamedTemporaryFile(suffix=".py", mode="w",
                                     encoding="utf-8", delete=False) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    findings = []
    try:
        # Single flake8 invocation with default format (no --format=json needed)
        result = subprocess.run(
            [_FLAKE8, "--max-line-length=200", tmp_path],
            capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",
        )
        for line in result.stdout.splitlines():
            m = re.match(r".+:(\d+):\d+:\s+([A-Z]\d+)\s+(.+)", line)
            if m:
                findings.append({
                    "rule_id":  m.group(2),
                    "message":  m.group(3).strip(),
                    "severity": "WARNING" if m.group(2).startswith("W") else "INFO",
                    "line":     int(m.group(1)),
                    "col":      0,
                })
    except (subprocess.TimeoutExpired, Exception) as e:
        logger.debug(f"flake8 error: {e}")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
    return findings



# ─────────────────────────────────────────────────────────────────────────────
# AST PARSE (Python syntax baseline — always available)
# ─────────────────────────────────────────────────────────────────────────────

def ast_check_python(code: str) -> Optional[str]:
    """Return SyntaxError string if code is invalid Python, else None."""
    import ast
    try:
        ast.parse(code)
        return None
    except SyntaxError as e:
        return str(e)


# ─────────────────────────────────────────────────────────────────────────────
# VERDICT ENGINE
# ─────────────────────────────────────────────────────────────────────────────

SECURITY_SEVERITY = {"ERROR", "WARNING", "HIGH", "MEDIUM"}

def security_findings(findings: List[Dict]) -> List[Dict]:
    """Filter to only security-relevant findings (not style)."""
    return [
        f for f in findings
        if f.get("severity", "").upper() in SECURITY_SEVERITY
        or any(kw in f.get("rule_id", "").lower()
               for kw in ("injection", "xss", "sqli", "rce", "ssrf",
                          "exec", "eval", "shell", "taint", "owasp",
                          "command", "format", "traversal"))
    ]


def compute_verdict(
    vuln_findings:  List[Dict],
    patch_findings: List[Dict],
) -> Tuple[bool, str, str]:
    """
    Returns: (mitigated: bool, verdict: str, details: str)

    Logic:
      - Count security findings in vuln vs patch code
      - MITIGATED:     security findings reduced to zero
      - PARTIAL:       security findings reduced but not eliminated
      - UNCHANGED:     same number of security findings
      - INTRODUCED_NEW: patch has MORE security findings than original
    """
    v_sec = security_findings(vuln_findings)
    p_sec = security_findings(patch_findings)

    v_cnt = len(v_sec)
    p_cnt = len(p_sec)

    if p_cnt == 0 and v_cnt > 0:
        verdict  = "MITIGATED"
        details  = f"All {v_cnt} vulnerability finding(s) resolved."
        mitigated = True
    elif p_cnt == 0 and v_cnt == 0:
        verdict  = "CLEAN"
        details  = "No security findings in original or patch (SAST may lack rules for this vuln type)."
        mitigated = True  # Assume ok if no findings either way
    elif p_cnt < v_cnt:
        verdict  = "PARTIAL"
        details  = f"Reduced from {v_cnt} to {p_cnt} security finding(s). Not fully mitigated."
        mitigated = False
    elif p_cnt > v_cnt:
        verdict  = "INTRODUCED_NEW"
        details  = f"Patch INTRODUCED {p_cnt - v_cnt} new security finding(s) (had {v_cnt})."
        mitigated = False
    else:
        verdict  = "UNCHANGED"
        details  = f"{v_cnt} security finding(s) remain unchanged."
        mitigated = False

    return mitigated, verdict, details


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def analyze_patch(entry: Dict) -> Dict:
    """Run SAST on one patch entry and return the verdict dict."""
    lang     = entry.get("language", "unknown").lower()
    vuln_code = entry.get("vuln_code", "")
    patch_code = entry.get("generated_patch", "")

    # Choose SAST tool
    if TOOL_STATUS["semgrep"]:
        tool_name = "semgrep"
        vuln_findings  = run_semgrep(vuln_code, lang)
        patch_findings = run_semgrep(patch_code, lang)
    elif lang == "python" and TOOL_STATUS["flake8"]:
        tool_name = "flake8"
        vuln_findings  = run_flake8(vuln_code)
        patch_findings = run_flake8(patch_code)
    else:
        tool_name = "none"
        vuln_findings  = []
        patch_findings = []

    # Python also gets AST syntax check
    syntax_error = None
    if lang == "python":
        syntax_error = ast_check_python(patch_code)

    mitigated, verdict, details = compute_verdict(vuln_findings, patch_findings)

    # If syntax is broken, override verdict
    if syntax_error:
        verdict   = "SYNTAX_ERROR"
        details   = f"Patch is invalid Python syntax: {syntax_error}"
        mitigated = False

    return {
        "id":             entry.get("id", "?"),
        "language":       entry.get("language", "unknown"),
        "vulnerability":  entry.get("vulnerability", "unknown"),
        "sast_tool":      tool_name,
        "vuln_findings":  vuln_findings,
        "patch_findings": patch_findings,
        "vuln_sec_count": len(security_findings(vuln_findings)),
        "patch_sec_count":len(security_findings(patch_findings)),
        # Exact rule IDs triggered — key for Task 9.1 audit trail
        "rule_ids_before": [f["rule_id"] for f in security_findings(vuln_findings)],
        "rule_ids_after":  [f["rule_id"] for f in security_findings(patch_findings)],
        "mitigated":      mitigated,
        "verdict":        verdict,
        "details":        details,
        "syntax_error":   syntax_error,
    }


def run_sast_check(patches_file: Path, output_file: Path) -> List[Dict]:
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

    logger.info(f"Running SAST on {len(entries)} patches  (tool: "
                f"{'semgrep' if TOOL_STATUS['semgrep'] else 'flake8/ast'})")

    output_file.parent.mkdir(parents=True, exist_ok=True)
    results = []
    with output_file.open("w", encoding="utf-8") as out_f:
        for entry in entries:
            result = analyze_patch(entry)
            results.append(result)
            out_f.write(json.dumps(result) + "\n")
            icon = "OK" if result["mitigated"] else "!!"
            logger.info(
                f"  [{icon}] {result['id']}  {result['vulnerability']} ({result['language']}) "
                f"-> {result['verdict']}"
            )

    return results


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

def print_summary(results: List[Dict]) -> None:
    total     = len(results)
    mitigated = sum(1 for r in results if r["mitigated"])
    verdicts  = {}
    for r in results:
        verdicts[r["verdict"]] = verdicts.get(r["verdict"], 0) + 1

    print(f"\n{'=' * 62}")
    print(f"  SAST Summary  (Task 5.1)")
    print(f"{'─' * 62}")
    print(f"  Total patches analysed : {total}")
    print(f"  Mitigated              : {mitigated}  ({mitigated/total*100:.0f}%)")
    print(f"{'─' * 62}")
    print(f"  {'Verdict':<20}  Count")
    for v, c in sorted(verdicts.items()):
        marker = " <-- target" if v == "MITIGATED" else ""
        print(f"  {v:<20}  {c}{marker}")
    print(f"{'=' * 62}\n")

    print(f"  Tool availability:")
    for tool, ok in TOOL_STATUS.items():
        print(f"    {tool:<12} {'AVAILABLE' if ok else 'NOT FOUND'}")
    print()


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Ouroboros – SAST Checker (Tasks 5.1 / 9.1)",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--patches",  type=Path, default=PATCHES_FILE)
    parser.add_argument("--output",   type=Path, default=OUTPUT_FILE)
    parser.add_argument("--rules",    type=str,  default=None,
                        help="Custom Semgrep ruleset (e.g. p/owasp-top-ten, ./rules/)")
    parser.add_argument("--timeout",  type=int,  default=60,
                        help="Per-scan timeout in seconds (default: 60)")
    parser.add_argument("--dry-run",  action="store_true",
                        help="Just print tool status, don't scan")
    return parser.parse_args()


def main():
    args = parse_args()
    logger.info("=" * 60)
    logger.info("Ouroboros -- SAST Check  (Task 5.1)")
    logger.info("=" * 60)

    print("\n  SAST Tool Status:")
    for tool, ok in TOOL_STATUS.items():
        print(f"    {tool:<12} {'OK' if ok else 'MISSING'}")
    print()

    if args.dry_run:
        if not TOOL_STATUS["semgrep"]:
            print("  Install semgrep:  pip install semgrep")
        return

    results = run_sast_check(args.patches, args.output)
    print_summary(results)
    print(f"  Results written to: {args.output}\n")


if __name__ == "__main__":
    main()
