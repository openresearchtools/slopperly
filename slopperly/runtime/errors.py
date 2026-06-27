"""Runtime exception types shared by Slopperly adapters."""


class SlopperlyRuntimeError(RuntimeError):
    """Base class for local runtime failures."""


class RuntimeUnavailableError(SlopperlyRuntimeError):
    """Raised when a required local runtime or workflow pack is unavailable."""


class WorkflowValidationError(SlopperlyRuntimeError):
    """Raised when a committed workflow pack is malformed or incomplete."""
