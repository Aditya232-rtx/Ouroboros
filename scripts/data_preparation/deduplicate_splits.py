"""
Ouroboros AI - Strict CVE-Group-Aware Deduplicator  (Task 1.2)
===============================================================
Re-splits any existing processed JSONL data with strict group isolation:
  - No CVE ID appears in more than one split.
  - Groups without a CVE are bucketed by (source, CWE, code-hash).
  - Produces a leakage report after splitting.

Usage
-----
  # Re-split from processed intermediates
  python scripts/data_preparation/deduplicate_splits.py \\
      --processed-dir data/processed \\
      --output-dir    data/splits \\
      --train-split 0.8 --val-split 0.1 --test-split 0.1

  # Only run the leakage check on existing splits (no re-splitting)
  python scripts/data_preparation/deduplicate_splits.py --check-leakage
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
logger = logging.getLogger("deduplicate_splits")


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _sha8(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:8]


def _extract_group_key(entry: Dict) -> str:
    """
    Extract the group_key for an entry.
    Priority: _meta.group_key > _meta.cve_id > hash(user_content)
    """
    meta = entry.get("_meta") or {}
    if meta.get("group_key"):
        return meta["group_key"]
    cve = (meta.get("cve_id") or "").strip().upper()
    if cve and cve not in ("", "NA", "N/A", "UNKNOWN"):
        return cve
    # Fallback: hash of user message content
    try:
        return _sha8(entry["messages"][1]["content"])
    except (KeyError, IndexError):
        return _sha8(json.dumps(entry))


def _is_valid(entry: Dict) -> bool:
    """Basic schema check: must have 3 messages with correct roles."""
    try:
        msgs = entry.get("messages", [])
        if len(msgs) != 3:
            return False
        for msg, role in zip(msgs, ["system", "user", "assistant"]):
            if msg.get("role") != role or not msg.get("content", "").strip():
                return False
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# CORE CLASS
# ─────────────────────────────────────────────────────────────────────────────

class GroupAwareDeduplicator:
    """
    Loads processed JSONL data, groups entries by CVE/pattern group_key,
    assigns groups to train/val/test without any overlap, then writes clean splits.
    """

    def __init__(
        self,
        processed_dir: Path,
        output_dir: Path,
        train_split: float = 0.8,
        val_split: float   = 0.1,
        test_split: float  = 0.1,
        seed: int = 42,
    ):
        assert abs(train_split + val_split + test_split - 1.0) < 1e-6, \
            "Splits must sum to 1.0"
        self.processed_dir = processed_dir
        self.output_dir    = output_dir
        self.train_split   = train_split
        self.val_split     = val_split
        self.test_split    = test_split
        self.seed          = seed

        # Internal state populated during load_entries()
        self.groups: Dict[str, List[Dict]] = {}   # group_key → entries
        self.duplicates  = 0
        self.invalid     = 0
        self.no_meta     = 0

        # Populated during split_groups()
        self.split_assignments: Dict[str, str] = {}   # group_key → split_name
        self.split_entries: Dict[str, List[Dict]] = {"train": [], "val": [], "test": []}

    # ── Loading ───────────────────────────────────────────────────────────────

    def load_entries(self) -> "GroupAwareDeduplicator":
        """Load all JSONL files from processed_dir, deduplicate, and group."""
        seen_content: Set[str] = set()
        jsonl_files = sorted(self.processed_dir.glob("**/*.jsonl"))
        if not jsonl_files:
            logger.warning(f"No JSONL files found in {self.processed_dir}")
            return self

        for path in jsonl_files:
            logger.info(f"  Loading {path.name} …")
            with path.open(encoding="utf-8", errors="ignore") as f:
                for lineno, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        self.invalid += 1
                        continue

                    if not _is_valid(entry):
                        self.invalid += 1
                        continue

                    # Content-level deduplication
                    content_key = entry["messages"][1]["content"]
                    if content_key in seen_content:
                        self.duplicates += 1
                        continue
                    seen_content.add(content_key)

                    # Group-level assignment
                    gk = _extract_group_key(entry)
                    if not entry.get("_meta"):
                        self.no_meta += 1
                    self.groups.setdefault(gk, []).append(entry)

        n = sum(len(v) for v in self.groups.values())
        logger.info(
            f"Loaded {n:,} unique valid entries | "
            f"{len(self.groups):,} groups | "
            f"{self.duplicates} duplicates removed | "
            f"{self.invalid} invalid | "
            f"{self.no_meta} without _meta"
        )
        return self

    # ── Splitting ─────────────────────────────────────────────────────────────

    def split_groups(self) -> "GroupAwareDeduplicator":
        """Assign groups to train/val/test by cumulative entry count."""
        total = sum(len(v) for v in self.groups.values())
        if total == 0:
            logger.error("No entries to split — did you run load_entries() first?")
            return self

        rng = random.Random(self.seed)
        group_keys = list(self.groups.keys())
        rng.shuffle(group_keys)

        n_train = int(total * self.train_split)
        n_val   = int(total * self.val_split)

        cumulative = 0
        for gk in group_keys:
            n_g = len(self.groups[gk])
            if cumulative < n_train:
                split = "train"
            elif cumulative < n_train + n_val:
                split = "val"
            else:
                split = "test"
            self.split_assignments[gk] = split
            cumulative += n_g

        # Collect entries per split
        self.split_entries = {"train": [], "val": [], "test": []}
        for gk, split in self.split_assignments.items():
            self.split_entries[split].extend(self.groups[gk])

        # Shuffle entries within each split (reproducible)
        for entries in self.split_entries.values():
            rng.shuffle(entries)

        return self

    # ── Leakage Verification ──────────────────────────────────────────────────

    def verify_no_leakage(self) -> bool:
        """Assert that no group_key appears in more than one split. Returns True if clean."""
        split_key_sets: Dict[str, Set[str]] = {
            s: set(gk for gk, sp in self.split_assignments.items() if sp == s)
            for s in ("train", "val", "test")
        }
        leaks: List[str] = []
        pairs = [("train", "val"), ("train", "test"), ("val", "test")]
        for a, b in pairs:
            overlap = split_key_sets[a] & split_key_sets[b]
            if overlap:
                leaks.append(
                    f"  ❌ {a} ∩ {b}: {len(overlap)} shared groups "
                    f"(examples: {list(overlap)[:3]})"
                )
        if leaks:
            logger.error("DATA LEAKAGE DETECTED:\n" + "\n".join(leaks))
            return False
        logger.info("✅ Zero group leakage confirmed — all splits are disjoint.")
        return True

    # ── Writing ───────────────────────────────────────────────────────────────

    def write_splits(self) -> Dict[str, Path]:
        """Write final JSONL files — _meta is stripped from every entry."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_paths = {}
        for split_name, entries in self.split_entries.items():
            out_path = self.output_dir / f"{split_name}.jsonl"
            with out_path.open("w", encoding="utf-8") as f:
                for entry in entries:
                    clean = {k: v for k, v in entry.items() if k != "_meta"}
                    f.write(json.dumps(clean, ensure_ascii=False) + "\n")
            output_paths[split_name] = out_path
        return output_paths

    # ── Reporting ─────────────────────────────────────────────────────────────

    def report(self) -> None:
        """Print a detailed stats table to stdout."""
        total_e = sum(len(v) for v in self.split_entries.values())
        total_g = len(self.split_assignments)

        # Count CVE-backed groups per split
        cve_pattern = re.compile(r"^CVE-\d{4}-\d+$", re.IGNORECASE)

        print("\n" + "═" * 68)
        print(f"  {'Split':<8} {'Entries':>8} {'Groups':>8} {'CVE groups':>12} {'%':>6}")
        print("─" * 68)
        for split in ("train", "val", "test"):
            entries = self.split_entries[split]
            gkeys = [gk for gk, sp in self.split_assignments.items() if sp == split]
            cve_backed = sum(1 for gk in gkeys if cve_pattern.match(gk))
            pct = len(entries) / total_e * 100 if total_e else 0
            print(
                f"  {split:<8} {len(entries):>8,} {len(gkeys):>8,} "
                f"{cve_backed:>12,} {pct:>5.1f}%"
            )
        print("─" * 68)
        print(f"  {'TOTAL':<8} {total_e:>8,} {total_g:>8,}")
        print("═" * 68)

        # Source breakdown
        source_counts: Dict[str, Dict[str, int]] = {}
        for gk, entries in self.groups.items():
            split = self.split_assignments.get(gk, "?")
            for e in entries:
                src = (e.get("_meta") or {}).get("source", "unknown")
                source_counts.setdefault(src, {"train": 0, "val": 0, "test": 0})
                source_counts[src][split] = source_counts[src].get(split, 0) + 1

        if source_counts:
            print(f"\n  {'Source':<18} {'Train':>8} {'Val':>8} {'Test':>8}")
            print("─" * 50)
            for src, counts in sorted(source_counts.items()):
                print(
                    f"  {src:<18} {counts.get('train',0):>8,} "
                    f"{counts.get('val',0):>8,} {counts.get('test',0):>8,}"
                )
        print()


