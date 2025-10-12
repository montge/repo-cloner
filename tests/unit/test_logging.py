"""Tests for structured logging system."""

import json
import logging
from io import StringIO

from repo_cloner.logging_config import (
    ContextFilter,
    JSONFormatter,
    configure_logging,
    get_logger,
    log_context,
)


class TestJSONFormatter:
    """Test suite for JSON log formatter."""

    def test_format_basic_log_message(self):
        """Test that basic log message is formatted as JSON."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        assert log_data["message"] == "Test message"
        assert log_data["level"] == "INFO"
        assert log_data["logger"] == "test"
        assert "timestamp" in log_data
        assert log_data["filename"] == "test.py"
        assert log_data["lineno"] == 42

    def test_format_includes_exception_info(self):
        """Test that exception info is included in JSON logs."""
        formatter = JSONFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        assert log_data["message"] == "Error occurred"
        assert log_data["level"] == "ERROR"
        assert "exception" in log_data
        assert "ValueError" in log_data["exception"]
        assert "Test error" in log_data["exception"]

    def test_format_includes_extra_fields(self):
        """Test that extra fields are included in JSON logs."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Add extra fields
        record.repository = "https://gitlab.com/org/repo"
        record.operation = "clone"
        record.duration = 12.5

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        assert log_data["repository"] == "https://gitlab.com/org/repo"
        assert log_data["operation"] == "clone"
        assert log_data["duration"] == 12.5

    def test_format_handles_non_json_serializable_extra_fields(self):
        """Test that non-JSON-serializable fields are converted to strings."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Add non-serializable object
        class CustomObject:
            def __repr__(self):
                return "<CustomObject>"

        record.custom_obj = CustomObject()

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        assert log_data["custom_obj"] == "<CustomObject>"


class TestContextFilter:
    """Test suite for context filter."""

    def test_filter_adds_context_to_record(self):
        """Test that context filter adds context fields to log record."""
        context = {"request_id": "abc123", "user": "admin"}
        filter_obj = ContextFilter(context)

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )

        filter_obj.filter(record)

        assert record.request_id == "abc123"
        assert record.user == "admin"

    def test_filter_allows_all_records(self):
        """Test that context filter doesn't block any records."""
        filter_obj = ContextFilter({})
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )

        result = filter_obj.filter(record)
        assert result is True


class TestLogContext:
    """Test suite for log context manager."""

    def test_context_manager_adds_fields_to_logs(self):
        """Test that context manager adds fields to all logs within context."""
        logger = logging.getLogger("test_context")
        logger.setLevel(logging.INFO)

        # Capture log output
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JSONFormatter())
        handler.addFilter(ContextFilter())  # Add context filter
        logger.addHandler(handler)

        with log_context(repository="https://gitlab.com/org/repo", operation="clone"):
            logger.info("Starting clone")
            logger.info("Clone complete")

        logger.removeHandler(handler)

        output = stream.getvalue()
        lines = [line for line in output.strip().split("\n") if line]

        # Both log messages should have context
        for line in lines:
            log_data = json.loads(line)
            assert log_data["repository"] == "https://gitlab.com/org/repo"
            assert log_data["operation"] == "clone"

    def test_context_manager_cleans_up_after_exit(self):
        """Test that context is removed after exiting context manager."""
        logger = logging.getLogger("test_cleanup")
        logger.setLevel(logging.INFO)

        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JSONFormatter())
        handler.addFilter(ContextFilter())  # Add context filter
        logger.addHandler(handler)

        # Log with context
        with log_context(temp_field="value"):
            logger.info("Inside context")

        # Log without context
        logger.info("Outside context")

        logger.removeHandler(handler)

        output = stream.getvalue()
        lines = [line for line in output.strip().split("\n") if line]

        # First log should have temp_field
        log1 = json.loads(lines[0])
        assert log1["temp_field"] == "value"

        # Second log should NOT have temp_field
        log2 = json.loads(lines[1])
        assert "temp_field" not in log2

    def test_nested_contexts_merge_fields(self):
        """Test that nested contexts merge their fields."""
        logger = logging.getLogger("test_nested")
        logger.setLevel(logging.INFO)

        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JSONFormatter())
        handler.addFilter(ContextFilter())  # Add context filter
        logger.addHandler(handler)

        with log_context(level1="outer"):
            with log_context(level2="inner"):
                logger.info("Nested log")

        logger.removeHandler(handler)

        output = stream.getvalue()
        log_data = json.loads(output.strip())

        assert log_data["level1"] == "outer"
        assert log_data["level2"] == "inner"


