"""
Ouroboros AI - Tokenizer & Smart Truncation  (Task 2.3)
========================================================
Applies Qwen 2.5 Coder 3B's ChatML template to all training entries,
counts tokens, and smartly truncates oversized code samples so the context
window focuses on the vulnerable function rather than the entire file.

ChatML format (Qwen 2.5 Coder):
  <|im_start|>system
  {content}<|im_end|>
  <|im_start|>user
  {content}<|im_end|>
  <|im_start|>assistant
  {content}<|im_end|>

Tokenizer priority:
  1. HuggingFace AutoTokenizer (local cache, no network needed)
  2. Char / 4  heuristic  (fast, ≈10% accurate for multilingual code)

Truncation strategy (when entry exceeds --max-tokens):
  1. Extract the vulnerable function/method from the code block
  2. Keep --context-lines around it (default 40 lines)
  3. Append a '# ... [truncated] ...' sentinel
  4. Re-check; if still oversize, hard-truncate tokens on the assistant side

Usage
-----
  # Report-only: show token histogram without writing any files
  python scripts/data_preparation/tokenize_dataset.py --report-only

  # Process all three splits (default paths)
  python scripts/data_preparation/tokenize_dataset.py

  # Process a single file
  python scripts/data_preparation/tokenize_dataset.py \\
      --input data/splits/train.jsonl --output data/splits/train.jsonl

  # Custom token budget (e.g. 8192 for longer context)
  python scripts/data_preparation/tokenize_dataset.py --max-tokens 8192

  # Use specific HF model for tokenization
  python scripts/data_preparation/tokenize_dataset.py \\
      --model Qwen/Qwen2.5-Coder-3B-Instruct
"""

import argparse
import io
import json
import logging
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Force UTF-8 output on Windows so box-drawing/emoji chars don't crash
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("tokenize_dataset")

# ─────────────────────────────────────────────────────────────────────────────
# CHATML TEMPLATE
# ─────────────────────────────────────────────────────────────────────────────

IM_START = "<|im_start|>"
IM_END   = "<|im_end|>"

def apply_chatml(entry: Dict) -> str:
    """
    Format a messages-list entry into Qwen's ChatML string.
    Returns the full formatted string ready for tokenization.
    """
    parts = []
    for msg in entry.get("messages", []):
        role    = msg.get("role", "")
        content = msg.get("content", "")
        parts.append(f"{IM_START}{role}\n{content}{IM_END}\n")
    # Append the generation prompt stub (the model will complete from here)
    parts.append(f"{IM_START}assistant\n")
    return "".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# TOKENIZER WRAPPER
# ─────────────────────────────────────────────────────────────────────────────

