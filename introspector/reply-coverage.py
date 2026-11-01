import json
import os
import subprocess
from datetime import datetime, timezone
from typing import Any

from .config import Config
from .errors import AnalysisStepError, PathMissingError
from .loggers import get_logger, log_file_info, run_logged

logger = get_logger(__name__)


class Reply:
    def __init__(self, config: Config):
        self.config = config

    def _try_parse_show_overview_output(self) -> dict[str, Any] | None:
        output_dir = self.config.output_dir

        # Primary: .cache/coverage/whole/llvm-cov.json
        llvm_cov_path = os.path.join(output_dir, ".cache", "coverage", "whole", "llvm-cov.json")
        log_file_info(llvm_cov_path, "whole_llvm_cov")
        if os.path.isfile(llvm_cov_path):
            try:
                with open(llvm_cov_path, "r", encoding="utf-8") as fh:
                    raw = json.load(fh)
            except (json.JSONDecodeError, OSError) as exc:
                logger.error("Failed to parse %s: %s", llvm_cov_path, exc)
                return None
            try:
                totals = raw["data"][0]["totals"]
                parsed = {
                    "coverage_percent": totals.get("lines", {}).get("percent"),
                    "regions": totals.get("regions", {}).get("covered"),
                    "functions": totals.get("functions", {}).get("covered"),
                    "lines": totals.get("lines", {}).get("covered"),
                    "branches": totals.get("branches", {}).get("covered"),
                }
                logger.info(
                    "parsed whole/llvm-cov.json: coverage_percent=%s regions=%s functions=%s lines=%s branches=%s",
                    parsed["coverage_percent"], parsed["regions"], parsed["functions"],
                    parsed["lines"], parsed["branches"],
                )
                return parsed
            except (KeyError, IndexError, TypeError) as exc:
                logger.error("whole/llvm-cov.json has unexpected shape: %s", exc)
                return None

        logger.error(
            "whole/llvm-cov.json not found under %s/.cache/coverage/whole/",
            output_dir,
        )
        return None

    def _verify_run_marker(self, introspector_start_wall: datetime) -> None:
        marker_path = os.path.join(
            self.config.output_dir, ".cache", "coverage", "whole", "last-run.json"
        )
        log_file_info(marker_path, "show_overview_marker")
        if not os.path.isfile(marker_path):
            raise AnalysisStepError(
                "reply_full_coverage",
                f"show_overview did not write run marker at {marker_path} "
                "either show_overview is an older version without marker support, "
                "or it exited before completing gather",
            )
        try:
            with open(marker_path, "r", encoding="utf-8") as fh:
                marker = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            raise AnalysisStepError(
                "reply_full_coverage",
                f"show_overview run marker unreadable at {marker_path}: {exc}",
            )

        # Check 1: mode
        mode = marker.get("mode")
        if mode != "replay":
            raise AnalysisStepError(
                "reply_full_coverage",
                f"show_overview mode was {mode!r}, expected 'replay' "
                "--replay flag did not propagate, or show_overview overrode it",
            )

        # Check 2: completed_at is fresh
        completed_at_str = marker.get("completed_at")
        try:
            completed_at = datetime.fromisoformat(completed_at_str)
            if completed_at.tzinfo is None:
                completed_at = completed_at.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError) as exc:
            raise AnalysisStepError(
                "reply_full_coverage",
                f"show_overview marker has invalid completed_at={completed_at_str!r}: {exc}",
            )
        if completed_at < introspector_start_wall:
            raise AnalysisStepError(
                "reply_full_coverage",
                f"show_overview marker completed_at={completed_at.isoformat()} is "
                f"BEFORE this introspector started at {introspector_start_wall.isoformat()} "
                "show_overview did not actually re-run; it may have skipped or errored silently",
            )

        # Check 3: fuzzer_count
        fuzzer_count = marker.get("fuzzer_count", 0)
        if not fuzzer_count:
            raise AnalysisStepError(
                "reply_full_coverage",
                "show_overview ran but fuzzer_count=0",
            )

        # Check 4: llvm-cov.json non-empty
        if not marker.get("llvm_cov_json_size"):
            raise AnalysisStepError(
                "reply_full_coverage",
                "show_overview ran but llvm-cov.json size is 0",
            )

        logger.info(
            "show_overview marker verified: mode=%s completed_at=%s fuzzer_count=%s llvm_cov_json_size=%s",
            mode, completed_at.isoformat(), fuzzer_count, marker.get("llvm_cov_json_size"),
        )

    def analyze(self) -> dict[str, Any] | None:
        try:
            self.config.require_dir(self.config.vms_dir, "VMS directory")
        except PathMissingError as exc:
            logger.warning("Skipping final-coverage: %s", exc)
            return None

        introspector_start_wall = datetime.now(timezone.utc)

        try:
            run_logged(
                ["cov_overview", "--replay"],
                cwd=self.config.output_dir,
                log_ctx="reply_full_coverage",
            )
        except FileNotFoundError:
            raise AnalysisStepError(
                "reply_full_coverage",
                "cov_overview binary not found on PATH",
            )
        except subprocess.CalledProcessError as exc:
            stderr_snippet = (exc.stderr or "")
            stdout_snippet = (exc.stdout or "")
            detail = f"cov_overview failed (rc={exc.returncode})"
            if stderr_snippet:
                detail += f" stderr={stderr_snippet}"
            if stdout_snippet:
                detail += f" stdout={stdout_snippet}"
            raise AnalysisStepError("reply_full_coverage", detail)

        # Verify show_overview actually did work in THIS run.
        self._verify_run_marker(introspector_start_wall)

        parsed = self._try_parse_show_overview_output()
        if not parsed:
            raise AnalysisStepError(
                "reply_full_coverage",
                "no structured coverage produced, whole/llvm-cov.json missing or unparseable",
            )

        result = {
            "coverage_percent": parsed.get("coverage_percent"),
            "regions": parsed.get("regions"),
            "functions": parsed.get("functions"),
            "lines": parsed.get("lines"),
            "branches": parsed.get("branches"),
        }
        logger.info(
            "final metrics: coverage_percent=%s regions=%s functions=%s lines=%s branches=%s",
            result["coverage_percent"], result["regions"], result["functions"],
            result["lines"], result["branches"],
        )
        return result