"""Application exceptions, mapped to HTTP responses at the API boundary.

Lower layers raise these instead of HTTPException, so services,
repositories and clients stay free of web-framework concerns. Messages are
written to be safe to show to API clients: no stack traces, no secrets.
"""

from __future__ import annotations


class AppError(Exception):
    """Base class for errors the API turns into a structured response."""

    status_code = 500
    code = "internal_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidRequestError(AppError):
    status_code = 400
    code = "invalid_request"


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class DependencyUnavailableError(AppError):
    """An external system (Pinecone, a model, the LLM) could not be used."""

    status_code = 503
    code = "dependency_unavailable"

    def __init__(self, dependency: str, message: str) -> None:
        super().__init__(message)
        self.dependency = dependency


class ConfigurationError(AppError):
    """The service is misconfigured (e.g. the Pinecone index doesn't exist)."""

    status_code = 503
    code = "misconfigured"
