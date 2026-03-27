"""
Unit tests for app/core/logging.py
Covers setup_logging() and the logger instance.
"""
import pytest
from app.core.logging import setup_logging, logger


def test_setup_logging_info_mode_does_not_raise():
    """setup_logging() without debug should not raise."""
    try:
        setup_logging(debug=False)
    except Exception as exc:
        pytest.fail(f"setup_logging(debug=False) raised: {exc}")


def test_setup_logging_debug_mode_does_not_raise():
    """setup_logging(debug=True) should not raise."""
    try:
        setup_logging(debug=True)
    except Exception as exc:
        pytest.fail(f"setup_logging(debug=True) raised: {exc}")


def test_logger_is_available():
    """The module-level logger should be importable and usable."""
    assert logger is not None


def test_logger_can_log_info():
    """Logger can emit an info message without raising."""
    setup_logging(debug=False)
    try:
        logger.info("test.event", key="value")
    except Exception as exc:
        pytest.fail(f"logger.info raised: {exc}")


def test_logger_can_log_warning():
    """Logger can emit a warning without raising."""
    setup_logging(debug=False)
    try:
        logger.warning("test.warning", reason="unit_test")
    except Exception as exc:
        pytest.fail(f"logger.warning raised: {exc}")
