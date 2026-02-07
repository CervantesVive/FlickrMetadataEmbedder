"""Shared test fixtures for FlickrMetadataEmbedder."""

from __future__ import annotations

import json
import os
import struct
import tempfile
from pathlib import Path

import pytest


# AIDEV-NOTE: Minimal valid JPEG (1x1 white pixel) for pyexiv2 tests.
# Hand-crafted with JFIF header, quantization table, SOF0, Huffman tables, SOS, and EOI.
MINIMAL_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"  # SOI + JFIF
    b"\xff\xdb\x00\x43\x00"  # DQT marker
    + b"\x01" * 64  # 64-byte quantization table (all 1s)
    + b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"  # SOF0: 1x1, 1 component
    + b"\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"  # DHT DC
    + b"\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"  # DHT AC
    + b"\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00\x7b\x40\x00\x00"  # SOS + scan data
    + b"\xff\xd9"  # EOI
)


@pytest.fixture
def tmp_jpeg(tmp_path: Path) -> Path:
    """Create a minimal valid JPEG file for testing."""
    jpeg_path = tmp_path / "test_image.jpg"
    jpeg_path.write_bytes(MINIMAL_JPEG)
    return jpeg_path


@pytest.fixture
def flickr_json_data() -> dict:
    """Standard Flickr photo JSON data for testing."""
    return {
        "id": "28985409503",
        "name": "2016-09-03 12.44.09",
        "description": "",
        "date_taken": "2016-09-03 12:44:09",
        "rotation": 0,
        "license": "All Rights Reserved",
        "geo": [],
        "tags": [{"tag": "vacation"}, {"tag": "summer"}],
        "albums": [{"title": "Summer 2016"}],
        "groups": [],
        "people": [],
        "notes": [],
        "comments": [],
        "privacy": "friend & family",
    }


@pytest.fixture
def flickr_export_dir(tmp_path: Path) -> Path:
    """Create a mock Flickr export directory structure.

    Structure:
        tmp_path/
            photo_111.json
            photo_222.json
            photo_333.json  (no matching image = orphan JSON)
            data-download-1/
                vacation_111_o.jpg
                beach_222_o.jpg
    """
    # JSON files in root
    for photo_id, name in [("111", "Vacation"), ("222", "Beach"), ("333", "Video")]:
        data = {
            "id": photo_id,
            "name": name,
            "description": "",
            "date_taken": f"2023-01-0{photo_id[0]} 12:00:00",
            "rotation": 0,
            "license": "All Rights Reserved",
            "geo": [],
            "tags": [],
            "albums": [],
        }
        json_path = tmp_path / f"photo_{photo_id}.json"
        json_path.write_text(json.dumps(data))

    # Image files in data-download directory
    img_dir = tmp_path / "data-download-1"
    img_dir.mkdir()
    (img_dir / "vacation_111_o.jpg").write_bytes(MINIMAL_JPEG)
    (img_dir / "beach_222_o.jpg").write_bytes(MINIMAL_JPEG)

    return tmp_path
