class HybridSubmitError(RuntimeError):
    """Base class for submit errors."""


class ManifestError(HybridSubmitError):
    pass


class QuotaExceededError(HybridSubmitError):
    pass


class BackendDownError(HybridSubmitError):
    pass


class SubmissionError(HybridSubmitError):
    pass
