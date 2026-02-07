"""Write EXIF/IPTC/XMP metadata to images using pyexiv2.

Replaces old image_updater.py (piexif-only, EXIF-only).
Supports all three metadata standards with preserve-existing behavior.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

import pyexiv2

from src.models import MetadataTags

logger = logging.getLogger(__name__)


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
        RuntimeError: If pyexiv2 fails to write.
    """
    if metadata.is_empty:
        return []

    # AIDEV-NOTE: Copy-then-modify prevents corruption if write fails mid-way
    target = image_path if overwrite else output_path
    if not overwrite:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(image_path, output_path)

    fields_written: list[str] = []

    # AIDEV-NOTE: pyexiv2.Image context manager ensures proper resource cleanup
    with pyexiv2.Image(str(target)) as img:
        if preserve_existing:
            existing_exif = img.read_exif()
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
