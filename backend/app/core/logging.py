import logging


def configure_logging() -> None:
    """Minimal stdlib logging setup. Structured logging (structlog,
    request-id correlation) was cut from this project's scope - see
    PLAN.md's "What Was Cut" - but the global exception handlers in
    main.py still need somewhere to log unexpected errors server-side
    without leaking them to the client."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
