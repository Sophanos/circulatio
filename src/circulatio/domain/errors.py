from __future__ import annotations


class CirculatioError(Exception):
    """Base domain error for Circulatio."""


class EntityNotFoundError(CirculatioError):
    """Raised when a requested record does not exist."""


class EntityDeletedError(CirculatioError):
    """Raised when a deleted record is requested without opting in."""


class ValidationError(CirculatioError):
    """Raised when a domain payload is invalid."""


class ConflictError(CirculatioError):
    """Raised when a create/update would violate a uniqueness rule."""


class PersistenceError(CirculatioError):
    """Raised when durable profile storage cannot safely satisfy a request."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class ProfileStorageCorruptionError(PersistenceError):
    """Raised when durable profile state is malformed or unreadable."""


class ProfileStorageConflictError(PersistenceError):
    """Raised when concurrent profile writers invalidate an optimistic update."""