class TokenizerWrapper:
    """
    Tiered tokenizer:
      1. HuggingFace AutoTokenizer (local cache, no network I/O)
      2. Char / 4 heuristic fallback
    """

    QWEN_MODEL = "Qwen/Qwen2.5-Coder-3B-Instruct"

    def __init__(self, model_name: Optional[str] = None):
        self._tok = None
        self._mode = "heuristic"
        self._try_load_hf(model_name or self.QWEN_MODEL)

    def _try_load_hf(self, model_name: str) -> None:
        # Suppress stray stderr noise from huggingface_hub (missing urllib3 etc.)
        _old_stderr = sys.stderr
        try:
            sys.stderr = io.StringIO()
            os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
            from transformers import AutoTokenizer  # type: ignore
            self._tok  = AutoTokenizer.from_pretrained(
                model_name,
                local_files_only=True,
                trust_remote_code=True,
            )
            self._mode = "hf"
        except Exception as e:
            pass  # handled below
        finally:
            sys.stderr = _old_stderr

        if self._mode == "hf":
            logger.info(f"Tokenizer: HuggingFace ({model_name})")
        else:
            logger.info("Tokenizer: char/4 heuristic (HF not available locally)")

    @property
    def mode(self) -> str:
        return self._mode

    def count(self, text: str) -> int:
        """Return the estimated token count for `text`."""
        if self._tok is not None:
            return len(self._tok.encode(text, add_special_tokens=False))
        # Heuristic: ~4 chars per token (conservative for code)
        return max(1, len(text) // 4)

    def encode(self, text: str) -> List[int]:
        if self._tok is not None:
            return self._tok.encode(text, add_special_tokens=False)
        # Simple split fallback — character level
        return list(text.encode("utf-8"))

    def decode(self, ids: List[int], text_budget: int) -> str:
        """Return approximately `text_budget` characters (heuristic mode only)."""
        if self._tok is not None:
            return self._tok.decode(ids[:text_budget], skip_special_tokens=True)
        # In heuristic mode the 'ids' are raw bytes
        return bytes(ids[:text_budget]).decode("utf-8", errors="replace")


# ─────────────────────────────────────────────────────────────────────────────
# FUNCTION EXTRACTOR  (language-agnostic heuristic)
# ─────────────────────────────────────────────────────────────────────────────

# Patterns that mark the start of a function/method
_FUNC_START_RE = re.compile(
    r"^(\s*)"                            # leading whitespace
    r"(?:public|private|protected|static|async|export|def|fn|fun|func|void|int|bool|char|uint|size_t|"
    r"unsigned|signed|inline|virtual|override|explicit|constexpr|auto|List|Dict|Optional|str|float|"
    r"double|long|short|byte)[\s\w<>\[\]*&:|,]+"
    r"(?:"
    r"(?:\w+\s*\()"                      # C-family: name(
    r"|(?:def\s+\w+\s*\()"              # Python: def name(
    r"|(?:func\s+\w+\s*\()"            # Go: func name(
    r"|(?:fn\s+\w+\s*\()"              # Rust: fn name(
    r")",
    re.MULTILINE,
)

# Vulnerability markers in the user message
_VULN_KEYWORDS = re.compile(
    r"#\s*(?:VULN|FIX|FIXME|BUG|HACK|XXX|TODO)|"
    r"//\s*(?:VULN|FIX|FIXME|BUG|HACK)|"
    r"/\*.*?(?:VULN|FIX|FIXME|BUG).*?\*/|"
    r'(?i:unsafe|injection|overflow|strcpy|strcat|gets|sprintf|system\(|eval\(|exec\()',
    re.DOTALL,
)


def extract_vulnerable_function(code: str, context_lines: int = 40) -> str:
    """
    Try to extract just the function/method that contains the vulnerability.
    Strategy:
      1. Find the line with a vulnerability keyword.
      2. Walk backward to find the enclosing function start.
      3. Extract from function start for `context_lines` lines.
      4. Fallback: return first `context_lines` lines if no function found.
    """
    lines = code.splitlines()
    if not lines:
        return code

    # Find line with a vulnerability marker
    target_line = 0
    for i, line in enumerate(lines):
        if _VULN_KEYWORDS.search(line):
            target_line = i
            break

    # Walk backward from target_line to find function start
    func_start = max(0, target_line - context_lines)
    for i in range(target_line, -1, -1):
        if _FUNC_START_RE.match(lines[i]):
            func_start = i
            break

    # Extract window
    end = min(len(lines), func_start + context_lines * 2)
    extracted = lines[func_start:end]

    truncation_marker = "# ... [truncated — showing vulnerable function context] ..."
    if func_start > 0:
        extracted = [truncation_marker] + extracted
    if end < len(lines):
        extracted = extracted + [truncation_marker]

    return "\n".join(extracted)


# ─────────────────────────────────────────────────────────────────────────────
# SMART TRUNCATOR
# ─────────────────────────────────────────────────────────────────────────────

_CODE_BLOCK_RE = re.compile(
    r"(Code:\s*\n)(.*?)$",       # matches "Code:\n<code>" at end of user message
    re.DOTALL,
)
_PATCH_BUDGET   = 0.5            # fraction of token budget reserved for the assistant (patch)
_OVERHEAD_CHARS = 200            # ChatML overhead tokens (conservative)


def smart_truncate(
    entry: Dict,
    tokenizer: TokenizerWrapper,
    max_tokens: int,
    context_lines: int,
) -> Tuple[Dict, bool]:
    """
    Return (possibly modified entry, was_truncated).
    Truncates only if the entry's ChatML representation exceeds max_tokens.
    """
    chatml = apply_chatml(entry)
    token_count = tokenizer.count(chatml)

    if token_count <= max_tokens:
        return entry, False

    # ── Step 1: Extract vulnerable function from user message code block ──
    msgs = [m.copy() for m in entry.get("messages", [])]
    user_msg = msgs[1].get("content", "")

    m = _CODE_BLOCK_RE.search(user_msg)
    if m:
        prefix   = user_msg[:m.start(2)]       # "Vulnerability: ...\nCode:\n"
        orig_code = m.group(2)
        extracted = extract_vulnerable_function(orig_code, context_lines)
        msgs[1]["content"] = prefix + extracted
        entry_candidate = {**entry, "messages": msgs}

        chatml2 = apply_chatml(entry_candidate)
        if tokenizer.count(chatml2) <= max_tokens:
            return entry_candidate, True

    # ── Step 2: Hard-truncate the code block on both sides ───────────────
    # Give 50% of the remaining budget to the assistant message
    assistant_budget_chars = (max_tokens * _PATCH_BUDGET) * 4  # chars
    system_user_budget     = (max_tokens - _OVERHEAD_CHARS) * 4 - int(assistant_budget_chars)

    # Trim assistant
    asst_content = msgs[2]["content"]
    if len(asst_content) > int(assistant_budget_chars):
        msgs[2]["content"] = (
            asst_content[:int(assistant_budget_chars)]
            + "\n# ... [hard truncated] ..."
        )

    # Trim user code block
    user_m = _CODE_BLOCK_RE.search(msgs[1]["content"])
    if user_m:
        prefix   = msgs[1]["content"][:user_m.start(2)]
        code     = user_m.group(2)
        avail    = max(200, system_user_budget - len(prefix))
        if len(code) > avail:
            msgs[1]["content"] = prefix + code[:int(avail)] + "\n# ... [hard truncated] ..."

    return {**entry, "messages": msgs}, True


# ─────────────────────────────────────────────────────────────────────────────
# TOKEN HISTOGRAM
# ─────────────────────────────────────────────────────────────────────────────

BUCKETS = [128, 256, 512, 1024, 2048, 4096, 8192, 16384]

class TokenHistogram:
    def __init__(self, label: str):
        self.label  = label
        self.counts: Counter = Counter()
        self.total  = 0
        self.min_   = float("inf")
        self.max_   = 0
        self.sum_   = 0

    def add(self, n: int) -> None:
        bucket = next((b for b in BUCKETS if n <= b), BUCKETS[-1])
        self.counts[bucket] += 1
        self.total += 1
        self.min_ = min(self.min_, n)
        self.max_ = max(self.max_, n)
        self.sum_ += n

    def mean(self) -> float:
        return self.sum_ / self.total if self.total else 0

    def print(self) -> None:
        print(f"\n{'═' * 58}")
        print(f"  Token Distribution — {self.label}")
        print(f"  entries: {self.total:,} | min: {int(self.min_)} | "
              f"max: {self.max_} | mean: {self.mean():.0f}")
        print(f"{'─' * 58}")
        bar_scale = max(1, self.total // 30)
        prev = 0
        for bucket in BUCKETS:
            count = self.counts.get(bucket, 0)
            label = f"≤{bucket:>5}"
            bar   = "█" * (count // bar_scale)
            pct   = count / self.total * 100 if self.total else 0
            print(f"  {label}  {count:>6,}  ({pct:5.1f}%)  {bar}")
            prev = bucket
        print(f"{'═' * 58}\n")


# ─────────────────────────────────────────────────────────────────────────────
# FILE PROCESSOR
# ─────────────────────────────────────────────────────────────────────────────

def process_file(
    input_path: Path,
    output_path: Optional[Path],
    tokenizer: TokenizerWrapper,
    max_tokens: int,
    context_lines: int,
    report_only: bool,
) -> Dict:
    """Process one JSONL file. Returns stats dict."""
    if not input_path.exists():
        logger.warning(f"File not found: {input_path}")
        return {}

    hist_before = TokenHistogram(f"{input_path.name} — BEFORE")
    hist_after  = TokenHistogram(f"{input_path.name} — AFTER")

    entries_in:  List[Dict] = []
    entries_out: List[Dict] = []
    truncated = 0
    invalid   = 0

    # Load
    with input_path.open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                msgs  = entry.get("messages", [])
                if len(msgs) != 3:
                    invalid += 1
                    continue
                entries_in.append(entry)
            except json.JSONDecodeError:
                invalid += 1

    # Measure before
    for entry in entries_in:
        chatml = apply_chatml(entry)
        hist_before.add(tokenizer.count(chatml))

    hist_before.print()

    if report_only:
        return {
            "file": str(input_path),
            "total": len(entries_in),
            "invalid": invalid,
            "mean_tokens": hist_before.mean(),
            "max_tokens_seen": hist_before.max_,
        }

    # Truncate + collect
    for entry in entries_in:
        truncated_entry, was_truncated = smart_truncate(
            entry, tokenizer, max_tokens, context_lines
        )
        entries_out.append(truncated_entry)
        if was_truncated:
            truncated += 1
        chatml = apply_chatml(truncated_entry)
        hist_after.add(tokenizer.count(chatml))

    hist_after.print()

    # Write output (strip _meta)
    out_path = output_path or input_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for entry in entries_out:
            clean = {k: v for k, v in entry.items() if k != "_meta"}
            f.write(json.dumps(clean, ensure_ascii=False) + "\n")

    still_over = sum(
        1 for e in entries_out
        if tokenizer.count(apply_chatml(e)) > max_tokens
    )

    logger.info(
        f"  {input_path.name}: {len(entries_in):,} entries | "
        f"{truncated:,} truncated | {still_over} still over limit | "
        f"→ {out_path}"
    )

    return {
        "file": str(input_path),
        "total": len(entries_in),
        "truncated": truncated,
        "still_over": still_over,
        "mean_tokens_before": hist_before.mean(),
        "mean_tokens_after":  hist_after.mean(),
        "max_tokens_after":   hist_after.max_,
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ouroboros – Tokenizer & Smart Truncation (Task 2.3)",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input", type=Path,
        help="Single JSONL file to process (if omitted, processes all splits)",
    )
    parser.add_argument(
        "--output", type=Path,
        help="Output path (default: overwrite input file)",
    )
    parser.add_argument(
        "--splits-dir", type=Path, default=Path("data/splits"),
        help="Directory containing train/val/test.jsonl (default: data/splits)",
    )
    parser.add_argument(
        "--max-tokens", type=int, default=4096,
        help="Maximum token budget per entry  (default: 4096)",
    )
    parser.add_argument(
        "--context-lines", type=int, default=40,
        help="Lines of context around the vulnerable function (default: 40)",
    )
    parser.add_argument(
        "--model", type=str, default="Qwen/Qwen2.5-Coder-3B-Instruct",
        help="HuggingFace model name for tokenizer (default: Qwen/Qwen2.5-Coder-3B-Instruct)",
    )
    parser.add_argument(
        "--report-only", action="store_true",
        help="Print token histogram only, do not write output files",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    logger.info("═" * 62)
    logger.info("Ouroboros — Tokenizer & Smart Truncation  (Task 2.3)")
    logger.info("═" * 62)
    logger.info(f"Max tokens     : {args.max_tokens}")
    logger.info(f"Context lines  : {args.context_lines}")
    logger.info(f"Report only    : {args.report_only}")

    tok = TokenizerWrapper(args.model)
    logger.info(f"Tokenizer mode : {tok.mode}")

    # Determine files to process
    if args.input:
        files = [(args.input, args.output)]
    else:
        files = []
        for split in ("train", "val", "test"):
            p = args.splits_dir / f"{split}.jsonl"
            if p.exists():
                files.append((p, None))   # None → overwrite in place

    if not files:
        logger.error("No JSONL files found to process.")
        sys.exit(1)

    all_stats = []
    for inp, out in files:
        logger.info(f"\nProcessing: {inp}")
        stats = process_file(
            input_path=inp,
            output_path=out,
            tokenizer=tok,
            max_tokens=args.max_tokens,
            context_lines=args.context_lines,
            report_only=args.report_only,
        )
        all_stats.append(stats)

    # Summary table
    if not args.report_only:
        print("═" * 70)
        print(f"  {'File':<20} {'Entries':>8} {'Truncated':>10} {'OverLimit':>10} {'Mean→':>8}")
        print("─" * 70)
        for s in all_stats:
            if not s:
                continue
            fname = Path(s["file"]).name
            print(
                f"  {fname:<20} {s.get('total',0):>8,} "
                f"{s.get('truncated',0):>10,} "
                f"{s.get('still_over',0):>10,} "
                f"{s.get('mean_tokens_after',0):>7.0f}"
            )
        print("═" * 70 + "\n")

    logger.info("✅ Tokenization pass complete.")


if __name__ == "__main__":
    main()
