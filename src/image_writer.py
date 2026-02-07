"""Write EXIF/IPTC/XMP metadata to images using pyexiv2.

Replaces old image_updater.py (piexif-only, EXIF-only).
Supports all three metadata standards with preserve-existing behavior.
"""

from __future__ import annotations

import logging
import shutil
from contextlib import contextmanager
from pathlib import Path

import pyexiv2

from src.models import MetadataTags

logger = logging.getLogger(__name__)

# AIDEV-NOTE: pyexiv2 log levels: 0=debug, 1=info, 2=warn(default), 3=error, 4=mute
_LOG_LEVEL_WARN = 2
_LOG_LEVEL_MUTE = 4


@contextmanager
def _tolerant_image(path: str):
    """Open a pyexiv2.Image, retrying with muted log level on corrupt MakerNote errors.

    Many old cameras (Canon, Minolta, Olympus, Sony) produce MakerNote data that
    libexiv2 can't fully parse. These are non-fatal warnings that pyexiv2 raises
    as exceptions at the default log level. Muting lets libexiv2 skip the corrupt
    data and process the rest normally.
    """
    # AIDEV-NOTE: Open-with-retry is separated from yield to avoid double-yield footgun.
    # The RuntimeError always occurs during Image() construction (file parsing), not after.
    try:
        pyexiv2.set_log_level(_LOG_LEVEL_WARN)
        img = pyexiv2.Image(path)
    except RuntimeError:
        logger.debug("Retrying with tolerant mode: %s", Path(path).name)
        pyexiv2.set_log_level(_LOG_LEVEL_MUTE)
        img = pyexiv2.Image(path)

    try:
        yield img
    finally:
        img.close()
        pyexiv2.set_log_level(_LOG_LEVEL_WARN)


def write_metadata(
    image_path: Path,
    output_path: Path,
    metadata: MetadataTags,
    *,
    overwrite: bool = False,
    preserve_existing: bool = True,
) -> list[str]:
    """Write metadata tags to an image file.

    Args:
        image_path: Source image file.
        output_path: Where to save (same as image_path if overwrite=True).
        metadata: MetadataTags with exif/iptc/xmp dicts.
        overwrite: If True, modify image_path in-place (output_path ignored).
        preserve_existing: If True, skip tags that already have values.

    Returns:
        List of tag names that were actually written.

    Raises:
        OSError: If file I/O fails.
        RuntimeError: If pyexiv2 fails to write (after tolerant retry).
    """
    if metadata.is_empty:
        return []

    # AIDEV-NOTE: Check the output file if it already exists (re-run), otherwise check source.
    # In overwrite mode, source IS the target so reading source is correct either way.
    check_path = image_path if overwrite else output_path
    if not check_path.exists():
        check_path = image_path

    if preserve_existing:
        with _tolerant_image(str(check_path)) as img:
            # AIDEV-NOTE: read_exif() can fail with UnicodeDecodeError on images with
            # non-UTF-8 EXIF data (e.g., raw bytes in old Panasonic/Kodak cameras).
            # Treat unreadable EXIF as empty so our tags get written fresh.
            try:
                existing_exif = img.read_exif()
            except UnicodeDecodeError:
                logger.debug("Unreadable EXIF encoding in %s, will overwrite", check_path.name)
                existing_exif = {}
            existing_iptc = img.read_iptc()
            existing_xmp = img.read_xmp()
    else:
        existing_exif = {}
        existing_iptc = {}
        existing_xmp = {}

    # Filter out tags that already exist in the image
    new_exif = {k: v for k, v in metadata.exif.items() if k not in existing_exif}
    new_iptc = {k: v for k, v in metadata.iptc.items() if k not in existing_iptc}
    new_xmp = {k: v for k, v in metadata.xmp.items() if k not in existing_xmp}

    # AIDEV-NOTE: Skip file entirely if all metadata already present (idempotent)
    if not new_exif and not new_iptc and not new_xmp:
        return []

    # AIDEV-NOTE: Only copy source→output if output doesn't exist yet.
    # If output already exists (partial previous run), write directly to it
    # to avoid overwriting already-embedded tags.
    target = image_path if overwrite else output_path
    if not overwrite and not output_path.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(image_path, output_path)

    fields_written: list[str] = []

    with _tolerant_image(str(target)) as img:
        if new_exif:
            img.modify_exif(new_exif)
            fields_written.extend(new_exif.keys())
        if new_iptc:
            img.modify_iptc(new_iptc)
            fields_written.extend(new_iptc.keys())
        if new_xmp:
            img.modify_xmp(new_xmp)
            fields_written.extend(new_xmp.keys())

    return fields_written
