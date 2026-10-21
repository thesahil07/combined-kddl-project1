"""Framework-independent errors raised by application use cases."""


class ApplicationError(Exception):
    """Base class for expected business and workflow failures."""


class ResourceNotFoundError(ApplicationError):
    pass


class ValidationError(ApplicationError):
    pass


class InvalidStateError(ApplicationError):
    pass


class AuthorizationError(ApplicationError):
    pass


class ExternalServiceUnavailableError(ApplicationError):
    pass
