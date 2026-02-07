"""CLI entry point for FlickrMetadataEmbedder.

Orchestrates the full pipeline: scan -> parse -> map -> write.
Supports --dry-run, --sanity-check, --resume, --fields, --strict.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from collections import Counter
from pathlib import Path

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table

from src.file_scanner import scan_directory, match_pairs
from src.image_writer import write_metadata
from src.logger import setup_logging
from src.metadata_mapper import map_metadata
from src.metadata_parser import parse_all_metadata
from src.models import ProcessingResult, ProcessingStatus
from src.sanity_checker import run_sanity_check
from src.state_manager import StateManager
from src.tag_definitions import ALL_FIELDS

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Embed Flickr metadata into image EXIF/IPTC/XMP",
    )
    parser.add_argument("--input-dir", required=True, help="Flickr export directory")
    parser.add_argument("--output-dir", help="Output directory for modified images")
    parser.add_argument("--overwrite", action="store_true", help="Modify originals in-place")
    parser.add_argument("--sanity-check", action="store_true", help="Validate matching only")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be embedded")
    parser.add_argument("--resume", action="store_true", help="Skip already-processed files")
    parser.add_argument("--force", action="store_true", help="Reprocess everything")
    parser.add_argument("--fields", help="Comma-separated fields to embed")
    parser.add_argument("--skip-fields", help="Comma-separated fields to skip")
    parser.add_argument("--verbose", action="store_true", help="Debug-level output")
    parser.add_argument("--quiet", action="store_true", help="Warnings and errors only")
    parser.add_argument("--strict", action="store_true", help="Stop on first error")
    return parser.parse_args()


def resolve_fields(args: argparse.Namespace) -> frozenset[str] | None:
    """Parse --fields and --skip-fields into a frozenset, or None for all."""
    if args.fields:
        requested = frozenset(f.strip() for f in args.fields.split(","))
        invalid = requested - ALL_FIELDS
        if invalid:
            print(f"Error: Unknown fields: {invalid}. Valid: {sorted(ALL_FIELDS)}")
            sys.exit(2)
        return requested
    if args.skip_fields:
        skip = frozenset(f.strip() for f in args.skip_fields.split(","))
        invalid = skip - ALL_FIELDS
        if invalid:
            print(f"Error: Unknown fields: {invalid}. Valid: {sorted(ALL_FIELDS)}")
            sys.exit(2)
        return ALL_FIELDS - skip
    return None


def main() -> int:
    """Main entry point. Returns exit code."""
    args = parse_args()

    # Validate args
    if not args.overwrite and not args.output_dir and not args.sanity_check and not args.dry_run:
        print("Error: --output-dir or --overwrite required (unless --sanity-check or --dry-run)")
        return 2

    output_target = args.output_dir if not args.overwrite else args.input_dir
    setup_logging(output_dir=output_target, verbose=args.verbose, quiet=args.quiet)

    # Sanity check mode — just validate and exit
    if args.sanity_check:
        return run_sanity_check(args.input_dir)

    # Phase 1: Scan files
    logger.info("Scanning %s...", args.input_dir)
    json_index, image_index = scan_directory(args.input_dir)
    pairs, orphan_jsons, orphan_images = match_pairs(json_index, image_index)
    logger.info(
        "Found %d matched pairs, %d orphan JSONs, %d orphan images",
        len(pairs), len(orphan_jsons), len(orphan_images),
    )

    # Phase 2: Parse metadata
    logger.info("Parsing metadata...")
    all_metadata = parse_all_metadata(json_index)
    logger.info("Parsed %d photo metadata files", len(all_metadata))

    # Phase 3: Process each pair
    fields = resolve_fields(args)
    results: list[ProcessingResult] = []
    console = Console()

    # State manager for resume support
    state_mgr = StateManager(output_target) if not args.dry_run else None
    processed_ids: set[str] = set()
    if args.resume and state_mgr and not args.force:
        processed_ids = state_mgr.load()

    start_time = time.time()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Embedding metadata", total=len(pairs))

        for pair in pairs:
            progress.update(task, advance=1)

            # Skip if already processed (resume mode)
            if pair.photo_id in processed_ids:
                results.append(ProcessingResult(
                    photo_id=pair.photo_id,
                    status=ProcessingStatus.SKIPPED,
                ))
                continue

            # Get parsed metadata for this photo
            photo = all_metadata.get(pair.photo_id)
            if not photo or not photo.has_embeddable_data:
                results.append(ProcessingResult(
                    photo_id=pair.photo_id,
                    status=ProcessingStatus.SKIPPED,
                ))
                continue

            # Map to tags
            mapped_tags = map_metadata(photo, fields)
            if mapped_tags.is_empty:
                results.append(ProcessingResult(
                    photo_id=pair.photo_id,
                    status=ProcessingStatus.SKIPPED,
                ))
                continue

            if args.dry_run:
                logger.info(
                    "[DRY RUN] Would embed %d tags into %s",
                    mapped_tags.field_count, pair.image_path.name,
                )
                results.append(ProcessingResult(
                    photo_id=pair.photo_id,
                    status=ProcessingStatus.SUCCESS,
                    fields_embedded=(
                        list(mapped_tags.exif.keys())
                        + list(mapped_tags.iptc.keys())
                        + list(mapped_tags.xmp.keys())
                    ),
                ))
                continue

            # Write metadata to image
            try:
                output_path = (
                    Path(args.output_dir) / pair.image_path.name
                    if args.output_dir
                    else pair.image_path
                )
                fields_written = write_metadata(
                    pair.image_path,
                    output_path,
                    mapped_tags,
                    overwrite=args.overwrite,
                )
                results.append(ProcessingResult(
                    photo_id=pair.photo_id,
                    status=ProcessingStatus.SUCCESS,
                    fields_embedded=fields_written,
                ))
                if state_mgr:
                    state_mgr.mark_processed(pair.photo_id)
            except Exception as e:
                logger.error("Failed to embed %s: %s", pair.image_path.name, e)
                results.append(ProcessingResult(
                    photo_id=pair.photo_id,
                    status=ProcessingStatus.FAILED_EMBED,
                    error_message=str(e),
                ))
                if args.strict:
                    logger.error("Stopping (--strict mode)")
                    break

    # Flush remaining state
    if state_mgr:
        state_mgr.save()

    duration = time.time() - start_time
    _print_summary(results, duration, console)

    has_failures = any(
        r.status in (ProcessingStatus.FAILED_PARSE, ProcessingStatus.FAILED_EMBED)
        for r in results
    )
    return 1 if has_failures else 0


def _print_summary(
    results: list[ProcessingResult],
    duration: float,
    console: Console,
) -> None:
    """Print processing summary using rich table."""
    status_counts = Counter(r.status for r in results)

    table = Table(title="Processing Summary")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")
    table.add_row("Total photos", str(len(results)))
    table.add_row("Embedded", str(status_counts.get(ProcessingStatus.SUCCESS, 0)))
    table.add_row("Skipped", str(status_counts.get(ProcessingStatus.SKIPPED, 0)))
    table.add_row("Failed (parse)", str(status_counts.get(ProcessingStatus.FAILED_PARSE, 0)))
    table.add_row("Failed (embed)", str(status_counts.get(ProcessingStatus.FAILED_EMBED, 0)))

    # Format duration
    minutes, seconds = divmod(int(duration), 60)
    table.add_row("Duration", f"{minutes}m {seconds}s")

    console.print(table)


if __name__ == "__main__":
    sys.exit(main())
