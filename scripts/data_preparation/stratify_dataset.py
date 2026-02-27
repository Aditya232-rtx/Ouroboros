"""
Ouroboros AI - Language & Vulnerability Stratifier  (Task 2.1)
==============================================================
Analyzes and rebalances the dataset so that no (language, vuln_type) bucket
dominates training — preventing C/C++ memory corruption from crowding out
Java deserialization, Python SSRF, etc.

Usage
-----
  # 1. Analyze distribution before stratification
  python scripts/data_preparation/stratify_dataset.py --analyze

  # 2. Stratify + produce balanced splits (default: max 1000 per bucket)
  python scripts/data_preparation/stratify_dataset.py --stratify

  # 3. Use a tighter cap
  python scripts/data_preparation/stratify_dataset.py --stratify --max-per-bucket 500

  # 4. Custom dirs
  python scripts/data_preparation/stratify_dataset.py --stratify \\
      --processed-dir data/processed --output-dir data/splits --max-per-bucket 800
"""

import argparse
import collections
import hashlib
import json
import logging
import random
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("stratify_dataset")


# ─────────────────────────────────────────────────────────────────────────────
# LANGUAGE DETECTION
# ─────────────────────────────────────────────────────────────────────────────

# Ordered rules: (regex_pattern, language).  First match wins.
_LANG_RULES: List[Tuple[re.Pattern, str]] = [
    # --- explicit Language: line (from SyntheticConverter) ---
    (re.compile(r"^Language:\s*(.+)$", re.MULTILINE | re.IGNORECASE), "__explicit__"),

    # --- file-level markers ---
    (re.compile(r"#include\s*<(?:stdio|stdlib|string|unistd|sys/)"), "C"),
    (re.compile(r"#include\s*<(?:iostream|vector|string|memory|algorithm)>"), "C++"),
    (re.compile(r"\bpackage\s+\w+(?:\.\w+)+\s*;|\bimport\s+java\."), "Java"),
    (re.compile(r"FROM\s+\w[\w:/.-]+\s*\n|RUN\s|CMD\s+\[|ENTRYPOINT"), "Dockerfile"),
    (re.compile(r"func\s+\w+\(.*\)\s*(?:\(.*\)\s*)?\{"), "Go"),
    (re.compile(r"\bfn\s+\w+\s*\(|let\s+mut\b|->.*Result<|use\s+std::"), "Rust"),
    (re.compile(r"const\s+\w+\s*=\s*require\(|module\.exports|\.then\(|async\s+function"), "JavaScript"),
    (re.compile(r"def\s+\w+\s*\(|import\s+\w+|from\s+\w+\s+import"), "Python"),
]

_EXPLICIT_RE = re.compile(r"^Language:\s*(.+)$", re.MULTILINE | re.IGNORECASE)


def detect_language(text: str) -> str:
    """
    Detect programming language from message text (user message content).
    Checks for an explicit 'Language: X' line first, then uses keyword heuristics.
    Returns a normalised language name, or 'Unknown'.
    """
    # Priority 1: explicit Language: line
    m = _EXPLICIT_RE.search(text)
    if m:
        raw = m.group(1).strip()
        return _normalise_lang(raw)

    # Priority 2: heuristic patterns (skip the explicit rule sentinel)
    for pattern, lang in _LANG_RULES[1:]:
        if pattern.search(text):
            return lang

    return "Unknown"


def _normalise_lang(raw: str) -> str:
    """Normalise various spellings to canonical names."""
    lmap = {
        "c": "C", "c/c++": "C/C++", "c++": "C++", "cpp": "C++",
        "java": "Java", "python": "Python", "javascript": "JavaScript",
        "js": "JavaScript", "typescript": "TypeScript", "go": "Go",
        "golang": "Go", "rust": "Rust", "dockerfile": "Dockerfile",
        "docker": "Dockerfile", "ruby": "Ruby", "php": "PHP",
        "kotlin": "Kotlin", "swift": "Swift",
    }
    return lmap.get(raw.lower(), raw.capitalize())


# ─────────────────────────────────────────────────────────────────────────────
# VULN-TYPE EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

_VULN_RE = re.compile(r"^Vulnerability:\s*(.+)$", re.MULTILINE | re.IGNORECASE)

