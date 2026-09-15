class DomainError(Exception):
    pass


class NotFound(DomainError):
    pass


class Forbidden(DomainError):
    pass


class InvalidTransition(DomainError):
    pass


class CompanyHasApplications(DomainError):
    pass
