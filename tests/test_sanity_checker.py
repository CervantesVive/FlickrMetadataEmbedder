"""Tests for sanity_checker module.

Tests run_sanity_check() which validates JSON-to-image matching.
"""

from __future__ import annotations

import json
from pathlib import Path

from tests.conftest import MINIMAL_JPEG

from src.sanity_checker import run_sanity_check


class TestRunSanityCheck:
    """Tests for run_sanity_check()."""

    def test_all_matched_returns_zero(self, flickr_export_dir: Path):
        """When all JSONs have matching images (and vice versa), returns 0.

        Note: flickr_export_dir has photo_333 as an orphan JSON (no image),
        so we remove it to get a clean match.
        """
        (flickr_export_dir / "photo_333.json").unlink()

        result = run_sanity_check(flickr_export_dir)

        assert result == 0

    def test_orphan_jsons_returns_one(self, flickr_export_dir: Path):
        """Orphan JSONs (no matching image) cause return code 1."""
        # flickr_export_dir has photo_333.json with no matching image
        result = run_sanity_check(flickr_export_dir)

        assert result == 1

    def test_orphan_images_returns_one(self, flickr_export_dir: Path):
        """Orphan images (no matching JSON) cause return code 1."""
        # Remove the orphan JSON to clear that issue
        (flickr_export_dir / "photo_333.json").unlink()

        # Add an image with no matching JSON
        img_dir = flickr_export_dir / "data-download-1"
        (img_dir / "random_999_o.jpg").write_bytes(MINIMAL_JPEG)

        result = run_sanity_check(flickr_export_dir)

        assert result == 1

    def test_empty_directory_returns_zero(self, tmp_path: Path):
        """Empty directory has no orphans, returns 0."""
        result = run_sanity_check(tmp_path)

        assert result == 0

    def test_only_jsons_no_images(self, tmp_path: Path):
        """JSONs without any images are all orphans, returns 1."""
        data = {"id": "100", "name": "Test"}
        (tmp_path / "photo_100.json").write_text(json.dumps(data))

        result = run_sanity_check(tmp_path)

        assert result == 1
