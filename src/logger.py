"""Logging setup with rich console output and file handler.

Replaces the old Logger class that opened/closed the log file on every message.
Uses stdlib logging with a rich console handler for pretty output.
"""

from __future__ import annotations

import logging
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler


def setup_logging(
    output_dir: str | Path | None = None,
    verbose: bool = False,
    quiet: bool = False,
) -> None:
    """Configure logging for the application.

    Args:
        output_dir: Directory for log file. If None, console-only.
        verbose: Enable DEBUG-level console output.
        quiet: Suppress INFO, show WARNING+ only.
    """
    root_logger = logging.getLogger("src")
    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers.clear()

    # Rich console handler
    console_level = logging.DEBUG if verbose else (logging.WARNING if quiet else logging.INFO)
    console = Console(stderr=True)
    rich_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=False,
        rich_tracebacks=True,
    )
    rich_handler.setLevel(console_level)
    root_logger.addHandler(rich_handler)

    # AIDEV-NOTE: File handler always captures DEBUG for complete audit trail
    if output_dir:
        log_path = Path(output_dir) / "metadata_processing.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        root_logger.addHandler(file_handler)
