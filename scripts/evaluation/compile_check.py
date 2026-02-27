"""
Ouroboros AI - Compilation Checker  (Tasks 5.2 / 9.2)
======================================================
Language-aware compilation / syntax check for generated patches.
Subprocess exit codes are the source of truth — compiler stdout/stderr
are parsed to extract human-readable error lines.

Supported languages and tools:
  Python     -> py_compile (stdlib) + ast.parse
  JavaScript -> node --check          (exit 0=OK, non-zero=error)
  Java       -> javac -Xlint:none     (exit 0=OK, non-zero=error)
  C          -> gcc -fsyntax-only     (exit 0=OK, non-zero=error)
  C++        -> g++ -fsyntax-only     (exit 0=OK, non-zero=error)
  Go         -> go build              (exit 0=OK, non-zero=error)
  Rust       -> rustc --emit=metadata (exit 0=OK, non-zero=error)

Usage
-----
  python scripts/evaluation/compile_check.py --patches data/evaluation/generated_patches.jsonl
  python scripts/evaluation/compile_check.py --tool-status
  python scripts/evaluation/compile_check.py --timeout 45
"""

import argparse, ast, json, logging, os, py_compile, re, shutil
import subprocess, sys, tempfile
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
logger = logging.getLogger("compile_check")

ROOT         = Path(__file__).resolve().parent.parent.parent
PATCHES_FILE = ROOT / "data" / "evaluation" / "generated_patches.jsonl"
OUTPUT_FILE  = ROOT / "data" / "evaluation" / "compile_results.jsonl"

TOOLS = {
    "python":  sys.executable,
    "node":    shutil.which("node"),
    "javac":   shutil.which("javac"),
    "gcc":     shutil.which("gcc"),
    "g++":     shutil.which("g++"),
    "cl":      shutil.which("cl"),
    "go":      shutil.which("go"),
    "rustc":   shutil.which("rustc"),
}

LANG_EXTS = {
    "python": ".py", "javascript": ".js", "typescript": ".ts",
    "java": ".java", "c": ".c", "cpp": ".cpp", "c++": ".cpp",
    "go": ".go", "rust": ".rs",
}


def print_tool_status() -> None:
    print("\n  Compilation Tool Availability:")
    for tool, path in TOOLS.items():
        print(f"    {tool:<12}  {path or 'NOT FOUND'}")
    print()


def _tmpfile(code: str, suffix: str) -> str:
    with tempfile.NamedTemporaryFile(suffix=suffix, mode="w",
                                     encoding="utf-8", delete=False) as f:
        f.write(code)
        return f.name


def _run(cmd: List[str], timeout: int = 30) -> Tuple[int, str, str]:
    """
    Run a subprocess command, return (returncode, stdout, stderr).
    Returns (-1, '', 'Timeout') on timeout or unexpected OS error.
    The exit code is the primary signal — 0=success, non-zero=failure.
    """
    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        logger.warning(f"Compiler timeout ({timeout}s): {cmd[0]}")
        return -1, "", f"Timeout after {timeout}s"
    except FileNotFoundError:
        return -1, "", f"Compiler not found: {cmd[0]}"
    except Exception as e:
        return -1, "", str(e)



# ── Python ───────────────────────────────────────────────────────────────────

def check_python(code: str) -> Tuple[bool, str, List[str], List[str]]:
    try:
        ast.parse(code)
    except SyntaxError as e:
        return False, "ast.parse", [f"SyntaxError: {e}"], []

    tmp = _tmpfile(code, ".py")
    try:
        py_compile.compile(tmp, doraise=True)
        return True, "py_compile", [], []
    except py_compile.PyCompileError as e:
        return False, "py_compile", [str(e)], []
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


# ── JavaScript ───────────────────────────────────────────────────────────────

def check_javascript(code: str) -> Tuple[bool, str, List[str], List[str]]:
    if not TOOLS["node"]:
        return True, "unsupported", [], ["node not found on PATH"]
    tmp = _tmpfile(code, ".js")
    try:
        rc, _, stderr = _run([TOOLS["node"], "--check", tmp])
        errors = [l for l in stderr.splitlines()
                  if l.strip() and any(k in l for k in ("Error:", "SyntaxError"))]
        return rc == 0, "node --check", errors, []
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


