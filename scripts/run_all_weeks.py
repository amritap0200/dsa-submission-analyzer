#!/usr/bin/env python3
"""
Usage: python3 run_all_weeks.py <lab_ec_root> <output_root>
Example: python3 run_all_weeks.py /mnt/c/Users/admin/Downloads/lab_ec/lab_ec cpg_output
"""
import sys
from pathlib import Path
from generate_cpgs import run_batch


def run_all(lab_ec_root: str, output_root: str):
    root = Path(lab_ec_root)
    week_dirs = sorted([d for d in root.iterdir() if d.is_dir() and d.name.lower().startswith("week")])

    for week_dir in week_dirs:
        source_dir = week_dir / "A"  # adjust if a given week uses a different subfolder name
        if not source_dir.exists():
            print(f"Skipping {week_dir.name}, no 'A' subfolder found")
            continue

        out_dir = Path(output_root) / week_dir.name
        print(f"\n=== Processing {week_dir.name} ===")
        run_batch(str(source_dir), str(out_dir))


if __name__ == "__main__":
    run_all(sys.argv[1], sys.argv[2])
