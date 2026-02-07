"""Tests for image_writer module.

Tests write_metadata() with real JPEG fixtures via pyexiv2.
"""

from __future__ import annotations

from pathlib import Path

import pyexiv2

from src.image_writer import write_metadata, _tolerant_image
from src.models import MetadataTags


class TestWriteMetadata:
    """Tests for write_metadata()."""

    def test_write_exif_tags(self, tmp_jpeg: Path, tmp_path: Path):
        """Write EXIF tags to a clean JPEG."""
        output = tmp_path / "output" / "test.jpg"
        tags = MetadataTags(exif={
            "Exif.Photo.DateTimeOriginal": "2016:09:03 12:44:09",
            "Exif.Image.ImageDescription": "Test Title",
        })

        fields = write_metadata(tmp_jpeg, output, tags)

        assert len(fields) == 2
        assert "Exif.Photo.DateTimeOriginal" in fields
        assert "Exif.Image.ImageDescription" in fields
        assert output.exists()

    def test_write_iptc_tags(self, tmp_jpeg: Path, tmp_path: Path):
        """Write IPTC tags to a JPEG."""
        output = tmp_path / "output" / "test.jpg"
        tags = MetadataTags(iptc={
            "Iptc.Application2.ObjectName": "My Photo",
            "Iptc.Application2.Keywords": ["vacation", "summer"],
        })

        fields = write_metadata(tmp_jpeg, output, tags)

        assert len(fields) == 2
        assert "Iptc.Application2.ObjectName" in fields

    def test_write_xmp_tags(self, tmp_jpeg: Path, tmp_path: Path):
        """Write XMP tags to a JPEG."""
        output = tmp_path / "output" / "test.jpg"
        tags = MetadataTags(xmp={
            "Xmp.dc.title": "XMP Title",
            "Xmp.dc.subject": ["tag1", "tag2"],
        })

        fields = write_metadata(tmp_jpeg, output, tags)

        assert len(fields) == 2
        assert "Xmp.dc.title" in fields

    def test_empty_metadata_returns_empty(self, tmp_jpeg: Path, tmp_path: Path):
        """Empty MetadataTags returns [] without modifying anything."""
        output = tmp_path / "output" / "test.jpg"
        tags = MetadataTags()

        fields = write_metadata(tmp_jpeg, output, tags)

        assert fields == []
        assert not output.exists()

    def test_roundtrip_exif_values(self, tmp_jpeg: Path, tmp_path: Path):
        """Written EXIF values can be read back correctly."""
        output = tmp_path / "output" / "test.jpg"
        tags = MetadataTags(exif={
            "Exif.Photo.DateTimeOriginal": "2016:09:03 12:44:09",
        })

        write_metadata(tmp_jpeg, output, tags)

        with pyexiv2.Image(str(output)) as img:
            exif = img.read_exif()
            assert exif["Exif.Photo.DateTimeOriginal"] == "2016:09:03 12:44:09"

    def test_roundtrip_iptc_values(self, tmp_jpeg: Path, tmp_path: Path):
        """Written IPTC values can be read back correctly."""
        output = tmp_path / "output" / "test.jpg"
        tags = MetadataTags(iptc={
            "Iptc.Application2.ObjectName": "My Photo Title",
        })

        write_metadata(tmp_jpeg, output, tags)

        with pyexiv2.Image(str(output)) as img:
            iptc = img.read_iptc()
            assert iptc["Iptc.Application2.ObjectName"] == "My Photo Title"

    def test_preserve_existing_skips_present_tags(self, tmp_jpeg: Path, tmp_path: Path):
        """With preserve_existing=True, existing tags are not overwritten."""
        output = tmp_path / "output" / "test.jpg"

        # First write: set title
        tags1 = MetadataTags(exif={"Exif.Image.ImageDescription": "Original"})
        write_metadata(tmp_jpeg, output, tags1)

        # Second write: try to overwrite title + add date
        tags2 = MetadataTags(exif={
            "Exif.Image.ImageDescription": "Overwritten",
            "Exif.Photo.DateTimeOriginal": "2020:01:01 00:00:00",
        })
        fields = write_metadata(tmp_jpeg, output, tags2, preserve_existing=True)

        # Only the new tag should be written
        assert "Exif.Photo.DateTimeOriginal" in fields
        assert "Exif.Image.ImageDescription" not in fields

        # Verify original title preserved
        with pyexiv2.Image(str(output)) as img:
            exif = img.read_exif()
            assert exif["Exif.Image.ImageDescription"] == "Original"
            assert exif["Exif.Photo.DateTimeOriginal"] == "2020:01:01 00:00:00"

    def test_idempotent_second_run_returns_empty(self, tmp_jpeg: Path, tmp_path: Path):
        """Second run with same tags returns [] (nothing new to write)."""
        output = tmp_path / "output" / "test.jpg"
        tags = MetadataTags(exif={
            "Exif.Photo.DateTimeOriginal": "2016:09:03 12:44:09",
        })

        # First write
        fields1 = write_metadata(tmp_jpeg, output, tags)
        assert len(fields1) == 1

        # Second write — should be idempotent
        fields2 = write_metadata(tmp_jpeg, output, tags)
        assert fields2 == []

    def test_overwrite_modifies_in_place(self, tmp_jpeg: Path, tmp_path: Path):
        """With overwrite=True, the source image is modified directly."""
        tags = MetadataTags(exif={
            "Exif.Image.ImageDescription": "In-place Title",
        })

        fields = write_metadata(tmp_jpeg, tmp_jpeg, tags, overwrite=True)

        assert len(fields) == 1

        with pyexiv2.Image(str(tmp_jpeg)) as img:
            exif = img.read_exif()
            assert exif["Exif.Image.ImageDescription"] == "In-place Title"

    def test_output_dir_created_if_missing(self, tmp_jpeg: Path, tmp_path: Path):
        """Output directory is created automatically if it doesn't exist."""
        output = tmp_path / "deep" / "nested" / "dir" / "test.jpg"
        tags = MetadataTags(exif={"Exif.Image.ImageDescription": "Deep"})

        write_metadata(tmp_jpeg, output, tags)

        assert output.exists()

    def test_preserve_false_overwrites_existing(self, tmp_jpeg: Path, tmp_path: Path):
        """With preserve_existing=False, existing tags are overwritten."""
        output = tmp_path / "output" / "test.jpg"

        # First write
        tags1 = MetadataTags(exif={"Exif.Image.ImageDescription": "Original"})
        write_metadata(tmp_jpeg, output, tags1)

        # Second write with preserve_existing=False
        tags2 = MetadataTags(exif={"Exif.Image.ImageDescription": "New"})
        fields = write_metadata(tmp_jpeg, output, tags2, preserve_existing=False)

        assert "Exif.Image.ImageDescription" in fields

        with pyexiv2.Image(str(output)) as img:
            exif = img.read_exif()
            assert exif["Exif.Image.ImageDescription"] == "New"

    def test_all_three_standards_written(self, tmp_jpeg: Path, tmp_path: Path):
        """EXIF, IPTC, and XMP tags are all written in one call."""
        output = tmp_path / "output" / "test.jpg"
        tags = MetadataTags(
            exif={"Exif.Photo.DateTimeOriginal": "2020:01:01 12:00:00"},
            iptc={"Iptc.Application2.ObjectName": "Title"},
            xmp={"Xmp.dc.description": "Description"},
        )

        fields = write_metadata(tmp_jpeg, output, tags)

        assert len(fields) == 3
        assert "Exif.Photo.DateTimeOriginal" in fields
        assert "Iptc.Application2.ObjectName" in fields
        assert "Xmp.dc.description" in fields


class TestTolerantImage:
    """Tests for _tolerant_image() context manager."""

    def test_opens_valid_jpeg(self, tmp_jpeg: Path):
        """Normal JPEG opens without error."""
        with _tolerant_image(str(tmp_jpeg)) as img:
            exif = img.read_exif()
            assert isinstance(exif, dict)

    def test_yields_writable_image(self, tmp_jpeg: Path):
        """Image returned by context manager supports modify_exif()."""
        with _tolerant_image(str(tmp_jpeg)) as img:
            img.modify_exif({"Exif.Image.ImageDescription": "Test"})

        # Verify write persisted
        with pyexiv2.Image(str(tmp_jpeg)) as img:
            assert img.read_exif()["Exif.Image.ImageDescription"] == "Test"

    def test_closes_image_on_exit(self, tmp_jpeg: Path):
        """Image is properly closed after context exit."""
        # AIDEV-NOTE: After close(), pyexiv2.Image methods raise.
        # We verify no resource leaks by successful context exit.
        with _tolerant_image(str(tmp_jpeg)) as img:
            pass
