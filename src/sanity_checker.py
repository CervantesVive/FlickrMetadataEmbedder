"""Validate JSON-to-image matching using file_scanner.

Replaces old implementation that had bugs with filename splitting
and directory name matching.
"""

from __future__ import annotations

import logging
from pathlib import Path

from rich.console import Console
from rich.table import Table

from src.file_scanner import scan_directory, match_pairs

logger = logging.getLogger(__name__)


def run_sanity_check(input_dir: str | Path) -> int:
    """Run sanity check and print results.

    Args:
        input_dir: Root Flickr export directory.

    Returns:
        Exit code: 0 if all matched, 1 if orphans found.
    """
    # AIDEV-NOTE: Reuses file_scanner for consistent matching logic across the app
    json_index, image_index = scan_directory(input_dir)
    pairs, orphan_jsons, orphan_images = match_pairs(json_index, image_index)

    console = Console()
    table = Table(title="Sanity Check Results")
    table.add_column("Category", style="bold")
    table.add_column("Count", justify="right")
    table.add_row("Matched pairs", f"[green]{len(pairs)}[/green]")
    table.add_row(
        "Orphan JSONs (no image)",
        f"[yellow]{len(orphan_jsons)}[/yellow]" if orphan_jsons else "0",
    )
    table.add_row(
        "Orphan images (no JSON)",
        f"[yellow]{len(orphan_images)}[/yellow]" if orphan_images else "0",
    )
    console.print(table)

    if orphan_jsons:
        logger.warning("Orphan JSON IDs (first 20): %s", orphan_jsons[:20])
    if orphan_images:
        logger.warning("Orphan image IDs (first 20): %s", orphan_images[:20])

    return 1 if (orphan_jsons or orphan_images) else 0
