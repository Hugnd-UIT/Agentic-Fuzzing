# review

Post-fuzzing analysis package for Agentic Fuzzing. Runs inside the analysis container
after the core fuzzing engine finishes, producing structured JSON output.

## Quick Start

```bash
# Set the output directory (usually done automatically by the Controller)
export OUTPUT=/path/to/fuzzing/output/project_name

# Run the review analysis step
python3 -m src.review.main
```

## Architecture

Each analysis module exposes a single `analyze() -> dict | None`
method. The `main` entry-point iterates over the registered steps with
per-step error isolation — one failure does not block the others.

```
src/review/
  __init__.py              # Package marker
  main.py                  # Entry-point: python3 -m src.review.main
  config.py                # Config — unified path discovery from $OUTPUT
  catch.py                 # Error / PathMissingError / AnalysisStepError
  report.py                # write_json() + try_write_png() (matplotlib optional)
  log.py                   # configure_logging() / get_logger()
  reply.py                 # Reply — final coverage summary
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OUTPUT` | Yes | Root directory of the fuzzing output for a project |

The directory at `$OUTPUT` is expected to follow this layout:

```
$OUTPUT/
  .cache/
    logs/                  # Agent log files (*.log)
    fuzzers/               # Fuzzer working directories
    coverage/              # LLVM profdata files per fuzzer
    fuzzer_stat.json       # Fuzzer finish timestamps
    review/                # Output directory (created automatically)
  .vms/
    index.json             # VM snapshots with agent phase timestamps
  build/
    build.sh               # Build script (used by core, not analysis)
    coverage/lib/lib*.so   # Coverage-instrumented shared library
  fuzzers/                 # Built fuzzer binaries
```

## Remaining Analysis Step

The single step produces a JSON file under `$OUTPUT/.cache/review/`.
Missing data causes the step to be skipped with a warning.

### Final Coverage Reply → `final_coverage.json`

Runs `cov_overview --replay` and parses the resulting coverage
data into the final coverage summary that the Storage normalizer consumes.

```json
{
  "coverage_percent": 12.3,
  "regions": 15.6,
  "functions": 22.1,
  "lines": 10.8,
  "branches": 8.4
}
```

**Dependencies:** `cov_overview` in PATH (copied by
`copy-tools.sh`).

> The JSON examples below this section in older revisions described
> `coverage_over_time`, `token_cost`, `instr_classify`, and `agent_gantt`.
> Those analyses no longer run from this package — see the scope note above.

## Error Handling

- **`PathMissingError`** — Required directory/file not found; the step logs a
  warning and returns `None`.
- **`AnalysisStepError`** — A step-specific failure (e.g. a tool not found);
  logged and skipped.
- **Unexpected exceptions** — Caught at the `main` level; logged with full
  traceback, other steps continue.

If all steps fail, the process exits with code 1. Otherwise it exits 0
regardless of how many individual steps succeeded.

## Integration with Controller

The Controller automatically launches an analysis container after a fuzzing
task completes successfully. It reuses the same Docker image and compose
template, changing only:

- `command`: `bash /root/Agentic Fuzzing/src/tools/copy-tools.sh && python3 -m src.review.main`
- `auto_clean`: `0` (prevents output deletion)
- `write_mode`: `True` (allows writing analysis JSON)
- `container_name`: `{original_name}_analysis`

The analysis results are then picked up by the Storage normalizer and exposed
through the Backend API for frontend visualization.