class TestConfigureLogging:
    """Test suite for logging configuration."""

    def test_configure_logging_sets_log_level(self):
        """Test that configure_logging sets the correct log level."""
        logger = configure_logging(level="DEBUG", json_format=False)
        assert logger.level == logging.DEBUG

        logger = configure_logging(level="INFO", json_format=False)
        assert logger.level == logging.INFO

        logger = configure_logging(level="WARNING", json_format=False)
        assert logger.level == logging.WARNING

    def test_configure_logging_json_format(self):
        """Test that configure_logging can enable JSON formatting."""
        logger = configure_logging(level="INFO", json_format=True)

        # Check that at least one handler uses JSONFormatter
        has_json_formatter = False
        for handler in logger.handlers:
            if isinstance(handler.formatter, JSONFormatter):
                has_json_formatter = True
                break

        assert has_json_formatter

    def test_configure_logging_plain_format(self):
        """Test that configure_logging can use plain text formatting."""
        logger = configure_logging(level="INFO", json_format=False)

        # Check that handlers don't use JSONFormatter
        for handler in logger.handlers:
            assert not isinstance(handler.formatter, JSONFormatter)

    def test_configure_logging_sets_log_file(self, tmp_path):
        """Test that configure_logging can write to a file."""
        log_file = tmp_path / "test.log"
        logger = configure_logging(level="INFO", log_file=str(log_file), json_format=False)

        logger.info("Test message")

        assert log_file.exists()
        content = log_file.read_text()
        assert "Test message" in content

    def test_configure_logging_json_to_file(self, tmp_path):
        """Test that JSON logs can be written to file."""
        log_file = tmp_path / "test.json"
        logger = configure_logging(level="INFO", log_file=str(log_file), json_format=True)

        logger.info("Test message", extra={"operation": "test"})

        assert log_file.exists()
        content = log_file.read_text()

        # Parse JSON log
        log_data = json.loads(content.strip())
        assert log_data["message"] == "Test message"
        assert log_data["operation"] == "test"


class TestGetLogger:
    """Test suite for get_logger utility."""

    def test_get_logger_returns_logger_with_name(self):
        """Test that get_logger returns a logger with the correct name."""
        logger = get_logger("test_module")
        assert logger.name == "repo_cloner.test_module"

    def test_get_logger_inherits_root_configuration(self):
        """Test that loggers inherit from root repo_cloner logger."""
        # Configure root logger
        root_logger = configure_logging(level="DEBUG", json_format=True)

        # Get child logger
        child_logger = get_logger("child")

        # Child should inherit level from root
        assert child_logger.level == logging.NOTSET  # Inherits from parent
        assert child_logger.parent == root_logger

    def test_get_logger_supports_extra_fields(self):
        """Test that loggers support extra fields in log calls."""
        logger = get_logger("test_extra")
        logger.setLevel(logging.INFO)

        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)

        logger.info("Test message", extra={"custom_field": "value"})

        logger.removeHandler(handler)

        output = stream.getvalue()
        log_data = json.loads(output.strip())

        assert log_data["custom_field"] == "value"


class TestLoggingIntegration:
    """Integration tests for the complete logging system."""

    def test_end_to_end_structured_logging(self, tmp_path):
        """Test complete workflow with structured logging."""
        log_file = tmp_path / "integration.log"

        # Configure logging
        logger = configure_logging(level="INFO", log_file=str(log_file), json_format=True)

        # Use context manager and log various events
        with log_context(session_id="session123"):
            logger.info("Session started")

            with log_context(operation="clone", repository="https://gitlab.com/org/repo"):
                logger.info("Starting repository clone")
                logger.info("Clone progress", extra={"percent": 50})
                logger.info("Clone complete", extra={"duration": 10.5})

            logger.info("Session ending")

        # Read and verify logs
        logs = []
        for line in log_file.read_text().strip().split("\n"):
            if line:
                logs.append(json.loads(line))

        # Should have 5 log messages:
        # session started, clone started, clone progress, clone complete,
        # session ending
        assert len(logs) == 5

        # All logs should have session_id
        for log in logs:
            assert log["session_id"] == "session123"

        # Clone logs should have operation and repository
        # logs[0] = "Session started"
        # logs[1] = "Starting repository clone" with operation="clone"
        # logs[2] = "Clone progress" with percent=50
        # logs[3] = "Clone complete" with duration=10.5
        # logs[4] = "Session ending"
        assert logs[1]["operation"] == "clone"
        assert logs[1]["repository"] == "https://gitlab.com/org/repo"
        assert logs[2]["percent"] == 50
        assert logs[3]["duration"] == 10.5

    def test_exception_logging_includes_traceback(self, tmp_path):
        """Test that exceptions are logged with full traceback."""
        log_file = tmp_path / "exceptions.log"
        logger = configure_logging(level="ERROR", log_file=str(log_file), json_format=True)

        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.exception("An error occurred", extra={"operation": "test"})

        # Read log
        log_data = json.loads(log_file.read_text().strip())

        assert log_data["level"] == "ERROR"
        assert log_data["message"] == "An error occurred"
        assert log_data["operation"] == "test"
        assert "exception" in log_data
        assert "ValueError: Test exception" in log_data["exception"]
        assert "Traceback" in log_data["exception"]
