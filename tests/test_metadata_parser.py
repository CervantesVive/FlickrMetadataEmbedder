"""Tests for metadata_parser module.

Tests parse_photo_json() and parse_all_metadata() against the new
FlickrPhoto Pydantic model API.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.metadata_parser import parse_photo_json, parse_all_metadata
from src.models import FlickrPhoto


class TestParsePhotoJson:
    """Tests for parse_photo_json()."""

    def test_valid_full_json(self, tmp_path: Path, flickr_json_data: dict):
        """Parse a complete Flickr JSON file into FlickrPhoto."""
        json_path = tmp_path / "photo_28985409503.json"
        json_path.write_text(json.dumps(flickr_json_data))

        result = parse_photo_json(json_path)

        assert result is not None
        assert isinstance(result, FlickrPhoto)
        assert result.id == "28985409503"
        assert result.name == "2016-09-03 12.44.09"
        assert result.date_taken == "2016-09-03 12:44:09"
        assert result.license == "All Rights Reserved"
        assert result.rotation == 0

    def test_tags_parsed(self, tmp_path: Path, flickr_json_data: dict):
        """Tags array is parsed into FlickrTag objects."""
        json_path = tmp_path / "photo_123.json"
        json_path.write_text(json.dumps(flickr_json_data))

        result = parse_photo_json(json_path)

        assert len(result.tags) == 2
        assert result.tags[0].tag == "vacation"
        assert result.tags[1].tag == "summer"

    def test_albums_parsed(self, tmp_path: Path, flickr_json_data: dict):
        """Albums array is parsed into FlickrAlbum objects."""
        json_path = tmp_path / "photo_123.json"
        json_path.write_text(json.dumps(flickr_json_data))

        result = parse_photo_json(json_path)

        assert len(result.albums) == 1
        assert result.albums[0].title == "Summer 2016"

    def test_empty_geo_array_becomes_none(self, tmp_path: Path, flickr_json_data: dict):
        """Flickr geo=[] (empty array) is normalized to None."""
        assert flickr_json_data["geo"] == []
        json_path = tmp_path / "photo_123.json"
        json_path.write_text(json.dumps(flickr_json_data))

        result = parse_photo_json(json_path)

        assert result.geo is None

    def test_geo_dict_becomes_geolocation(self, tmp_path: Path, flickr_json_data: dict):
        """Flickr geo dict with lat/lon is parsed into GeoLocation."""
        flickr_json_data["geo"] = {
            "latitude": 37.7749,
            "longitude": -122.4194,
            "accuracy": 16,
        }
        json_path = tmp_path / "photo_123.json"
        json_path.write_text(json.dumps(flickr_json_data))

        result = parse_photo_json(json_path)

        assert result.geo is not None
        assert result.geo.latitude == pytest.approx(37.7749)
        assert result.geo.longitude == pytest.approx(-122.4194)
        assert result.geo.accuracy == 16

    def test_empty_description_becomes_none(self, tmp_path: Path, flickr_json_data: dict):
        """Empty string description is normalized to None."""
        assert flickr_json_data["description"] == ""
        json_path = tmp_path / "photo_123.json"
        json_path.write_text(json.dumps(flickr_json_data))

        result = parse_photo_json(json_path)

        assert result.description is None

    def test_nonempty_description_preserved(self, tmp_path: Path, flickr_json_data: dict):
        """Non-empty description is preserved as-is."""
        flickr_json_data["description"] = "A beautiful sunset"
        json_path = tmp_path / "photo_123.json"
        json_path.write_text(json.dumps(flickr_json_data))

        result = parse_photo_json(json_path)

        assert result.description == "A beautiful sunset"

    def test_minimal_json_only_id(self, tmp_path: Path):
        """JSON with only 'id' field parses with defaults."""
        data = {"id": "999"}
        json_path = tmp_path / "photo_999.json"
        json_path.write_text(json.dumps(data))

        result = parse_photo_json(json_path)

        assert result is not None
        assert result.id == "999"
        assert result.name is None
        assert result.date_taken is None
        assert result.geo is None
        assert result.tags == []
        assert result.albums == []
        assert result.rotation == 0

    def test_missing_id_returns_none(self, tmp_path: Path):
        """JSON without 'id' field returns None."""
        data = {"name": "No ID photo"}
        json_path = tmp_path / "photo_noid.json"
        json_path.write_text(json.dumps(data))

        result = parse_photo_json(json_path)

        assert result is None

    def test_null_id_returns_none(self, tmp_path: Path):
        """JSON with id=null returns None."""
        data = {"id": None, "name": "Null ID"}
        json_path = tmp_path / "photo_null.json"
        json_path.write_text(json.dumps(data))

        result = parse_photo_json(json_path)

        assert result is None

    def test_invalid_json_returns_none(self, tmp_path: Path):
        """Malformed JSON file returns None."""
        json_path = tmp_path / "photo_bad.json"
        json_path.write_text("{ not valid json }")

        result = parse_photo_json(json_path)

        assert result is None

    def test_missing_file_returns_none(self, tmp_path: Path):
        """Non-existent file returns None."""
        json_path = tmp_path / "photo_nonexistent.json"

        result = parse_photo_json(json_path)

        assert result is None

    def test_has_embeddable_data_with_name(self, tmp_path: Path, flickr_json_data: dict):
        """Photo with name has embeddable data."""
        json_path = tmp_path / "photo_123.json"
        json_path.write_text(json.dumps(flickr_json_data))

        result = parse_photo_json(json_path)

        assert result.has_embeddable_data is True

    def test_has_embeddable_data_empty(self, tmp_path: Path):
        """Photo with only id has no embeddable data."""
        data = {"id": "empty"}
        json_path = tmp_path / "photo_empty.json"
        json_path.write_text(json.dumps(data))

        result = parse_photo_json(json_path)

        assert result.has_embeddable_data is False

    def test_extra_fields_ignored(self, tmp_path: Path, flickr_json_data: dict):
        """Unknown fields in JSON are silently ignored by Pydantic."""
        flickr_json_data["groups"] = [{"name": "Group1"}]
        flickr_json_data["comments"] = [{"text": "Nice!"}]
        flickr_json_data["privacy"] = "public"
        json_path = tmp_path / "photo_123.json"
        json_path.write_text(json.dumps(flickr_json_data))

        result = parse_photo_json(json_path)

        assert result is not None
        assert result.id == "28985409503"


class TestParseAllMetadata:
    """Tests for parse_all_metadata()."""

    def test_multiple_files(self, flickr_export_dir: Path):
        """Parse all JSON files from a mock export directory."""
        # AIDEV-NOTE: flickr_export_dir fixture creates photo_111.json, photo_222.json, photo_333.json
        json_paths = {
            "111": flickr_export_dir / "photo_111.json",
            "222": flickr_export_dir / "photo_222.json",
            "333": flickr_export_dir / "photo_333.json",
        }

        result = parse_all_metadata(json_paths)

        assert len(result) == 3
        assert "111" in result
        assert "222" in result
        assert "333" in result
        assert result["111"].name == "Vacation"
        assert result["222"].name == "Beach"

    def test_mixed_valid_invalid(self, flickr_export_dir: Path, tmp_path: Path):
        """Only successfully parsed entries are returned."""
        bad_json = tmp_path / "photo_bad.json"
        bad_json.write_text("not json")

        json_paths = {
            "111": flickr_export_dir / "photo_111.json",
            "bad": bad_json,
        }

        result = parse_all_metadata(json_paths)

        assert len(result) == 1
        assert "111" in result
        assert "bad" not in result

    def test_empty_input(self):
        """Empty dict input returns empty dict."""
        result = parse_all_metadata({})

        assert result == {}
