#!/usr/bin/env python3
"""
Usage: python3 run_queries_all_weeks.py <cpg_output_root>
Runs the full query orchestrator against every week folder that has
a generation_manifest.json, i.e. every week CPG generation has completed for.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.analyzer.run_queries import build_dataset_report


def run_all(cpg_output_root: str):
    root = Path(cpg_output_root)
    week_dirs = sorted(d for d in root.iterdir() if d.is_dir())

    for week_dir in week_dirs:
        manifest = week_dir / "generation_manifest.json"
        if not manifest.exists():
            print(f"Skipping {week_dir.name}, no manifest found (CPGs not generated yet)")
            continue
        print(f"\n=== Querying {week_dir.name} ===")
        build_dataset_report(str(week_dir), str(manifest))


if __name__ == "__main__":
    run_all(sys.argv[1])
