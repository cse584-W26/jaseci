#!/usr/bin/env bash
set -euo pipefail
frontend_dir=$(cd -- "$(dirname -- "$0")" && pwd)
experiment_dir=$(cd -- "$frontend_dir/../.." && pwd)
taskset -c 9,19 python "$frontend_dir/prepare_overlay.py"
mkdir -p "$frontend_dir/classes"
taskset -c 9,19 "$experiment_dir/boot-jdk8/bin/javac" -cp "$experiment_dir/deps/*" -d "$frontend_dir/classes" "$frontend_dir/src/webridge/wbridge/sql/ast/SQLAstVisitor.java" "$frontend_dir/FrontendTest.java"
taskset -c 9,19 "$experiment_dir/boot-jdk8/bin/java" -cp "$frontend_dir/classes:$experiment_dir/deps/*" FrontendTest "$frontend_dir/cases.json" "$experiment_dir/alignment/schema.sql" "$frontend_dir/test-results.json"
