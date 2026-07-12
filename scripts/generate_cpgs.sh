#!/bin/bash

# Usage: ./generate_cpgs.sh <week_dir> <out_dir>
# Example: ./generate_cpgs.sh /mnt/c/Users/admin/Downloads/lab_ec/lab_ec/week1/A /mnt/c/Users/admin/Downloads/lab_ec/lab_ec/week1/cpg_output

shopt -s nocaseglob

if [ $# -ne 2 ]; then
  echo "Usage: $0 <week_dir> <out_dir>"
  exit 1
fi

WEEK_DIR="$1"
OUT_DIR="$2"
mkdir -p "$OUT_DIR"

for file in "$WEEK_DIR"/*.c; do
  filename=$(basename "$file")
  usn=$(echo "$filename" | grep -oE "PES2UG[0-9]{2}CS[0-9]{3}")

  if [ -z "$usn" ]; then
    usn=$(echo "$filename" | tr -cd '[:alnum:]_' | cut -c1-40)
  fi

  student_dir="$OUT_DIR/$usn"
  mkdir -p "$student_dir"
  cp "$file" "$student_dir/solution.c"

  echo "Generating CPG for $usn..."
  c2cpg.sh "$student_dir" -o "$student_dir/cpg.bin"
done

echo "Done. CPGs are in $OUT_DIR"
