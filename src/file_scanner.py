"""Single-pass directory scanner with O(n) JSON-to-image matching.

Replaces O(n*m) substring matching in old image_updater.py.
Builds {photo_id -> Path} indexes for both JSONs and images in one walk,
then matches pairs via dict lookup.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from src.models import PhotoFilePair

# AIDEV-NOTE: Image naming is <original_name>_<photo_id>_o.jpg in data-download-* dirs
_IMAGE_ID_PATTERN = re.compile(r"_(\d+)_o\.\w+$")

# AIDEV-NOTE: JSON naming is photo_<id>.json (no hash suffix, confirmed from real export)
_JSON_ID_PATTERN = re.compile(r"^photo_(\d+)\.json$")

_IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".tiff", ".tif", ".gif"})


def scan_directory(input_dir: str | Path) -> tuple[dict[str, Path], dict[str, Path]]:
    """Single-pass walk building {photo_id -> path} for JSONs and images.

    Args:
        input_dir: Root Flickr export directory.

    Returns:
        Tuple of (json_index, image_index) where each maps photo_id -> file path.
    """
    json_index: dict[str, Path] = {}
    image_index: dict[str, Path] = {}

    for root, _, files in os.walk(input_dir):
        root_path = Path(root)
        dir_name = root_path.name

        for filename in files:
            file_path = root_path / filename

            # JSON metadata files (any directory)
            json_match = _JSON_ID_PATTERN.match(filename)
            if json_match:
                photo_id = json_match.group(1)
                json_index[photo_id] = file_path
                continue

            # Image files (only in data-download-* directories)
            # AIDEV-NOTE: Flickr exports put images only in data-download-* subdirs
            if dir_name.startswith("data-download-"):
                ext = file_path.suffix.lower()
                if ext in _IMAGE_EXTENSIONS:
                    img_match = _IMAGE_ID_PATTERN.search(filename)
                    if img_match:
                        photo_id = img_match.group(1)
                        image_index[photo_id] = file_path

    return json_index, image_index


def match_pairs(
    json_index: dict[str, Path],
    image_index: dict[str, Path],
) -> tuple[list[PhotoFilePair], list[str], list[str]]:
    """Match JSON metadata files to image files by photo_id.

    Args:
        json_index: Dict mapping photo_id -> json file path.
        image_index: Dict mapping photo_id -> image file path.

    Returns:
        Tuple of (matched_pairs, orphan_json_ids, orphan_image_ids).
    """
    all_ids = set(json_index.keys()) | set(image_index.keys())

    matched: list[PhotoFilePair] = []
    orphan_jsons: list[str] = []
    orphan_images: list[str] = []

    for photo_id in sorted(all_ids):
        has_json = photo_id in json_index
        has_image = photo_id in image_index

        if has_json and has_image:
            matched.append(PhotoFilePair(
                photo_id=photo_id,
                json_path=json_index[photo_id],
                image_path=image_index[photo_id],
            ))
        elif has_json:
            orphan_jsons.append(photo_id)
        else:
            orphan_images.append(photo_id)

    return matched, orphan_jsons, orphan_images
