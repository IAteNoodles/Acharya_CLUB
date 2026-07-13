import structlog
from structlog.processors import JSONRenderer, TimeStamper, add_log_level


def setup_logging():
    structlog.configure(
        processors=[
            add_log_level,
            TimeStamper(fmt="iso"),
            structlog.processors.UnicodeDecoder(),
            JSONRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    return structlog.get_logger()
