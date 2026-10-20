#!/usr/bin/env bash
set -euo pipefail
alignment_dir=$(cd -- "$(dirname -- "$0")" && pwd)
mkdir -p "$alignment_dir/classes"
"$alignment_dir/../boot-jdk8/bin/javac" -cp "$alignment_dir/../deps/*" -d "$alignment_dir/classes" "$alignment_dir/AlignedIc5.java"
exec "$alignment_dir/../boot-jdk8/bin/java" -Dalignment.dir="$alignment_dir" -cp "$alignment_dir/classes:$alignment_dir/../deps/*" AlignedIc5 "$@"