# Canonical families — map verbose names to a shorter bucket label
_VULN_FAMILY: Dict[str, str] = {
    "sql injection":                      "SQL Injection",
    "cross-site scripting":               "XSS",
    "xss":                                "XSS",
    "command injection":                  "Command Injection",
    "os command injection":               "Command Injection",
    "path traversal":                     "Path Traversal",
    "directory traversal":                "Path Traversal",
    "server-side request forgery":        "SSRF",
    "ssrf":                               "SSRF",
    "insecure deserialization":           "Deserialization",
    "deserialization":                    "Deserialization",
    "authentication bypass":              "Auth Bypass",
    "cryptographic failure":              "Crypto Failure",
    "hardcoded credentials":              "Hardcoded Creds",
    "insecure direct object reference":   "IDOR",
    "idor":                               "IDOR",
    "security misconfiguration":          "Misconfiguration",
    "execution with unnecessary privileges": "Privilege Escalation",
    "null pointer dereference":           "NULL Deref",
    "buffer overflow":                    "Buffer Overflow",
    "stack-based buffer overflow":        "Buffer Overflow",
    "heap-based buffer overflow":         "Buffer Overflow",
    "use after free":                     "Use After Free",
    "use-after-free":                     "Use After Free",
    "integer overflow":                   "Integer Overflow",
    "integer underflow":                  "Integer Underflow",
    "race condition":                     "Race Condition",
    "insecure permissions":               "Insecure Perms",
    "memory leak":                        "Memory Leak",
    "double free":                        "Double Free",
    "format string":                      "Format String",
    "uncontrolled format string":         "Format Strings",
    "improper input validation":          "Input Validation",
    "ldap injection":                     "LDAP Injection",
    "write-what-where":                   "Write-What-Where",
    "divide by zero":                     "Divide By Zero",
    "infinite loop":                      "Infinite Loop",
}


def extract_vuln_type(user_content: str) -> str:
    """Extract and normalise vulnerability type from the user message."""
    m = _VULN_RE.search(user_content)
    if not m:
        return "Unknown"
    raw = m.group(1).strip()
    # Try exact or prefix match in family map
    raw_lower = raw.lower()
    for key, family in _VULN_FAMILY.items():
        if key in raw_lower:
            return family
    # Truncate long names
    return raw[:40] if len(raw) > 40 else raw


def extract_bucket(entry: Dict) -> Tuple[str, str]:
    """Return (language, vuln_type) bucket for an entry."""
    try:
        user_content = entry["messages"][1]["content"]
        lang      = detect_language(user_content)
        vuln_type = extract_vuln_type(user_content)
        return (lang, vuln_type)
    except (KeyError, IndexError):
        return ("Unknown", "Unknown")


# ─────────────────────────────────────────────────────────────────────────────
# DISTRIBUTION ANALYZER
# ─────────────────────────────────────────────────────────────────────────────

class DistributionAnalyzer:
    """Reads all entries and builds a pivot table: language × vuln_type."""

    def __init__(self):
        self.counts: Dict[Tuple[str, str], int] = collections.defaultdict(int)
        self.total = 0

    def feed(self, entries):
        for entry in entries:
            bucket = extract_bucket(entry)
            self.counts[bucket] += 1
            self.total += 1

    def report(self, title: str = "Dataset Distribution") -> None:
        if not self.counts:
            print("  (no data)")
            return

        # Gather axes
        languages  = sorted({lang for (lang, _) in self.counts})
        vuln_types = sorted({vt   for (_, vt)   in self.counts})

        # Print pivot table
        col_w = max(len(vt) for vt in vuln_types) + 2
        lang_w = max(len(l) for l in languages) + 2

        print(f"\n{'═' * (lang_w + col_w * len(vuln_types) + 12)}")
        print(f"  {title}  (total: {self.total:,} entries)")
        print(f"{'─' * (lang_w + col_w * len(vuln_types) + 12)}")

        # Header
        header = f"  {'Language':<{lang_w}}"
        for vt in vuln_types:
            header += f"{vt:>{col_w}}"
        header += f"  {'TOTAL':>7}"
        print(header)
        print(f"{'─' * (lang_w + col_w * len(vuln_types) + 12)}")

        for lang in languages:
            row_total = sum(self.counts.get((lang, vt), 0) for vt in vuln_types)
            row = f"  {lang:<{lang_w}}"
            for vt in vuln_types:
                n = self.counts.get((lang, vt), 0)
                row += f"{n:>{col_w},}"
            row += f"  {row_total:>7,}"
            print(row)

        print(f"{'─' * (lang_w + col_w * len(vuln_types) + 12)}")
        totals_row = f"  {'TOTAL':<{lang_w}}"
        for vt in vuln_types:
            n = sum(self.counts.get((lang, vt), 0) for lang in languages)
            totals_row += f"{n:>{col_w},}"
        totals_row += f"  {self.total:>7,}"
        print(totals_row)
        print(f"{'═' * (lang_w + col_w * len(vuln_types) + 12)}\n")

        # Top-5 dominant buckets
        top = sorted(self.counts.items(), key=lambda x: -x[1])[:8]
        print("  🏆 Top buckets:")
        for (lang, vt), n in top:
            pct = n / self.total * 100 if self.total else 0
            bar = "█" * min(int(pct / 2), 30)
            print(f"     {lang:<14} × {vt:<28} {n:>6,}  ({pct:4.1f}%)  {bar}")
        print()


