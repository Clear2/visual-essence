class VideoExtractionError(Exception):
    """Base error for expected video extraction failures."""


class UnsupportedPlatformError(VideoExtractionError):
    """The submitted URL belongs to a platform not enabled yet."""


class UnsafeVideoUrlError(VideoExtractionError):
    """The submitted or redirected URL violates outbound request policy."""


class UpstreamFetchError(VideoExtractionError):
    """The public platform could not be reached successfully."""


class ContentUnavailableError(VideoExtractionError):
    """The upstream page did not expose usable public video metadata."""


class VideoAnalysisError(VideoExtractionError):
    """Speech transcription or LLM interpretation could not be completed."""
