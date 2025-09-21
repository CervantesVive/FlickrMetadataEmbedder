import os
import tempfile
import pytest
from unittest.mock import Mock, patch
import piexif
from src.image_updater import embed_metadata


class TestImageUpdater:
    """Test suite for EXIF metadata embedding functionality."""

    def test_embed_metadata_successful(self):
        """Test successful metadata embedding into images."""
        # AIDEV-NOTE: Testing a standard Flickr image naming pattern with photo ID
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_logger = Mock()

            # Create mock metadata
            metadata = {
                "12345678": {
                    "date_taken": "2023-05-15 14:30:00",
                    "geolocation": {"latitude": 37.7749, "longitude": -122.4194}
                },
                "87654321": {
                    "date_taken": "2023-06-01 09:15:30",
                    "geolocation": None
                }
            }

            # Create test image files matching Flickr naming
            image1 = os.path.join(tmpdir, "12345678_original.jpg")
            image2 = os.path.join(tmpdir, "87654321_medium.jpg")
            open(image1, 'a').close()
            open(image2, 'a').close()

            output_dir = os.path.join(tmpdir, "output")
            os.makedirs(output_dir)

            # Mock piexif functions
            with patch('piexif.load') as mock_load, \
                 patch('piexif.dump') as mock_dump, \
                 patch('piexif.insert') as mock_insert:

                mock_load.return_value = {"Exif": {}, "GPS": {}}
                mock_dump.return_value = b"exif_data"

                embed_metadata(tmpdir, output_dir, metadata, False, mock_logger)

                # Verify piexif was called for both images
                assert mock_load.call_count == 2
                assert mock_dump.call_count == 2
                assert mock_insert.call_count == 2

                # Verify logger's recorded success
                log_calls = mock_logger.log.call_args_list
                assert any("[INFO]" in str(call) and "12345678_original.jpg" in str(call) for call in log_calls)
                assert any("[INFO]" in str(call) and "87654321_medium.jpg" in str(call) for call in log_calls)

    def test_embed_metadata_with_overwrite(self):
        """Test that overwrite mode updates files in-place."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_logger = Mock()

            metadata = {
                "99999": {
                    "date_taken": "2023-07-04 16:00:00",
                    "geolocation": None
                }
            }

            # Create a test image
            image_path = os.path.join(tmpdir, "99999_original.jpg")
            open(image_path, 'a').close()

            with patch('piexif.load') as mock_load, \
                 patch('piexif.dump') as mock_dump, \
                 patch('piexif.insert') as mock_insert:

                mock_load.return_value = {"Exif": {}, "GPS": {}}
                mock_dump.return_value = b"exif_data"

                # Test with overwrite=True
                embed_metadata(tmpdir, "/unused/output", metadata, True, mock_logger)

                # Should update the original file, not output dir
                mock_insert.assert_called_once()
                insert_call = mock_insert.call_args[0]
                assert insert_call[1] == image_path  # Should write to the original location

    def test_embed_metadata_without_overwrite(self):
        """Test that non-overwrite mode saves it to the output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_logger = Mock()

            metadata = {
                "88888": {
                    "date_taken": "2023-08-15 10:00:00",
                    "geolocation": None
                }
            }

            # Create a test image
            image_name = "88888_large.jpg"
            image_path = os.path.join(tmpdir, image_name)
            open(image_path, 'a').close()

            output_dir = os.path.join(tmpdir, "output")
            os.makedirs(output_dir)

            with patch('piexif.load') as mock_load, \
                 patch('piexif.dump') as mock_dump, \
                 patch('piexif.insert') as mock_insert:

                mock_load.return_value = {"Exif": {}, "GPS": {}}
                mock_dump.return_value = b"exif_data"

                # Test with overwrite=False
                embed_metadata(tmpdir, output_dir, metadata, False, mock_logger)

                # Should save to the output directory
                mock_insert.assert_called_once()
                insert_call = mock_insert.call_args[0]
                expected_output = os.path.join(output_dir, image_name)
                assert insert_call[1] == expected_output

    def test_embed_metadata_nested_directories(self):
        """Test processing images in a nested directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_logger = Mock()

            metadata = {
                "111": {"date_taken": "2023-01-01 12:00:00", "geolocation": None},
                "222": {"date_taken": "2023-02-02 12:00:00", "geolocation": None},
            }

            # Create nested structure like Flickr export
            subdir1 = os.path.join(tmpdir, "data-download-1")
            subdir2 = os.path.join(tmpdir, "data-download-2", "albums")
            os.makedirs(subdir1)
            os.makedirs(subdir2)

            # Create images in different subdirectories
            image1 = os.path.join(subdir1, "111_original.jpg")
            image2 = os.path.join(subdir2, "222_square.jpg")
            open(image1, 'a').close()
            open(image2, 'a').close()

            output_dir = os.path.join(tmpdir, "output")
            os.makedirs(output_dir)

            with patch('piexif.load') as mock_load, \
                 patch('piexif.dump') as mock_dump, \
                 patch('piexif.insert') as mock_insert:

                mock_load.return_value = {"Exif": {}, "GPS": {}}
                mock_dump.return_value = b"exif_data"

                embed_metadata(tmpdir, output_dir, metadata, False, mock_logger)

                # Should process both images from nested directories
                assert mock_insert.call_count == 2

    def test_embed_metadata_date_taken_only(self):
        """Test embedding when only date_taken is available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_logger = Mock()

            metadata = {
                "77777": {
                    "date_taken": "2023-09-20 15:45:00",
                    "geolocation": None  # No GPS data
                }
            }

            image_path = os.path.join(tmpdir, "77777_original.jpg")
            open(image_path, 'a').close()

            with patch('piexif.load') as mock_load, \
                 patch('piexif.dump') as mock_dump:

                exif_dict = {"Exif": {}, "GPS": {}}
                mock_load.return_value = exif_dict

                embed_metadata(tmpdir, tmpdir, metadata, True, mock_logger)

                # Verify DateTimeOriginal was set
                mock_dump.assert_called_once()
                dump_call_dict = mock_dump.call_args[0][0]
                assert piexif.ExifIFD.DateTimeOriginal in dump_call_dict["Exif"]

    def test_embed_metadata_geolocation_only(self):
        """Test embedding when only geolocation is available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_logger = Mock()

            metadata = {
                "66666": {
                    "date_taken": None,  # No date
                    "geolocation": {"latitude": 40.7128, "longitude": -74.0060}
                }
            }

            image_path = os.path.join(tmpdir, "66666_original.jpg")
            open(image_path, 'a').close()

            with patch('piexif.load') as mock_load, \
                 patch('piexif.dump') as mock_dump:

                exif_dict = {"Exif": {}, "GPS": {}}
                mock_load.return_value = exif_dict

                embed_metadata(tmpdir, tmpdir, metadata, True, mock_logger)

                # Verify GPS data was set
                mock_dump.assert_called_once()
                dump_call_dict = mock_dump.call_args[0][0]
                assert dump_call_dict["GPS"] == metadata["66666"]["geolocation"]

    def test_embed_metadata_exception_handling(self):
        """Test error handling when piexif operations fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_logger = Mock()

            metadata = {
                "55555": {
                    "date_taken": "2023-10-01 08:00:00",
                    "geolocation": None
                }
            }

            image_path = os.path.join(tmpdir, "55555_original.jpg")
            open(image_path, 'a').close()

            with patch('piexif.load') as mock_load:
                # Simulate piexif.load failure
                mock_load.side_effect = Exception("Invalid EXIF data")

                embed_metadata(tmpdir, tmpdir, metadata, True, mock_logger)

                # Verify error was logged
                log_calls = mock_logger.log.call_args_list
                assert any("[ERROR]" in str(call) and "55555_original.jpg" in str(call) for call in log_calls)
                assert any("Invalid EXIF data" in str(call) for call in log_calls)

    def test_embed_metadata_no_matching_images(self):
        """Test behavior when no images match metadata IDs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_logger = Mock()

            metadata = {
                "no_match_1": {"date_taken": "2023-01-01", "geolocation": None},
                "no_match_2": {"date_taken": "2023-02-02", "geolocation": None},
            }

            # Create images with different IDs
            wrong_image = os.path.join(tmpdir, "different_id.jpg")
            open(wrong_image, 'a').close()

            with patch('piexif.load') as mock_load, \
                 patch('piexif.insert') as mock_insert:

                embed_metadata(tmpdir, tmpdir, metadata, True, mock_logger)

                # Should not process any images
                mock_load.assert_not_called()
                mock_insert.assert_not_called()

    def test_embed_metadata_multiple_id_matches(self):
        """Test handling images with multiple photo ID matches in filename."""
        # AIDEV-NOTE: Edge case where the filename contains multiple photo IDs
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_logger = Mock()

            metadata = {
                "123": {"date_taken": "2023-01-01", "geolocation": None},
                "456": {"date_taken": "2023-02-02", "geolocation": None},
            }

            # Image name contains both IDs
            tricky_image = os.path.join(tmpdir, "123_and_456.jpg")
            open(tricky_image, 'a').close()

            with patch('piexif.load') as mock_load, \
                 patch('piexif.dump') as mock_dump, \
                 patch('piexif.insert') as mock_insert:

                mock_load.return_value = {"Exif": {}, "GPS": {}}
                mock_dump.return_value = b"exif_data"

                embed_metadata(tmpdir, tmpdir, metadata, True, mock_logger)

                # Should process the image (picks first matching ID)
                assert mock_insert.call_count == 1

    def test_embed_metadata_empty_metadata(self):
        """Test behavior with an empty metadata dictionary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_logger = Mock()

            # Empty metadata
            metadata = {}

            # Create a test image
            image_path = os.path.join(tmpdir, "some_image.jpg")
            open(image_path, 'a').close()

            with patch('piexif.load') as mock_load, \
                 patch('piexif.insert') as mock_insert:

                embed_metadata(tmpdir, tmpdir, metadata, True, mock_logger)

                # Should not process any images
                mock_load.assert_not_called()
                mock_insert.assert_not_called()

    def test_embed_metadata_various_flickr_sizes(self):
        """Test matching various Flickr image size suffixes."""
        # AIDEV-NOTE: Flickr uses suffixes like _o, _b, _c, _z, _m, _n, _s, _t, _q
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_logger = Mock()

            metadata = {
                "999888": {"date_taken": "2023-11-11 11:11:11", "geolocation": None}
            }

            # Create images with various Flickr size suffixes
            flickr_sizes = ["_o.jpg", "_b.jpg", "_c.jpg", "_z.jpg", "_m.jpg",
                          "_n.jpg", "_s.jpg", "_t.jpg", "_q.jpg", "_k.jpg"]

            for suffix in flickr_sizes:
                image_path = os.path.join(tmpdir, f"999888{suffix}")
                open(image_path, 'a').close()

            with patch('piexif.load') as mock_load, \
                 patch('piexif.dump') as mock_dump, \
                 patch('piexif.insert') as mock_insert:

                mock_load.return_value = {"Exif": {}, "GPS": {}}
                mock_dump.return_value = b"exif_data"

                embed_metadata(tmpdir, tmpdir, metadata, True, mock_logger)

                # Should process all image variants
                assert mock_insert.call_count == len(flickr_sizes)

    @patch('os.walk')
    def test_embed_metadata_permission_error(self, mock_walk):
        """Test handling when directory traversal fails."""
        mock_logger = Mock()
        mock_walk.side_effect = PermissionError("Access denied")

        metadata = {"test": {"date_taken": "2023-01-01", "geolocation": None}}

        # Should raise the permission error
        with pytest.raises(PermissionError):
            embed_metadata("/restricted/path", "/output", metadata, False, mock_logger)