#!/usr/bin/env bash
set -euo pipefail
exp_root=$(cd -- "$(dirname -- "$0")" && pwd)
exec "$exp_root/boot-jdk8/bin/java" -Dorg.slf4j.simpleLogger.defaultLogLevel=warn -Dexperiment.dir="$exp_root" -cp "$exp_root/classes:$exp_root/deps/*" Ic5Benchmark "$@"
