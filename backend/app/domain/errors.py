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


class JDParseError(DomainError):
    pass


class JDNotParsed(DomainError):
    pass


class MatchingError(DomainError):
    pass


class FollowUpGenerationError(DomainError):
    pass
