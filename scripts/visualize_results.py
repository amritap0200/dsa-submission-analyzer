#!/usr/bin/env python3
"""
Usage: python3 visualize_results.py <cpg_output_root>
Reads all_weeks_summary.json (produced by summarize_results.py)
plus each week's raw error_report.jsonl, and writes PNG charts
to <cpg_output_root>/charts/. demo_samples is excluded, matching
summarize_results.py.
"""
import json
import sys
from pathlib import Path
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

EXCLUDE = {"demo_samples"}


def load_jsonl(path: Path):
    records = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def chart_error_type_totals(combined_counts, out_dir: Path):
    types = list(combined_counts.keys())
    counts = list(combined_counts.values())

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(types, counts, color="#4C72B0")
    ax.set_ylabel("Total occurrences")
    ax.set_title("Error type totals across all weeks")
    plt.xticks(rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(out_dir / "error_type_totals.png", dpi=150)
    plt.close(fig)


def chart_errors_per_week_stacked(per_week: dict, out_dir: Path):
    weeks = sorted(per_week.keys())
    all_types = sorted({t for w in weeks for t in per_week[w]["error_type_counts"]})

    fig, ax = plt.subplots(figsize=(10, 6))
    bottom = [0] * len(weeks)
    for error_type in all_types:
        values = [per_week[w]["error_type_counts"].get(error_type, 0) for w in weeks]
        ax.bar(weeks, values, bottom=bottom, label=error_type)
        bottom = [b + v for b, v in zip(bottom, values)]

    ax.set_ylabel("Errors")
    ax.set_title("Error breakdown by week (stacked by type)")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
    plt.xticks(rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(out_dir / "errors_by_week_stacked.png", dpi=150)
    plt.close(fig)


def chart_trend_total_errors(per_week: dict, out_dir: Path):
    weeks = sorted(per_week.keys())
    totals = [per_week[w]["total_errors_found"] for w in weeks]
    avgs = [per_week[w]["avg_errors_per_student"] for w in weeks]

    fig, ax1 = plt.subplots(figsize=(9, 5))
    ax1.plot(weeks, totals, marker="o", color="#4C72B0", label="Total errors")
    ax1.set_ylabel("Total errors", color="#4C72B0")
    ax1.tick_params(axis="y", labelcolor="#4C72B0")

    ax2 = ax1.twinx()
    ax2.plot(weeks, avgs, marker="s", color="#C44E52", label="Avg errors/student")
    ax2.set_ylabel("Avg errors per student", color="#C44E52")
    ax2.tick_params(axis="y", labelcolor="#C44E52")

    ax1.set_title("Error trend across weeks")
    plt.xticks(rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(out_dir / "trend_across_weeks.png", dpi=150)
    plt.close(fig)


def chart_per_student_histogram(cpg_output_root: Path, week_names, out_dir: Path):
    all_counts = []
    for week_name in week_names:
        report_path = cpg_output_root / week_name / "error_report.jsonl"
        if not report_path.exists():
            continue
        for entry in load_jsonl(report_path):
            if entry.get("processing_error"):
                continue
            all_counts.append(len(entry.get("errors", [])))

    if not all_counts:
        return

    fig, ax = plt.subplots(figsize=(9, 5))
    max_count = max(all_counts)
    ax.hist(all_counts, bins=range(0, max_count + 2), color="#55A868", edgecolor="black")
    ax.set_xlabel("Errors flagged per student")
    ax.set_ylabel("Number of students")
    ax.set_title("Distribution of errors per student (all real weeks)")
    fig.tight_layout()
    fig.savefig(out_dir / "errors_per_student_histogram.png", dpi=150)
    plt.close(fig)


def visualize(cpg_output_root: str):
    root = Path(cpg_output_root)
    summary_path = root / "all_weeks_summary.json"

    if not summary_path.exists():
        print(f"{summary_path} not found. Run summarize_results.py first.")
        sys.exit(1)

    summary = json.loads(summary_path.read_text())
    per_week = summary["per_week"]
    combined_counts = summary["combined_error_type_counts"]

    if not per_week:
        print("No real weeks found in all_weeks_summary.json, nothing to chart.")
        sys.exit(1)

    out_dir = root / "charts"
    out_dir.mkdir(exist_ok=True)

    chart_error_type_totals(combined_counts, out_dir)
    chart_errors_per_week_stacked(per_week, out_dir)
    chart_trend_total_errors(per_week, out_dir)
    chart_per_student_histogram(root, per_week.keys(), out_dir)

    print(f"Charts written to {out_dir}/:")
    for f in sorted(out_dir.glob("*.png")):
        print(f"  {f.name}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 visualize_results.py <cpg_output_root>")
        sys.exit(1)
    visualize(sys.argv[1])