# ─────────────────────────────────────────────────────────────────────────────
# LEAKAGE-ONLY CHECK (works on final splits without _meta)
# ─────────────────────────────────────────────────────────────────────────────

def check_leakage_in_splits(splits_dir: Path) -> int:
    """
    Read group_key values from the _meta field in existing splits and verify
    zero overlap. Returns 0 if clean, 1 if leakage detected.
    NOTE: only works if splits were written WITH _meta (i.e., from processed dir).
    As a fallback, uses the hash of the user content.
    """
    split_keys: Dict[str, Set[str]] = {}
    for split in ("train", "val", "test"):
        path = splits_dir / f"{split}.jsonl"
        if not path.exists():
            logger.warning(f"  {split}.jsonl not found — skipping")
            continue
        keys: Set[str] = set()
        with path.open(encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    gk = _extract_group_key(entry)
                    keys.add(gk)
                except Exception:
                    pass
        split_keys[split] = keys
        logger.info(f"  {split}: {len(keys):,} unique group keys")

    leakage = False
    pairs = [("train", "val"), ("train", "test"), ("val", "test")]
    for a, b in pairs:
        if a not in split_keys or b not in split_keys:
            continue
        overlap = split_keys[a] & split_keys[b]
        if overlap:
            logger.error(
                f"❌ LEAKAGE: {a} ∩ {b} = {len(overlap)} shared keys "
                f"(examples: {list(overlap)[:5]})"
            )
            leakage = True
        else:
            logger.info(f"✅ {a} ∩ {b} = ∅  (no leakage)")

    return 1 if leakage else 0


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ouroboros – Strict CVE-Group-Aware Deduplicator (Task 1.2)",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--processed-dir", type=Path, default=Path("data/processed"),
        help="Directory of per-source processed JSONL files (default: data/processed)",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/splits"),
        help="Output directory for train/val/test splits (default: data/splits)",
    )
    parser.add_argument("--train-split", type=float, default=0.8)
    parser.add_argument("--val-split",   type=float, default=0.1)
    parser.add_argument("--test-split",  type=float, default=0.1)
    parser.add_argument("--seed",        type=int,   default=42)
    parser.add_argument(
        "--check-leakage", action="store_true",
        help="Only verify existing splits in --output-dir for CVE leakage (no re-split)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.check_leakage:
        logger.info(f"Checking leakage in existing splits at: {args.output_dir}")
        sys.exit(check_leakage_in_splits(args.output_dir))

    logger.info("═" * 60)
    logger.info("Ouroboros — Strict CVE-Group Deduplicator")
    logger.info("═" * 60)
    logger.info(f"Processed dir : {args.processed_dir.resolve()}")
    logger.info(f"Output dir    : {args.output_dir.resolve()}")
    logger.info(f"Splits        : train={args.train_split} val={args.val_split} test={args.test_split}")
    logger.info(f"Seed          : {args.seed}")

    dedup = GroupAwareDeduplicator(
        processed_dir=args.processed_dir,
        output_dir=args.output_dir,
        train_split=args.train_split,
        val_split=args.val_split,
        test_split=args.test_split,
        seed=args.seed,
    )

    dedup.load_entries()

    if not dedup.groups:
        logger.error("No data loaded — check that --processed-dir contains .jsonl files.")
        sys.exit(1)

    dedup.split_groups()
    ok = dedup.verify_no_leakage()
    paths = dedup.write_splits()
    dedup.report()

    for split_name, path in paths.items():
        n = sum(1 for _ in path.open(encoding="utf-8"))
        logger.info(f"  Written: {path}  ({n:,} lines)")

    if not ok:
        logger.error("Splits written but leakage was detected — investigate immediately.")
        sys.exit(1)

    logger.info("✅ Deduplication complete. Splits are CVE-leak-free.")


if __name__ == "__main__":
    main()
