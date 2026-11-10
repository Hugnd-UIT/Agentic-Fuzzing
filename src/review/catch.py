class Error(Exception):
    """Base error for all statistics analysis failures."""


class PathMissingError(Error):
    """A required path does not exist."""

    def __init__(self, name: str, path: str) -> None:
        self.name = name
        self.path = path
        super().__init__(f"{name} not found: {path}")


class AnalysisStepError(Error):
    """A single analysis step failed. Should not block other steps."""

    def __init__(self, step: str, detail: str) -> None:
        self.step = step
        self.detail = detail
        super().__init__(f"[{step}] {detail}")
