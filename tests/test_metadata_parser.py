import json
import os
import tempfile
import pytest
from unittest.mock import Mock, patch, mock_open
from src.metadata_parser import extract_metadata


class TestMetadataParser:
    """Test suite for metadata extraction from Flickr JSON exports."""

    def test_extract_metadata_valid_files(self):
        """Test extraction from valid Flickr metadata JSON files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create mock logger
            mock_logger = Mock()

            # Create test metadata files
            metadata1 = {
                "id": "12345678",
                "date_taken": "2023-05-15 14:30:00",
                "geolocation": {
                    "latitude": 37.7749,
                    "longitude": -122.4194,
                    "accuracy": 10
                }
            }

            metadata2 = {
                "id": "87654321",
                "date_taken": "2023-06-01 09:15:30",
                "geolocation": None
            }

            # Write test files
            file1_path = os.path.join(tmpdir, "photo_12345678_abc123.json")
            file2_path = os.path.join(tmpdir, "photo_87654321_def456.json")

            with open(file1_path, "w") as f:
                json.dump(metadata1, f)

            with open(file2_path, "w") as f:
                json.dump(metadata2, f)

            # Extract metadata
            result = extract_metadata(tmpdir, mock_logger)

            # Verify results
            assert len(result) == 2
            assert "12345678" in result
            assert "87654321" in result
            assert result["12345678"]["date_taken"] == "2023-05-15 14:30:00"
            assert result["12345678"]["geolocation"]["latitude"] == 37.7749
            assert result["87654321"]["date_taken"] == "2023-06-01 09:15:30"
            assert result["87654321"]["geolocation"] is None

            # Verify no errors were logged
            mock_logger.log.assert_not_called()

    def test_extract_metadata_nested_directories(self):
        """Test extraction from the nested directory structure (data-download-* pattern)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_logger = Mock()

            # Create nested Flickr export structure
            subdir1 = os.path.join(tmpdir, "data-download-1")
            subdir2 = os.path.join(tmpdir, "data-download-2")
            nested = os.path.join(subdir1, "albums", "vacation")

            os.makedirs(subdir1)
            os.makedirs(subdir2)
            os.makedirs(nested)

            # Create metadata files in different locations
            metadata_locations = [
                (subdir1, "photo_111_aaa.json", {"id": "111", "date_taken": "2023-01-01", "geolocation": None}),
                (subdir2, "photo_222_bbb.json", {"id": "222", "date_taken": "2023-02-02", "geolocation": None}),
                (nested, "photo_333_ccc.json", {"id": "333", "date_taken": "2023-03-03", "geolocation": None}),
            ]

            for dir_path, filename, data in metadata_locations:
                with open(os.path.join(dir_path, filename), "w") as f:
                    json.dump(data, f)

            result = extract_metadata(tmpdir, mock_logger)

            # Should find all three files
            assert len(result) == 3
            assert "111" in result
            assert "222" in result
            assert "333" in result

    def test_extract_metadata_invalid_json(self):
        """Test handling of malformed JSON files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_logger = Mock()

            # Create an invalid JSON file
            invalid_file = os.path.join(tmpdir, "photo_invalid_xyz.json")
            with open(invalid_file, "w") as f:
                f.write("{invalid json content")

            # Create one valid file
            valid_file = os.path.join(tmpdir, "photo_valid_123.json")
            with open(valid_file, "w") as f:
                json.dump({"id": "valid123", "date_taken": "2023-01-01", "geolocation": None}, f)

            result = extract_metadata(tmpdir, mock_logger)

            # Should process valid file and log error for invalid
            assert len(result) == 1
            assert "valid123" in result

            # Verify error was logged
            mock_logger.log.assert_called_once()
            log_call = mock_logger.log.call_args[0][0]
            assert "[ERROR]" in log_call
            assert "photo_invalid_xyz.json" in log_call

    def test_extract_metadata_missing_id(self):
        """Test handling of JSON files without the 'id' field."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_logger = Mock()

            # Create a file without ID
            no_id_file = os.path.join(tmpdir, "photo_noid_abc.json")
            with open(no_id_file, "w") as f:
                json.dump({"date_taken": "2023-01-01", "geolocation": None}, f)

            # Create a file with ID
            with_id_file = os.path.join(tmpdir, "photo_withid_def.json")
            with open(with_id_file, "w") as f:
                json.dump({"id": "12345", "date_taken": "2023-01-01", "geolocation": None}, f)

            result = extract_metadata(tmpdir, mock_logger)

            # Should only include a file with ID
            assert len(result) == 1
            assert "12345" in result
            assert "noid" not in result

    def test_extract_metadata_ignores_non_photo_json(self):
        """Test that only photo_*.json files are processed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_logger = Mock()

            # Create various JSON files
            files_to_create = [
                ("photo_123_abc.json", {"id": "123", "date_taken": "2023-01-01", "geolocation": None}, True),  # Should process
                ("album_456.json", {"id": "456", "date_taken": "2023-01-01", "geolocation": None}, False),  # Should ignore
                ("metadata.json", {"id": "789", "date_taken": "2023-01-01", "geolocation": None}, False),  # Should ignore
                ("photo_data.txt", "not json", False),  # Should ignore
                ("photo_999_xyz.json", {"id": "999", "date_taken": "2023-01-01", "geolocation": None}, True),  # Should process
            ]

            for filename, content, _ in files_to_create:
                filepath = os.path.join(tmpdir, filename)
                if filename.endswith(".json") and isinstance(content, dict):
                    with open(filepath, "w") as f:
                        json.dump(content, f)
                else:
                    with open(filepath, "w") as f:
                        f.write(content)

            result = extract_metadata(tmpdir, mock_logger)

            # Should only process photo_*.json files
            assert len(result) == 2
            assert "123" in result
            assert "999" in result
            assert "456" not in result
            assert "789" not in result

    def test_extract_metadata_empty_directory(self):
        """Test extraction from empty directory returns empty dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_logger = Mock()

            result = extract_metadata(tmpdir, mock_logger)

            assert result == {}
            mock_logger.log.assert_not_called()

    def test_extract_metadata_complex_geolocation(self):
        """Test extraction of complex geolocation data from Flickr export."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_logger = Mock()

            complex_metadata = {
                "id": "geo123",
                "date_taken": "2023-07-04 16:20:00",
                "geolocation": {
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "accuracy": 16,
                    "context": "0",
                    "place_id": "WoePlanetaryId",
                    "woeid": "2459115",
                    "geo_is_public": 1,
                    "geo_is_contact": 0,
                    "geo_is_friend": 0,
                    "geo_is_family": 0
                }
            }

            file_path = os.path.join(tmpdir, "photo_geo123_test.json")
            with open(file_path, "w") as f:
                json.dump(complex_metadata, f)

            result = extract_metadata(tmpdir, mock_logger)

            assert "geo123" in result
            assert result["geo123"]["geolocation"]["latitude"] == 40.7128
            assert result["geo123"]["geolocation"]["longitude"] == -74.0060
            assert result["geo123"]["geolocation"]["accuracy"] == 16
            assert result["geo123"]["geolocation"]["woeid"] == "2459115"

    def test_extract_metadata_numeric_id_conversion(self):
        """Test that numeric IDs are converted to strings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_logger = Mock()

            # Create file with numeric ID
            numeric_metadata = {
                "id": 99887766,  # Numeric ID
                "date_taken": "2023-08-15 10:00:00",
                "geolocation": None
            }

            file_path = os.path.join(tmpdir, "photo_99887766_num.json")
            with open(file_path, "w") as f:
                json.dump(numeric_metadata, f)

            result = extract_metadata(tmpdir, mock_logger)

            # ID should be string in a result
            assert "99887766" in result
            assert isinstance(list(result.keys())[0], str)

    def test_extract_metadata_partial_data(self):
        """Test extraction when some fields are missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_logger = Mock()

            # Various partial metadata scenarios
            scenarios = [
                {"id": "partial1", "date_taken": "2023-01-01"},  # No geolocation
                {"id": "partial2", "geolocation": {"latitude": 50.0, "longitude": 0.0}},  # No date_taken
                {"id": "partial3"},  # Only ID
            ]

            for i, metadata in enumerate(scenarios):
                file_path = os.path.join(tmpdir, f"photo_partial{i}_test.json")
                with open(file_path, "w") as f:
                    json.dump(metadata, f)

            result = extract_metadata(tmpdir, mock_logger)

            # All files should be processed
            assert len(result) == 3

            # Check partial1
            assert result["partial1"]["date_taken"] == "2023-01-01"
            assert result["partial1"]["geolocation"] is None

            # Check partial2
            assert result["partial2"]["date_taken"] is None
            assert result["partial2"]["geolocation"]["latitude"] == 50.0

            # Check partial3
            assert result["partial3"]["date_taken"] is None
            assert result["partial3"]["geolocation"] is None

    @patch("os.walk")
    def test_extract_metadata_permission_error(self, mock_walk):
        """Test handling when directory traversal fails."""
        mock_logger = Mock()
        mock_walk.side_effect = PermissionError("Access denied")

        # Should raise the permission error (not caught by the function)
        with pytest.raises(PermissionError):
            extract_metadata("/restricted/path", mock_logger)

    def test_extract_metadata_various_date_formats(self):
        """Test handling of different Flickr date formats across export versions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_logger = Mock()

            date_formats = [
                ("format1", "2023-05-15 14:30:00"),  # Standard format
                ("format2", "2023-05-15T14:30:00Z"),  # ISO format
                ("format3", "1684163400"),  # Unix timestamp
                ("format4", "May 15, 2023"),  # Human-readable
            ]

            for photo_id, date_format in date_formats:
                metadata = {
                    "id": photo_id,
                    "date_taken": date_format,
                    "geolocation": None
                }
                file_path = os.path.join(tmpdir, f"photo_{photo_id}_test.json")
                with open(file_path, "w") as f:
                    json.dump(metadata, f)

            result = extract_metadata(tmpdir, mock_logger)

            # Should extract all dates as-is (formatting handled by image_updater)
            assert len(result) == 4
            for photo_id, date_format in date_formats:
                assert result[photo_id]["date_taken"] == date_format