import pytest
import structlog

from app.core.logging_config import setup_logging


def test_setup_logging_returns_logger():
    logger = setup_logging()
    assert logger is not None
    assert hasattr(logger, "info")
    assert hasattr(logger, "error")


def test_log_output_is_json(capsys):
    logger = setup_logging()
    logger.info("test message", extra_field="value")
    out = capsys.readouterr().out
    import json
    parsed = json.loads(out)
    assert parsed["event"] == "test message"
    assert parsed["extra_field"] == "value"
    assert "timestamp" in parsed
    assert "level" in parsed