# ── Java ─────────────────────────────────────────────────────────────────────

def check_java(code: str) -> Tuple[bool, str, List[str], List[str]]:
    if not TOOLS["javac"]:
        return True, "unsupported", [], ["javac not found on PATH"]
    m = re.search(r"\bpublic\s+class\s+(\w+)", code)
    class_name = m.group(1) if m else "Snippet"
    with tempfile.TemporaryDirectory() as tmpdir:
        java_file = Path(tmpdir) / f"{class_name}.java"
        java_file.write_text(code, encoding="utf-8")
        rc, stdout, stderr = _run([TOOLS["javac"], "-Xlint:none", "-nowarn", str(java_file)])
        all_out = (stdout + stderr).splitlines()
        errors   = [l for l in all_out if "error:" in l.lower()]
        warnings = [l for l in all_out if "warning:" in l.lower()]
        return rc == 0, "javac", errors, warnings


# ── C / C++ ──────────────────────────────────────────────────────────────────

def check_c(code: str, is_cpp: bool = False, timeout: int = 30) -> Tuple[bool, str, List[str], List[str]]:
    """
    Run gcc/g++ -fsyntax-only on C/C++ code (Task 9.2).
    Exit code 0 = compiles clean, non-zero = syntax/type errors.
    stderr contains compiler diagnostics; we filter to error:/warning: lines.
    """
    compiler = TOOLS.get("g++" if is_cpp else "gcc") or TOOLS.get("cl")
    if not compiler:
        return True, "unsupported", [], ["gcc/g++ not found on PATH"]
    suffix = ".cpp" if is_cpp else ".c"
    tmp = _tmpfile(code, suffix)
    try:
        if "cl.exe" in str(compiler):
            # MSVC syntax check
            cmd = [compiler, "/Zs", "/nologo", tmp]
        else:
            flag = "-std=c++17" if is_cpp else "-std=c11"
            cmd  = [compiler, "-fsyntax-only", flag, "-Wall", tmp]
        rc, stdout, stderr = _run(cmd, timeout=timeout)
        all_out  = (stdout + stderr).splitlines()
        # Extract structured compiler messages
        errors   = [l.strip() for l in all_out
                    if "error:" in l.lower() and l.strip()]
        warnings = [l.strip() for l in all_out
                    if "warning:" in l.lower() and l.strip()]
        name = ("g++" if is_cpp else "gcc") + " -fsyntax-only"
        # Log first error for immediate visibility
        if errors:
            logger.debug(f"  {name} error: {errors[0][:80]}")
        return rc == 0, name, errors[:5], warnings[:3]
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass



# ── Go ───────────────────────────────────────────────────────────────────────

def check_go(code: str) -> Tuple[bool, str, List[str], List[str]]:
    if not TOOLS["go"]:
        return True, "unsupported", [], ["go not found on PATH"]
    with tempfile.TemporaryDirectory() as tmpdir:
        if "package " not in code:
            code = "package main\n\n" + code
        go_file = Path(tmpdir) / "main.go"
        go_file.write_text(code, encoding="utf-8")
        rc, stdout, stderr = _run([TOOLS["go"], "build", "-o", os.devnull, str(go_file)])
        all_out  = (stdout + stderr).splitlines()
        errors   = [l for l in all_out if "error" in l.lower()]
        warnings = [l for l in all_out if "warning" in l.lower()]
        return rc == 0, "go build", errors, warnings


# ── Rust ─────────────────────────────────────────────────────────────────────

def check_rust(code: str) -> Tuple[bool, str, List[str], List[str]]:
    if not TOOLS["rustc"]:
        return True, "unsupported", [], ["rustc not found on PATH"]
    tmp = _tmpfile(code, ".rs")
    try:
        rc, stdout, stderr = _run([
            TOOLS["rustc"], "--edition", "2021", "--emit=metadata", "-o", os.devnull, tmp
        ])
        all_out  = (stdout + stderr).splitlines()
        errors   = [l for l in all_out if "error" in l.lower()]
        warnings = [l for l in all_out if "warning" in l.lower()]
        return rc == 0, "rustc", errors, warnings
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# DISPATCHER
# ─────────────────────────────────────────────────────────────────────────────

