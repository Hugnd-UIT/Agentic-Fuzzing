# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Zero-false-positive crash pre-triage gatekeeper in `run_fuzzer`.
- ASan/UBSan/MSan banner and Linux kernel signal-termination verification.
- Automated Stack Frame #0 blame attribution (Harness vs Library fault).
- Direct `HARNESS_BUG` classification bypassing `CrashAnalyzerAgent`.
- Crash deduplication engine via compiler `DEDUP_TOKEN` and stack hashing.
- Automatic filtering and cleanup of benign non-crash exits (`exit 1`).

### Changed

- Aggregate multi-instance AFL crashes with content-based MD5 hashing.
