#!/usr/bin/env bash
set -uo pipefail

BENCHMARK_DURATION="${FUZZING_DURATION:-24h}"
echo "Starting agentic fuzzing benchmark for $BENCHMARK_DURATION."
git config --global --add safe.directory '*' || true
timeout --signal=INT --kill-after=60s "$BENCHMARK_DURATION" uv run main.py
FUZZ_EXIT_CODE=$?

if [[ "$FUZZ_EXIT_CODE" -ne 0 && "$FUZZ_EXIT_CODE" -ne 124 ]]; then
    echo "Agentic fuzzing exited with status $FUZZ_EXIT_CODE; skipping final coverage export." >&2
    exit "$FUZZ_EXIT_CODE"
fi

echo "Benchmark complete. Exporting full code coverage."
if [[ -z "${OUTPUT:-}" || ! -d "$OUTPUT/build/coverage/include" || ! -f "$OUTPUT/.cache/fuzzer_stat.json" ]]; then
    echo "No completed coverage build or fuzzer stats found; skipping final coverage export."
    exit 0
fi
bash /root/agentic-fuzzing/src/tools/copy-tools.sh
exec uv run python /usr/local/bin/cov_overview --replay