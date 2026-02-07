"""Tests for logger module.

Tests setup_logging() with its console level and file handler configuration.
"""

from __future__ import annotations

import logging
from pathlib import Path

from rich.logging import RichHandler

from src.logger import setup_logging


class TestSetupLogging:
    """Tests for setup_logging()."""

    def _get_src_logger(self) -> logging.Logger:
        """Get the 'src' logger configured by setup_logging()."""
        return logging.getLogger("src")

    def test_default_console_level_is_info(self):
        """Default setup has console handler at INFO level."""
        setup_logging()
        logger = self._get_src_logger()

        assert logger.level == logging.DEBUG  # Root level is DEBUG
        rich_handlers = [h for h in logger.handlers if isinstance(h, RichHandler)]
        assert len(rich_handlers) == 1
        assert rich_handlers[0].level == logging.INFO

    def test_verbose_sets_debug_level(self):
        """verbose=True sets console handler to DEBUG."""
        setup_logging(verbose=True)
        logger = self._get_src_logger()

        rich_handlers = [h for h in logger.handlers if isinstance(h, RichHandler)]
        assert rich_handlers[0].level == logging.DEBUG

    def test_quiet_sets_warning_level(self):
        """quiet=True sets console handler to WARNING."""
        setup_logging(quiet=True)
        logger = self._get_src_logger()

        rich_handlers = [h for h in logger.handlers if isinstance(h, RichHandler)]
        assert rich_handlers[0].level == logging.WARNING

    def test_clears_existing_handlers(self):
        """Each call clears previously configured handlers."""
        setup_logging()
        setup_logging()
        logger = self._get_src_logger()

        # Should have exactly 1 handler (console only), not 2
        assert len(logger.handlers) == 1

    def test_file_handler_created_with_output_dir(self, tmp_path: Path):
        """output_dir creates a file handler writing to metadata_processing.log."""
        setup_logging(output_dir=tmp_path)
        logger = self._get_src_logger()

        file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) == 1

        log_path = tmp_path / "metadata_processing.log"
        assert log_path.exists()

    def test_no_file_handler_without_output_dir(self):
        """Without output_dir, no file handler is created."""
        setup_logging(output_dir=None)
        logger = self._get_src_logger()

        file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) == 0

    def test_file_handler_at_debug_level(self, tmp_path: Path):
        """File handler always captures at DEBUG level for audit trail."""
        setup_logging(output_dir=tmp_path, quiet=True)
        logger = self._get_src_logger()

        file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
        assert file_handlers[0].level == logging.DEBUG

    def test_log_messages_written_to_file(self, tmp_path: Path):
        """Log messages actually appear in the log file."""
        setup_logging(output_dir=tmp_path)
        logger = logging.getLogger("src.test")
        logger.info("Test message for file")

        # Flush the file handler to ensure content is written
        for handler in logging.getLogger("src").handlers:
            handler.flush()

        log_path = tmp_path / "metadata_processing.log"
        content = log_path.read_text()
        assert "Test message for file" in content

    def test_output_dir_created_if_missing(self, tmp_path: Path):
        """Nested output directory is created automatically."""
        log_dir = tmp_path / "nested" / "log" / "dir"
        setup_logging(output_dir=log_dir)

        assert (log_dir / "metadata_processing.log").exists()
