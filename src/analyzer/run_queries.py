#!/usr/bin/env python3
"""
Runs all applicable Joern queries across every generated CPG and
produces one structured JSON file matching the required schema.
"""

import json
import subprocess
import re
from pathlib import Path

QUERIES_DIR = Path("queries")

# language-gated query applicability
LANGUAGE_AGNOSTIC_QUERIES = [
    "null_deref.sc", "buffer_overflow.sc", "uninitialized_variable.sc",
    "missing_return.sc", "infinite_loop.sc"
]
C_ONLY_QUERIES = ["memory_leak.sc", "double_free.sc"]
C_LANGUAGES = {"c", "cpp"}


def applicable_queries(language: str):
    queries = list(LANGUAGE_AGNOSTIC_QUERIES)
    if language in C_LANGUAGES:
        queries += C_ONLY_QUERIES
    return queries


def run_query(query_file: str, cpg_path: str):
    cmd = ["joern", "--script", str(QUERIES_DIR / query_file),
           "--params", f"cpgPath={cpg_path}"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        # Joern prints the Scala list repr; extract the Map entries via a light parse
        return parse_scala_list_output(result.stdout)
    except subprocess.TimeoutExpired:
        return []


def parse_scala_list_output(raw_output: str):
    """
    Joern prints something like:
    List(Map(error_type -> null_pointer_dereference, line_number -> 12, ...))
    This extracts each Map(...) block into a Python dict.
    """
    entries = []
    for block in re.findall(r"Map\((.*?)\)(?=,\s*Map|\)$|\)\s*$)", raw_output, re.DOTALL):
        entry = {}
        for kv in re.findall(r"(\w+)\s*->\s*([^,]+)", block):
            key, val = kv
            val = val.strip()
            if val.lstrip("-").isdigit():
                val = int(val)
            entry[key] = val
        if entry:
            entries.append(entry)
    return entries


def build_dataset_report(cpg_output_root: str, manifest_path: str):
    manifest = json.loads(Path(manifest_path).read_text())
    report = []

    for student_id, meta in manifest["results"].items():
        if meta["status"] != "success":
            continue

        language = meta["language"]
        cpg_path = meta["cpg_path"]
        week = Path(cpg_output_root).name  # e.g. "week_01"

        errors = []
        for query_file in applicable_queries(language):
            errors.extend(run_query(query_file, cpg_path))

        report.append({
            "student_id": student_id,
            "week": week,
            "file_path": cpg_path,
            "language": language,
            "errors": errors
        })

    out_path = Path(cpg_output_root) / "error_report.json"
    out_path.write_text(json.dumps(report, indent=2))
    print(f"Wrote {len(report)} student records to {out_path}")
    return report


if __name__ == "__main__":
    import sys
    build_dataset_report(sys.argv[1], sys.argv[2])