def check_code(code: str, language: str) -> Tuple[bool, str, List[str], List[str]]:
    lang = language.lower().strip()
    if lang == "python":            return check_python(code)
    elif lang in ("javascript","js"): return check_javascript(code)
    elif lang == "java":            return check_java(code)
    elif lang == "c":               return check_c(code, is_cpp=False)
    elif lang in ("c++", "cpp"):    return check_c(code, is_cpp=True)
    elif lang == "go":              return check_go(code)
    elif lang == "rust":            return check_rust(code)
    else:
        return True, "unsupported", [], [f"No checker for: {language}"]


# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

def run_compile_check(patches_file: Path, output_file: Path) -> List[Dict]:
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

    output_file.parent.mkdir(parents=True, exist_ok=True)
    results = []

    with output_file.open("w", encoding="utf-8") as out_f:
        for entry in entries:
            lang  = entry.get("language", "unknown")
            patch = entry.get("generated_patch", "")
            ok, checker, errors, warnings = check_code(patch, lang)
            verdict = "UNSUPPORTED" if checker == "unsupported" else ("PASS" if ok else "FAIL")

            result = {
                "id":         entry.get("id", "?"),
                "language":   lang,
                "compile_ok": ok,
                "checker":    checker,
                "errors":     errors[:5],
                "warnings":   warnings[:3],
                "verdict":    verdict,
            }
            results.append(result)
            out_f.write(json.dumps(result) + "\n")

            icon = "PASS" if ok else ("????" if verdict == "UNSUPPORTED" else "FAIL")
            logger.info(
                f"  [{icon}] {entry.get('id','?')}  {lang} via {checker}"
                + (f"  -> {errors[0][:60]}" if errors else "")
            )

    return results


def print_summary(results: List[Dict]) -> None:
    total  = len(results)
    passed = sum(1 for r in results if r["verdict"] == "PASS")
    failed = sum(1 for r in results if r["verdict"] == "FAIL")
    unsup  = sum(1 for r in results if r["verdict"] == "UNSUPPORTED")

    print(f"\n{'=' * 62}")
    print(f"  Compilation Summary  (Task 5.2)")
    print(f"{'─' * 62}")
    print(f"  Total   : {total}")
    print(f"  PASS    : {passed}  ({passed/total*100:.0f}%)")
    print(f"  FAIL    : {failed}")
    print(f"  UNSUP   : {unsup}")
    print(f"{'─' * 62}")
    for r in results:
        icon = "+" if r["verdict"] == "PASS" else ("?" if r["verdict"] == "UNSUPPORTED" else "X")
        print(f"  [{icon}] {r['id']:<14}  {r['language']:<14}  {r['checker']:<22}  {r['verdict']}")
        for e in r.get("errors", [])[:2]:
            print(f"        {e[:70]}")
    print(f"{'=' * 62}\n")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Ouroboros - Compilation Checker (Tasks 5.2 / 9.2)",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--patches",     type=Path, default=PATCHES_FILE)
    parser.add_argument("--output",      type=Path, default=OUTPUT_FILE)
    parser.add_argument("--timeout",     type=int,  default=30,
                        help="Per-compiler subprocess timeout in seconds (default: 30)")
    parser.add_argument("--tool-status", action="store_true",
                        help="Print available compilers and exit")
    return parser.parse_args()


def main():
    args = parse_args()
    logger.info("=" * 60)
    logger.info("Ouroboros -- Compilation Check  (Task 5.2)")
    logger.info("=" * 60)
    print_tool_status()
    if args.tool_status:
        return
    results = run_compile_check(args.patches, args.output)
    print_summary(results)
    print(f"  Results written to: {args.output}\n")


if __name__ == "__main__":
    main()
