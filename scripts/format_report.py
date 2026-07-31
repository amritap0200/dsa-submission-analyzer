#!/usr/bin/env python3
"""
Usage: python3 format_report.py <cpg_output_root> <week_name>
Reads error_report.jsonl for one week and writes a structured
Markdown report alongside it. Does not modify or replace the
original JSONL in any way.
"""
import json
import sys
from pathlib import Path
from collections import Counter


def load_records(report_path: Path):
    records = []
    for line in report_path.read_text().splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def format_week(cpg_output_root: str, week_name: str):
    week_dir = Path(cpg_output_root) / week_name
    report_path = week_dir / "error_report.jsonl"

    if not report_path.exists():
        print(f"No error_report.jsonl found for {week_name}")
        return

    records = load_records(report_path)

    failed = [r for r in records if r.get("processing_error")]
    ok = [r for r in records if not r.get("processing_error")]

    error_type_counts = Counter()
    for r in ok:
        for err in r.get("errors", []):
            error_type_counts[err["error_type"]] += 1

    ok_sorted = sorted(ok, key=lambda r: len(r.get("errors", [])), reverse=True)

    lines = []
    lines.append(f"# Error Report: {week_name}")
    lines.append("")
    lines.append(f"- Students processed: **{len(ok)}**")
    lines.append(f"- Processing failures: **{len(failed)}**")
    lines.append(f"- Total errors found: **{sum(error_type_counts.values())}**")
    lines.append("")
    lines.append("## Error type breakdown")
    lines.append("")
    lines.append("| Error type | Count |")
    lines.append("|---|---|")
    for error_type, count in error_type_counts.most_common():
        lines.append(f"| {error_type} | {count} |")
    lines.append("")

    if failed:
        lines.append("## Processing failures")
        lines.append("")
        lines.append("| Student | Error |")
        lines.append("|---|---|")
        for r in failed:
            msg = r.get("processing_error", "").replace("|", "\\|")
            lines.append(f"| {r['student_id']} | {msg} |")
        lines.append("")

    lines.append("## Per-student breakdown")
    lines.append("")

    for r in ok_sorted:
        errors = r.get("errors", [])
        lines.append(f"### {r['student_id']} ({len(errors)} error{'s' if len(errors) != 1 else ''})")
        lines.append("")
        if not errors:
            lines.append("_No errors detected._")
            lines.append("")
            continue

        by_type = {}
        for err in errors:
            by_type.setdefault(err["error_type"], []).append(err)

        lines.append("| Error type | Line | Description |")
        lines.append("|---|---|---|")
        for error_type, occurrences in by_type.items():
            for occ in occurrences:
                desc = occ["description"].replace("|", "\\|")
                lines.append(f"| {error_type} | {occ['line_number']} | {desc} |")
        lines.append("")

    out_path = week_dir / "readable_report.md"
    out_path.write_text("\n".join(lines))
    print(f"Written: {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 format_report.py <cpg_output_root> <week_name>")
        sys.exit(1)
    format_week(sys.argv[1], sys.argv[2])
