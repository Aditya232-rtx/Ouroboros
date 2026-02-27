"""
Ouroboros AI - Dataset Spot-Check Validator
Task 1.1: Validate a generated JSONL dataset file.

Usage:
  python scripts/data_preparation/validate_dataset.py data/splits/train.jsonl
  python scripts/data_preparation/validate_dataset.py data/splits/train.jsonl --samples 5
"""

import argparse
import json
import random
import sys
from pathlib import Path


def validate(jsonl_path: Path, n_samples: int = 3, seed: int = 42) -> int:
    """
    Validate a JSONL dataset file and print a report.
    Returns exit code (0 = all good, 1 = issues found).
    """
    if not jsonl_path.exists():
        print(f"❌  File not found: {jsonl_path}")
        return 1

    total   = 0
    valid   = 0
    invalid = 0
    seen    = set()
    duplicates = 0
    all_valid_entries = []

    with jsonl_path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            total += 1

            # Parse JSON
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as e:
                invalid += 1
                if invalid <= 3:
                    print(f"  ⚠  Line {lineno}: JSON parse error — {e}")
                continue

            # Validate schema
            messages = entry.get("messages", [])
            expected_roles = ["system", "user", "assistant"]
            ok = True

            if len(messages) != 3:
                ok = False
                if invalid < 3:
                    print(f"  ⚠  Line {lineno}: Expected 3 messages, got {len(messages)}")
            else:
                for i, (msg, role) in enumerate(zip(messages, expected_roles)):
                    if msg.get("role") != role:
                        ok = False
                        print(f"  ⚠  Line {lineno}: messages[{i}].role = '{msg.get('role')}', expected '{role}'")
                    if not msg.get("content", "").strip():
                        ok = False
                        print(f"  ⚠  Line {lineno}: messages[{i}].content is empty")

            if not ok:
                invalid += 1
                continue

            # Deduplication check
            key = messages[1]["content"]
            if key in seen:
                duplicates += 1
            else:
                seen.add(key)
                valid += 1
                all_valid_entries.append(entry)

    # ── Report ────────────────────────────────────────────────────────────────
    print("\n" + "═" * 60)
    print(f"  📄  File     : {jsonl_path}")
    print(f"  📊  Total    : {total:,}")
    print(f"  ✅  Valid    : {valid:,}")
    print(f"  ❌  Invalid  : {invalid:,}")
    print(f"  🔁  Duplicates: {duplicates:,}")
    pass_rate = round(valid / total * 100, 1) if total else 0.0
    print(f"  📈  Pass rate: {pass_rate}%")
    print("═" * 60)

    if not all_valid_entries:
        print("\n⚠  No valid entries to sample.")
        return 1

    # ── Random samples ────────────────────────────────────────────────────────
    random.seed(seed)
    samples = random.sample(all_valid_entries, min(n_samples, len(all_valid_entries)))

    print(f"\n📝  {len(samples)} Random Sample(s):\n")
    for i, entry in enumerate(samples, 1):
        msgs = entry["messages"]
        print(f"{'─' * 60}")
        print(f"  Sample {i}")
        print(f"{'─' * 60}")
        print(f"  [SYSTEM]\n  {msgs[0]['content']}\n")
        user_content = msgs[1]["content"]
        # Truncate long code for display
        if len(user_content) > 400:
            user_content = user_content[:400] + "\n  ... (truncated)"
        print(f"  [USER]\n  {user_content}\n")
        assistant_content = msgs[2]["content"]
        if len(assistant_content) > 400:
            assistant_content = assistant_content[:400] + "\n  ... (truncated)"
        print(f"  [ASSISTANT]\n  {assistant_content}\n")

    # Return exit code
    if invalid > 0 or total == 0:
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Ouroboros – Dataset Spot-Check Validator",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("jsonl_file", type=Path,
                        help="Path to the JSONL dataset file to validate")
    parser.add_argument("--samples", type=int, default=3,
                        help="Number of random samples to print (default: 3)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for sample selection (default: 42)")
    args = parser.parse_args()

    exit_code = validate(args.jsonl_file, n_samples=args.samples, seed=args.seed)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