# ─────────────────────────────────────────────────────────────────────────────
# STRATIFIED SAMPLER
# ─────────────────────────────────────────────────────────────────────────────

class StratifiedSampler:
    """
    Caps each (language, vuln_type) bucket at max_per_bucket entries.
    Entries within a bucket are sampled reproducibly.
    Buckets smaller than the cap are kept in full (no upsampling).
    """

    def __init__(self, max_per_bucket: int = 1000, seed: int = 42):
        self.max_per_bucket = max_per_bucket
        self.rng = random.Random(seed)

    def sample(self, entries: List[Dict]) -> List[Dict]:
        """Return a stratified-sampled subset."""
        buckets: Dict[Tuple[str, str], List[Dict]] = collections.defaultdict(list)
        for entry in entries:
            bucket = extract_bucket(entry)
            buckets[bucket].append(entry)

        result: List[Dict] = []
        dropped = 0
        for bucket, items in sorted(buckets.items()):
            if len(items) <= self.max_per_bucket:
                result.extend(items)
            else:
                sampled = self.rng.sample(items, self.max_per_bucket)
                result.extend(sampled)
                dropped += len(items) - self.max_per_bucket
                lang, vt = bucket
                logger.info(
                    f"  Capped ({lang} × {vt}): "
                    f"{len(items):,} → {self.max_per_bucket:,} "
                    f"(-{len(items)-self.max_per_bucket:,})"
                )

        logger.info(
            f"Stratification: {len(entries):,} → {len(result):,} entries "
            f"({dropped:,} dropped to enforce cap of {self.max_per_bucket}/bucket)"
        )
        self.rng.shuffle(result)
        return result


