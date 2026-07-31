#!/usr/bin/env python3
"""
Usage: python3 run_one_week.py <cpg_output_root> <week_name>
Example: python3 run_one_week.py cpg_output week1

Runs detect_all.sc for exactly one week's worth of CPGs, cleans up
Joern's scratch workspace before and after, filters Joern's noisy
per-pass log lines from the console, and copies the finished
error_report.jsonl to the Windows-visible mirror folder. Safe to
interrupt and rerun, since detect_all.sc resumes from what's already
written rather than starting over.
"""
import sys
import subprocess
import shutil
from pathlib import Path

C_LANGUAGE_WEEKS_DEFAULT = True
WINDOWS_MIRROR_ROOT = "/mnt/c/Users/admin/Downloads/lab_ec/lab_ec/cpg_output"

NOISE_PREFIXES = (
    "[INFO ]",
    "Creating project",
    "Creating working copy",
    "Loading base CPG from",
    "Adding default overlays",
    "closing/saving project",
    "writing to storage at",
    "closed graph at",
)
NOISE_SUBSTRINGS = (
    "The graph has been modified",
)


def is_noise(line: str) -> bool:
    stripped = line.strip()
    if any(stripped.startswith(p) for p in NOISE_PREFIXES):
        return True
    if any(s in stripped for s in NOISE_SUBSTRINGS):
        return True
    return False


def clean_workspace():
    workspace = Path("workspace")
    if workspace.exists():
        shutil.rmtree(workspace)
        print("Cleared Joern's workspace/ scratch directory")


def run_week(cpg_output_root: str, week_name: str):
    week_dir = Path(cpg_output_root) / week_name
    manifest = week_dir / "generation_manifest.json"

    if not manifest.exists():
        print(f"No manifest found for {week_name}, CPGs not generated yet")
        return

    clean_workspace()

    print(f"\n=== Querying {week_name} (single JVM run, resumable) ===")
    cmd = [
        "joern", "--script", "src/analyzer/detect_all.sc",
        "--param", f"weekDir={week_dir}",
        "--param", f"isC={str(C_LANGUAGE_WEEKS_DEFAULT).lower()}"
    ]

    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1
    )
    for line in process.stdout:
        if not is_noise(line):
            print(line, end="")
    process.wait()

    report = week_dir / "error_report.jsonl"
    if report.exists():
        dest_dir = Path(WINDOWS_MIRROR_ROOT) / week_name
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(report, dest_dir / "error_report.jsonl")
        print(f"Copied results to {dest_dir / 'error_report.jsonl'}")
    else:
        print(f"{week_name}: no error_report.jsonl produced yet")

    clean_workspace()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 run_one_week.py <cpg_output_root> <week_name>")
        sys.exit(1)
    run_week(sys.argv[1], sys.argv[2])
