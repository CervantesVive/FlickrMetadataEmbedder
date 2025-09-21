import pytest
import piexif
from src.gps_converter import (
    decimal_to_dms,
    dms_to_rational,
    get_coordinate_ref,
    flickr_to_exif_gps,
    exif_to_decimal_gps
)


class TestGPSConverter:
    """Test suite for GPS coordinate conversion functions."""

    def test_decimal_to_dms_positive(self):
        """Test conversion of positive decimal coordinates to DMS."""
        # AIDEV-NOTE: Testing San Francisco coordinates (37.7749° N)
        degrees, minutes, seconds = decimal_to_dms(37.7749)

        assert degrees == 37
        assert minutes == 46
        assert abs(seconds - 29.64) < 0.01  # Allow small floating point error

    def test_decimal_to_dms_negative(self):
        """Test conversion of negative decimal coordinates to DMS."""
        # AIDEV-NOTE: Testing San Francisco longitude (-122.4194° W)
        degrees, minutes, seconds = decimal_to_dms(-122.4194)

        # Should return absolute values - direction handled separately
        assert degrees == 122
        assert minutes == 25
        assert abs(seconds - 9.84) < 0.01

    def test_decimal_to_dms_zero(self):
        """Test conversion of zero coordinate."""
        degrees, minutes, seconds = decimal_to_dms(0.0)

        assert degrees == 0
        assert minutes == 0
        assert seconds == 0.0

    def test_decimal_to_dms_small_value(self):
        """Test conversion of small decimal value."""
        degrees, minutes, seconds = decimal_to_dms(0.5)

        assert degrees == 0
        assert minutes == 30
        assert seconds == 0.0

    def test_dms_to_rational_whole_numbers(self):
        """Test conversion of whole DMS values to rational format."""
        rational = dms_to_rational(37, 46, 29.0)

        expected = [(37, 1), (46, 1), (290000, 10000)]
        assert rational == expected

    def test_dms_to_rational_fractional_seconds(self):
        """Test conversion of DMS with fractional seconds."""
        rational = dms_to_rational(122, 25, 9.84)

        expected = [(122, 1), (25, 1), (98400, 10000)]
        assert rational == expected

    def test_get_coordinate_ref_latitude(self):
        """Test latitude coordinate reference determination."""
        assert get_coordinate_ref(37.7749, 'lat') == 'N'
        assert get_coordinate_ref(-33.8688, 'lat') == 'S'
        assert get_coordinate_ref(0.0, 'lat') == 'N'

    def test_get_coordinate_ref_longitude(self):
        """Test longitude coordinate reference determination."""
        assert get_coordinate_ref(-122.4194, 'lon') == 'W'
        assert get_coordinate_ref(151.2093, 'lon') == 'E'
        assert get_coordinate_ref(0.0, 'lon') == 'E'

    def test_get_coordinate_ref_invalid_type(self):
        """Test error handling for invalid coordinate type."""
        with pytest.raises(ValueError):
            get_coordinate_ref(37.7749, 'invalid')

    def test_flickr_to_exif_gps_san_francisco(self):
        """Test conversion of San Francisco coordinates from Flickr to EXIF format."""
        # AIDEV-NOTE: Real San Francisco coordinates from Flickr export
        flickr_geo = {
            "latitude": 37.7749,
            "longitude": -122.4194,
            "accuracy": 16
        }

        exif_gps = flickr_to_exif_gps(flickr_geo)

        # Verify structure
        assert piexif.GPSIFD.GPSLatitude in exif_gps
        assert piexif.GPSIFD.GPSLatitudeRef in exif_gps
        assert piexif.GPSIFD.GPSLongitude in exif_gps
        assert piexif.GPSIFD.GPSLongitudeRef in exif_gps

        # Verify references
        assert exif_gps[piexif.GPSIFD.GPSLatitudeRef] == 'N'
        assert exif_gps[piexif.GPSIFD.GPSLongitudeRef] == 'W'

        # Verify latitude format
        lat_rational = exif_gps[piexif.GPSIFD.GPSLatitude]
        assert len(lat_rational) == 3
        assert lat_rational[0] == (37, 1)  # degrees
        assert lat_rational[1] == (46, 1)  # minutes
        # Seconds should be close to 29.64
        assert abs(lat_rational[2][0] / lat_rational[2][1] - 29.64) < 0.01

    def test_flickr_to_exif_gps_sydney(self):
        """Test conversion of Sydney coordinates."""
        # AIDEV-NOTE: Testing southern hemisphere coordinates
        flickr_geo = {
            "latitude": -33.8688,
            "longitude": 151.2093
        }

        exif_gps = flickr_to_exif_gps(flickr_geo)

        assert exif_gps[piexif.GPSIFD.GPSLatitudeRef] == 'S'
        assert exif_gps[piexif.GPSIFD.GPSLongitudeRef] == 'E'

    def test_flickr_to_exif_gps_equator_prime_meridian(self):
        """Test conversion of coordinates at equator and prime meridian."""
        flickr_geo = {
            "latitude": 0.0,
            "longitude": 0.0
        }

        exif_gps = flickr_to_exif_gps(flickr_geo)

        assert exif_gps[piexif.GPSIFD.GPSLatitudeRef] == 'N'
        assert exif_gps[piexif.GPSIFD.GPSLongitudeRef] == 'E'

        # Should have zero coordinates
        assert exif_gps[piexif.GPSIFD.GPSLatitude] == [(0, 1), (0, 1), (0, 10000)]
        assert exif_gps[piexif.GPSIFD.GPSLongitude] == [(0, 1), (0, 1), (0, 10000)]

    def test_flickr_to_exif_gps_missing_data(self):
        """Test handling of missing GPS data."""
        test_cases = [
            None,
            {},
            {"latitude": 37.7749},  # Missing longitude
            {"longitude": -122.4194},  # Missing latitude
            {"latitude": None, "longitude": -122.4194},
            {"latitude": "invalid", "longitude": -122.4194},
        ]

        for flickr_geo in test_cases:
            result = flickr_to_exif_gps(flickr_geo)
            assert result is None

    def test_flickr_to_exif_gps_extreme_coordinates(self):
        """Test conversion of extreme coordinate values."""
        # North Pole
        flickr_geo = {"latitude": 90.0, "longitude": 0.0}
        exif_gps = flickr_to_exif_gps(flickr_geo)
        assert exif_gps[piexif.GPSIFD.GPSLatitude] == [(90, 1), (0, 1), (0, 10000)]

        # South Pole
        flickr_geo = {"latitude": -90.0, "longitude": 0.0}
        exif_gps = flickr_to_exif_gps(flickr_geo)
        assert exif_gps[piexif.GPSIFD.GPSLatitudeRef] == 'S'
        assert exif_gps[piexif.GPSIFD.GPSLatitude] == [(90, 1), (0, 1), (0, 10000)]

        # International Date Line
        flickr_geo = {"latitude": 0.0, "longitude": 180.0}
        exif_gps = flickr_to_exif_gps(flickr_geo)
        assert exif_gps[piexif.GPSIFD.GPSLongitude] == [(180, 1), (0, 1), (0, 10000)]

        flickr_geo = {"latitude": 0.0, "longitude": -180.0}
        exif_gps = flickr_to_exif_gps(flickr_geo)
        assert exif_gps[piexif.GPSIFD.GPSLongitudeRef] == 'W'

    def test_exif_to_decimal_gps_san_francisco(self):
        """Test reverse conversion from EXIF to decimal coordinates."""
        # AIDEV-NOTE: Testing round-trip conversion accuracy
        original_flickr = {"latitude": 37.7749, "longitude": -122.4194}

        # Convert to EXIF
        exif_gps = flickr_to_exif_gps(original_flickr)

        # Convert back to decimal
        lat_decimal, lon_decimal = exif_to_decimal_gps(exif_gps)

        # Should be very close to original (within precision limits)
        assert abs(lat_decimal - 37.7749) < 0.0001
        assert abs(lon_decimal - (-122.4194)) < 0.0001

    def test_exif_to_decimal_gps_missing_data(self):
        """Test handling of incomplete EXIF GPS data."""
        test_cases = [
            {},  # Empty GPS data
            {piexif.GPSIFD.GPSLatitude: [(37, 1), (46, 1), (296400, 10000)]},  # Missing longitude
            {piexif.GPSIFD.GPSLongitude: [(122, 1), (25, 1), (98400, 10000)]},  # Missing latitude
        ]

        for exif_gps in test_cases:
            lat, lon = exif_to_decimal_gps(exif_gps)
            assert lat is None
            assert lon is None

    def test_exif_to_decimal_gps_malformed_data(self):
        """Test handling of malformed EXIF GPS data."""
        malformed_cases = [
            {piexif.GPSIFD.GPSLatitude: "invalid"},  # Wrong format
            {piexif.GPSIFD.GPSLatitude: [(37, 0), (46, 1), (296400, 10000)]},  # Division by zero
        ]

        for exif_gps in malformed_cases:
            lat, lon = exif_to_decimal_gps(exif_gps)
            assert lat is None
            assert lon is None

    def test_round_trip_precision(self):
        """Test precision preservation in round-trip conversions."""
        # AIDEV-NOTE: Test various coordinate precisions
        test_coordinates = [
            (37.7749, -122.4194),      # San Francisco
            (40.7128, -74.0060),       # New York
            (51.5074, -0.1278),        # London
            (-33.8688, 151.2093),      # Sydney
            (35.6762, 139.6503),       # Tokyo
        ]

        for original_lat, original_lon in test_coordinates:
            flickr_geo = {"latitude": original_lat, "longitude": original_lon}

            # Convert to EXIF and back
            exif_gps = flickr_to_exif_gps(flickr_geo)
            converted_lat, converted_lon = exif_to_decimal_gps(exif_gps)

            # Precision should be within 0.0001 degrees (~11 meters at equator)
            assert abs(converted_lat - original_lat) < 0.0001
            assert abs(converted_lon - original_lon) < 0.0001

    def test_flickr_additional_fields(self):
        """Test handling of additional Flickr GPS fields."""
        # AIDEV-NOTE: Flickr exports may include additional GPS metadata
        flickr_geo = {
            "latitude": 37.7749,
            "longitude": -122.4194,
            "accuracy": 16,
            "context": "0",
            "place_id": "WoePlanetaryId",
            "woeid": "2459115",
            "geo_is_public": 1,
            "geo_is_contact": 0,
            "geo_is_friend": 0,
            "geo_is_family": 0
        }

        exif_gps = flickr_to_exif_gps(flickr_geo)

        # Should still process successfully and include core GPS data
        assert exif_gps is not None
        assert piexif.GPSIFD.GPSLatitude in exif_gps
        assert piexif.GPSIFD.GPSLongitude in exif_gps

        # Additional fields don't interfere with conversion
        lat, lon = exif_to_decimal_gps(exif_gps)
        assert abs(lat - 37.7749) < 0.0001
        assert abs(lon - (-122.4194)) < 0.0001