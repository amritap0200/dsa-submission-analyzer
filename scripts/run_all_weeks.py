#!/usr/bin/env python3
"""
Usage: python3 run_all_weeks.py <lab_ec_root> <output_root> [min_week]
Example: python3 run_all_weeks.py /mnt/c/Users/admin/Downloads/lab_ec/lab_ec cpg_output 3
"""
import sys
import re
from pathlib import Path
from generate_cpgs import run_batch


def week_number(week_dir: Path) -> int:
    match = re.search(r"\d+", week_dir.name)
    return int(match.group()) if match else -1


def label_for_source_dir(week_dir: Path, source_dir: Path) -> str:
    rel = source_dir.relative_to(week_dir)
    parts = rel.parts
    if len(parts) == 1:
        return week_dir.name
    return f"{week_dir.name}_{parts[0]}"


def run_all(lab_ec_root: str, output_root: str, min_week: int = 1):
    root = Path(lab_ec_root)
    week_dirs = sorted(
        [d for d in root.iterdir() if d.is_dir() and d.name.lower().startswith("week")],
        key=week_number
    )

    for week_dir in week_dirs:
        if week_number(week_dir) < min_week:
            continue

        source_dirs = sorted(week_dir.rglob("A"))
        if not source_dirs:
            print(f"Skipping {week_dir.name}, no 'A' folder found")
            continue

        for source_dir in source_dirs:
            if not source_dir.is_dir():
                continue
            label = label_for_source_dir(week_dir, source_dir)
            out_dir = Path(output_root) / label
            print(f"\n=== Processing {label} ({source_dir}) ===")
            run_batch(str(source_dir), str(out_dir))


if __name__ == "__main__":
    lab_ec_root = sys.argv[1]
    output_root = sys.argv[2]
    min_week = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    run_all(lab_ec_root, output_root, min_week)
