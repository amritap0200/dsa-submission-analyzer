#!/usr/bin/env python3
"""
Multi-language CPG generator.
Usage: python3 generate_cpgs.py <dataset_dir> <output_dir>
Example: python3 generate_cpgs.py dataset/week_01 cpg_output/week_01
"""

import os
import sys
import subprocess
import json
import logging
import re
from pathlib import Path
from datetime import datetime

EXTENSION_TO_FRONTEND = {
    ".c": "c2cpg.sh", ".cpp": "c2cpg.sh", ".cc": "c2cpg.sh",
    ".h": "c2cpg.sh", ".hpp": "c2cpg.sh",
    ".java": "javasrc2cpg.sh",
    ".py": "pysrc2cpg.sh",
    ".js": "jssrc2cpg.sh", ".jsx": "jssrc2cpg.sh",
    ".ts": "jssrc2cpg.sh", ".tsx": "jssrc2cpg.sh",
    ".cs": "csharpsrc2cpg.sh",
    ".kt": "kotlin2cpg.sh",
    ".rb": "rubysrc2cpg.sh",
    ".swift": "swiftsrc2cpg.sh",
    ".go": "gosrc2cpg.sh",
}

EXTENSION_TO_LANGUAGE = {
    ".c": "c", ".cpp": "cpp", ".cc": "cpp", ".h": "c", ".hpp": "cpp",
    ".java": "java", ".py": "python",
    ".js": "javascript", ".jsx": "javascript", ".ts": "typescript", ".tsx": "typescript",
    ".cs": "csharp", ".kt": "kotlin", ".rb": "ruby", ".swift": "swift", ".go": "go",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("cpg_generation.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)


def detect_frontend(file_path: Path):
    ext = file_path.suffix.lower()
    return EXTENSION_TO_FRONTEND.get(ext), EXTENSION_TO_LANGUAGE.get(ext)

def extract_usn(filename: str) -> str:
    """
    Extracts a normalized, uppercase USN from a filename regardless of
    the case used in the original file, e.g. matches both
    'PES2UG19CS100' and 'pes2ug19cs100'.
    """
    match = re.search(r"PES2UG\d{2}CS\d{3}", filename, re.IGNORECASE)
    if match:
        return match.group(0).upper()
    # fallback: sanitize the raw filename if no USN pattern is found
    cleaned = re.sub(r"[^A-Za-z0-9_]", "", filename)
    return cleaned[:40]

def generate_cpg(file_path: Path, out_dir: Path, timeout_sec=120):
    frontend, language = detect_frontend(file_path)
    if frontend is None:
        return {"status": "skipped", "reason": f"unsupported extension {file_path.suffix}"}

    student_id = extract_usn(file_path.stem)
    student_dir = out_dir / student_id
    student_dir.mkdir(parents=True, exist_ok=True)

    isolated_path = student_dir / file_path.name
    isolated_path.write_bytes(file_path.read_bytes())

    cpg_path = student_dir / "cpg.bin"
    cmd = [frontend, str(student_dir), "-o", str(cpg_path)]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
        if result.returncode != 0 or not cpg_path.exists():
            return {"status": "failed", "language": language, "stderr": result.stderr[-2000:]}
        return {"status": "success", "language": language, "cpg_path": str(cpg_path)}
    except subprocess.TimeoutExpired:
        return {"status": "failed", "language": language, "reason": "timeout"}
    except FileNotFoundError:
        return {"status": "failed", "language": language, "reason": f"{frontend} not found on PATH"}


def run_batch(dataset_dir: str, output_dir: str):
    dataset_path = Path(dataset_dir)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    manifest = {"run_timestamp": datetime.now().isoformat(), "results": {}, "ignored_non_source_files": []}

    files = [f for f in dataset_path.iterdir() if f.is_file()]
    log.info(f"Found {len(files)} files in {dataset_dir}")

    for f in files:
        if f.suffix.lower() not in EXTENSION_TO_FRONTEND:
            manifest["ignored_non_source_files"].append(f.name)
            log.warning(f"  IGNORED (not a recognized source file): {f.name}")
            continue

        student_id = extract_usn(f.stem)
        log.info(f"Processing {student_id} ({f.suffix})...")
        result = generate_cpg(f, out_path)
        manifest["results"][student_id] = result

        if result["status"] == "success":
            log.info(f"  OK: {student_id} [{result['language']}]")
        else:
            log.error(f"  FAILED: {student_id} - {result.get('reason', result.get('stderr', 'unknown'))}")

    manifest_path = out_path / "generation_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    succeeded = sum(1 for r in manifest["results"].values() if r["status"] == "success")
    failed = sum(1 for r in manifest["results"].values() if r["status"] == "failed")
    ignored = len(manifest["ignored_non_source_files"])
    log.info(f"Done. {succeeded} succeeded, {failed} failed, {ignored} non-source files ignored.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 generate_cpgs.py <dataset_dir> <output_dir>")
        sys.exit(1)
    run_batch(sys.argv[1], sys.argv[2])
