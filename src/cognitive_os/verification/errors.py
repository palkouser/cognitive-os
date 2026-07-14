"""Typed verifier registry, selection, and execution failures."""


class VerificationError(RuntimeError):
    pass


class VerifierRegistrationError(VerificationError):
    pass


class VerifierNotFoundError(VerificationError):
    pass


class VerifierUnavailableError(VerificationError):
    pass


class AmbiguousVerifierSelectionError(VerificationError):
    pass


class VerifierSelectionError(VerificationError):
    pass


class VerificationPersistenceError(VerificationError):
    pass
