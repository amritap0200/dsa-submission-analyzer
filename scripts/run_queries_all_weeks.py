#!/usr/bin/env python3
import sys
import subprocess
from pathlib import Path

C_LANGUAGE_WEEKS_DEFAULT = True  # set False per-week if a week is ever non-C


def run_all(cpg_output_root: str):
    root = Path(cpg_output_root)
    week_dirs = sorted(d for d in root.iterdir() if d.is_dir())

    for week_dir in week_dirs:
        manifest = week_dir / "generation_manifest.json"
        if not manifest.exists():
            print(f"Skipping {week_dir.name}, no manifest found")
            continue

        print(f"\n=== Querying {week_dir.name} (single JVM run) ===")
        cmd = [
            "joern", "--script", "src/analyzer/detect_all.sc",
            "--params", f"weekDir={week_dir},isC={str(C_LANGUAGE_WEEKS_DEFAULT).lower()}"
        ]
        subprocess.run(cmd)


if __name__ == "__main__":
    run_all(sys.argv[1])
