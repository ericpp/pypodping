"""Error classes for the PodPing library."""


class PodpingError(Exception):
    """Base exception for PodPing operations."""
    pass


class PodpingConnectionError(PodpingError):
    """Error connecting to Hive nodes."""
    pass


class PodpingAuthenticationError(PodpingError):
    """Error with Hive account authentication."""
    pass


class PodpingValidationError(PodpingError):
    """Error validating input data (URLs, etc.)."""
    pass


class PodpingNetworkError(PodpingError):
    """Network-related error during operations."""
    pass
