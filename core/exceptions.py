class DatasetLoadError(Exception):
    """Raised when the source dataset file cannot be read or parsed at all."""


class InvalidRecordError(Exception):
    """Raised when a single source record fails validation beyond recovery."""