# ─────────────────────────────────────────────────────────────────────────────
# I/O HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def load_processed(processed_dir: Path) -> List[Dict]:
    """Load all JSONL files from data/processed/, skipping invalid entries."""
    entries: List[Dict] = []
    seen: Set[str] = set()
    jsonl_files = sorted(processed_dir.glob("**/*.jsonl"))
    if not jsonl_files:
        logger.warning(f"No JSONL files found in {processed_dir}")
        return entries

    for path in jsonl_files:
        logger.info(f"  Loading {path.name} …")
        with path.open(encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    msgs = entry.get("messages", [])
                    if len(msgs) != 3:
                        continue
                    # Dedup on user content
                    key = msgs[1].get("content", "")
                    if key in seen:
                        continue
                    seen.add(key)
                    entries.append(entry)
                except Exception:
                    pass

    logger.info(f"Loaded {len(entries):,} unique valid entries from {len(jsonl_files)} files")
    return entries


def _sha8(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:8]


def _get_group_key(entry: Dict) -> str:
    meta = entry.get("_meta") or {}
    if meta.get("group_key"):
        return meta["group_key"]
    cve = (meta.get("cve_id") or "").strip().upper()
    if cve and cve not in ("", "NA", "N/A", "UNKNOWN"):
        return cve
    try:
        return _sha8(entry["messages"][1]["content"])
    except (KeyError, IndexError):
        return _sha8(json.dumps(entry))


def group_aware_split(
    entries: List[Dict],
    train_split: float = 0.8,
    val_split: float   = 0.1,
    seed: int = 42,
) -> Dict[str, List[Dict]]:
    """Split entries at group boundary to prevent CVE leakage."""
    groups: Dict[str, List[Dict]] = collections.defaultdict(list)
    for e in entries:
        groups[_get_group_key(e)].append(e)

    rng = random.Random(seed)
    group_keys = list(groups.keys())
    rng.shuffle(group_keys)

    total = len(entries)
    n_train = int(total * train_split)
    n_val   = int(total * val_split)

    split_groups: Dict[str, List[str]] = {"train": [], "val": [], "test": []}
    cumulative = 0
    for gk in group_keys:
        n_g = len(groups[gk])
        if cumulative < n_train:
            split_groups["train"].append(gk)
        elif cumulative < n_train + n_val:
            split_groups["val"].append(gk)
        else:
            split_groups["test"].append(gk)
        cumulative += n_g

    result: Dict[str, List[Dict]] = {}
    for split_name, gkeys in split_groups.items():
        es = [e for gk in gkeys for e in groups[gk]]
        rng.shuffle(es)
        result[split_name] = es

    # Leakage assertion
    sets = {s: set(gkeys) for s, gkeys in split_groups.items()}
    assert sets["train"].isdisjoint(sets["val"]),  "LEAKAGE: train ∩ val!"
    assert sets["train"].isdisjoint(sets["test"]), "LEAKAGE: train ∩ test!"
    assert sets["val"].isdisjoint(sets["test"]),   "LEAKAGE: val ∩ test!"
    logger.info("✅ Zero CVE-group leakage confirmed after stratification.")
    return result


def write_splits(
    splits: Dict[str, List[Dict]],
    output_dir: Path,
) -> None:
    """Write final JSONL splits, stripping _meta from each entry."""
    output_dir.mkdir(parents=True, exist_ok=True)
    for split_name, entries in splits.items():
        out = output_dir / f"{split_name}.jsonl"
        with out.open("w", encoding="utf-8") as f:
            for entry in entries:
                clean = {k: v for k, v in entry.items() if k != "_meta"}
                f.write(json.dumps(clean, ensure_ascii=False) + "\n")
        logger.info(f"  {split_name:5s}: {len(entries):>7,} entries → {out}")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ouroboros – Language & Vulnerability Stratifier (Task 2.1)",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--processed-dir", type=Path, default=Path("data/processed"),
        help="Directory of per-source processed JSONL files (default: data/processed)",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/splits"),
        help="Destination for stratified train/val/test splits (default: data/splits)",
    )
    parser.add_argument(
        "--max-per-bucket", type=int, default=1000,
        help="Max entries per (language × vuln_type) bucket (default: 1000)",
    )
    parser.add_argument("--train-split", type=float, default=0.8)
    parser.add_argument("--val-split",   type=float, default=0.1)
    parser.add_argument("--seed",        type=int,   default=42)

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--analyze",  action="store_true",
        help="Print distribution pivot table and exit (no files written)",
    )
    mode.add_argument(
        "--stratify", action="store_true",
        help="Apply stratified sampling and write balanced splits",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    logger.info("═" * 62)
    logger.info("Ouroboros — Language & Vulnerability Stratifier (Task 2.1)")
    logger.info("═" * 62)

    # ── Load ──────────────────────────────────────────────────────────────────
    entries = load_processed(args.processed_dir)
    if not entries:
        logger.error("No entries loaded — check --processed-dir path.")
        sys.exit(1)

    # ── ANALYZE mode ──────────────────────────────────────────────────────────
    if args.analyze:
        analyzer = DistributionAnalyzer()
        analyzer.feed(entries)
        analyzer.report("Current Distribution (before stratification)")
        sys.exit(0)

    # ── STRATIFY mode ─────────────────────────────────────────────────────────
    # 1. Show before
    analyzer_before = DistributionAnalyzer()
    analyzer_before.feed(entries)
    analyzer_before.report("BEFORE Stratification")

    # 2. Sample
    sampler = StratifiedSampler(max_per_bucket=args.max_per_bucket, seed=args.seed)
    balanced = sampler.sample(entries)

    # 3. Show after
    analyzer_after = DistributionAnalyzer()
    analyzer_after.feed(balanced)
    analyzer_after.report("AFTER Stratification")

    # 4. CVE-group-aware split
    logger.info("Splitting with CVE-group isolation …")
    splits = group_aware_split(
        balanced,
        train_split=args.train_split,
        val_split=args.val_split,
        seed=args.seed,
    )

    # 5. Split distribution
    for split_name, es in splits.items():
        an = DistributionAnalyzer()
        an.feed(es)
        an.report(f"{split_name.upper()} split distribution")

    # 6. Write
    write_splits(splits, args.output_dir)
    logger.info("✅ Stratification complete.")


if __name__ == "__main__":
    main()
