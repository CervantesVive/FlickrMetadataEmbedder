import os
import tempfile
import pytest
from unittest.mock import patch, mock_open
from src.logger import Logger


class TestLogger:
    """Test suite for the Logger class."""

    def test_logger_initialization(self):
        """Test that Logger initializes with correct attributes."""
        logger = Logger("/test/output", verbose=True)
        assert logger.log_file == os.path.join("/test/output", "metadata_processing.log")
        assert logger.verbose is True

        logger_quiet = Logger("/another/path", verbose=False)
        assert logger_quiet.log_file == os.path.join("/another/path", "metadata_processing.log")
        assert logger_quiet.verbose is False

    def test_log_writes_to_file(self):
        """Test that log messages are written to the log file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = Logger(tmpdir, verbose=False)
            test_message = "Test log message"

            logger.log(test_message)

            # Verify the message was written to the file
            with open(logger.log_file, "r") as f:
                content = f.read()
            assert test_message + "\n" == content

    def test_log_appends_multiple_messages(self):
        """Test that multiple log calls append to the file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = Logger(tmpdir, verbose=False)
            messages = ["First message", "Second message", "Third message"]

            for msg in messages:
                logger.log(msg)

            # Verify all messages were appended
            with open(logger.log_file, "r") as f:
                content = f.read()

            for msg in messages:
                assert msg in content

            # Check messages are on separate lines
            lines = content.strip().split("\n")
            assert len(lines) == len(messages)

    def test_error_message_prints_to_console(self, capsys):
        """Test that error messages are printed to console regardless of verbose setting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = Logger(tmpdir, verbose=False)
            error_message = "[ERROR] Something went wrong"

            logger.log(error_message)

            # Check console output
            captured = capsys.readouterr()
            assert error_message in captured.out

    def test_warning_message_prints_to_console(self, capsys):
        """Test that warning messages are printed to console regardless of verbose setting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = Logger(tmpdir, verbose=False)
            warning_message = "[WARNING] This is a warning"

            logger.log(warning_message)

            # Check console output
            captured = capsys.readouterr()
            assert warning_message in captured.out

    def test_verbose_mode_prints_all_messages(self, capsys):
        """Test that verbose mode prints all messages to console."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = Logger(tmpdir, verbose=True)
            messages = [
                "Regular info message",
                "[ERROR] Error message",
                "[WARNING] Warning message",
                "Another info message"
            ]

            for msg in messages:
                logger.log(msg)

            # Check that all messages appear in console output
            captured = capsys.readouterr()
            for msg in messages:
                assert msg in captured.out

    def test_non_verbose_mode_suppresses_info_messages(self, capsys):
        """Test that non-verbose mode doesn't print regular info messages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = Logger(tmpdir, verbose=False)
            info_message = "Regular info message"

            logger.log(info_message)

            # Check that info message is NOT in console output
            captured = capsys.readouterr()
            assert info_message not in captured.out

            # But verify it was still written to file
            with open(logger.log_file, "r") as f:
                content = f.read()
            assert info_message in content

    def test_mixed_message_types(self, capsys):
        """Test logging with mixed message types in non-verbose mode."""
        # AIDEV-NOTE: Testing selective console output based on message type
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = Logger(tmpdir, verbose=False)

            messages = [
                ("Info: Processing started", False),  # (message, should_print)
                ("[ERROR] Failed to parse file", True),
                ("Info: Found 10 files", False),
                ("[WARNING] Missing metadata", True),
                ("Info: Processing complete", False),
            ]

            for msg, _ in messages:
                logger.log(msg)

            captured = capsys.readouterr()

            # Check console output matches expected behavior
            for msg, should_print in messages:
                if should_print:
                    assert msg in captured.out
                else:
                    assert msg not in captured.out

            # All messages should be in the log file
            with open(logger.log_file, "r") as f:
                content = f.read()
            for msg, _ in messages:
                assert msg in content

    def test_log_file_creation_in_nested_directory(self):
        """Test that log file is created correctly in nested directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_path = os.path.join(tmpdir, "nested", "output", "dir")
            os.makedirs(nested_path, exist_ok=True)

            logger = Logger(nested_path, verbose=False)
            logger.log("Test message in nested directory")

            expected_log_path = os.path.join(nested_path, "metadata_processing.log")
            assert os.path.exists(expected_log_path)

            with open(expected_log_path, "r") as f:
                content = f.read()
            assert "Test message in nested directory" in content

    def test_special_characters_in_messages(self):
        """Test that messages with special characters are handled correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = Logger(tmpdir, verbose=False)

            special_messages = [
                "Message with newline\ncharacter",
                "Message with 'quotes' and \"double quotes\"",
                "Message with unicode: `} =� �",
                "Message with tabs\t\there",
                "Path with backslashes: C:\\Users\\Test\\File.jpg"
            ]

            for msg in special_messages:
                logger.log(msg)

            with open(logger.log_file, "r", encoding="utf-8") as f:
                content = f.read()

            for msg in special_messages:
                assert msg in content

    def test_case_sensitive_error_warning_detection(self, capsys):
        """Test that error/warning detection is case-sensitive."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = Logger(tmpdir, verbose=False)

            # These should NOT trigger console output in non-verbose mode
            non_trigger_messages = [
                "error in lowercase",
                "warning without brackets",
                "[error] lowercase error",
                "[warning] lowercase warning",
                "ERROR without brackets",
                "WARNING without brackets"
            ]

            for msg in non_trigger_messages:
                logger.log(msg)

            captured = capsys.readouterr()
            for msg in non_trigger_messages:
                assert msg not in captured.out

            # These SHOULD trigger console output
            logger.log("[ERROR] Proper error")
            logger.log("[WARNING] Proper warning")

            captured = capsys.readouterr()
            assert "[ERROR] Proper error" in captured.out
            assert "[WARNING] Proper warning" in captured.out

    @patch("builtins.open", side_effect=IOError("Permission denied"))
    def test_log_file_write_error(self, mock_file):
        """Test behavior when log file cannot be written."""
        # AIDEV-NOTE: Testing error handling when file operations fail
        logger = Logger("/test/dir", verbose=False)

        # This should raise an IOError when trying to write
        with pytest.raises(IOError):
            logger.log("Test message")

    def test_empty_message_handling(self):
        """Test that empty messages are handled correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = Logger(tmpdir, verbose=True)

            logger.log("")

            with open(logger.log_file, "r") as f:
                content = f.read()

            # Empty message should still create a newline
            assert content == "\n"

    def test_concurrent_logging(self):
        """Test that multiple log calls in sequence work correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = Logger(tmpdir, verbose=False)

            # Simulate rapid logging
            for i in range(100):
                logger.log(f"Log entry {i}")

            with open(logger.log_file, "r") as f:
                lines = f.readlines()

            assert len(lines) == 100
            for i in range(100):
                assert f"Log entry {i}\n" == lines[i]