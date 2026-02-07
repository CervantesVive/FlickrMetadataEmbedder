"""Tests for GPS coordinate conversion functions.

Tests decimal_to_dms(), dms_to_rational_string(), and get_coordinate_ref().
"""

from __future__ import annotations

import pytest

from src.gps_converter import (
    decimal_to_dms,
    dms_to_rational_string,
    get_coordinate_ref,
)


class TestDecimalToDms:
    """Tests for decimal_to_dms()."""

    def test_positive_coordinate(self):
        """Convert positive decimal (San Francisco latitude) to DMS."""
        degrees, minutes, seconds = decimal_to_dms(37.7749)

        assert degrees == 37
        assert minutes == 46
        assert abs(seconds - 29.64) < 0.01

    def test_negative_coordinate(self):
        """Convert negative decimal (San Francisco longitude) to DMS."""
        degrees, minutes, seconds = decimal_to_dms(-122.4194)

        # Returns absolute values — direction handled by get_coordinate_ref()
        assert degrees == 122
        assert minutes == 25
        assert abs(seconds - 9.84) < 0.01

    def test_zero(self):
        """Convert zero coordinate."""
        degrees, minutes, seconds = decimal_to_dms(0.0)

        assert degrees == 0
        assert minutes == 0
        assert seconds == 0.0

    def test_small_value(self):
        """Convert small decimal value (0.5 degrees = 30 minutes)."""
        degrees, minutes, seconds = decimal_to_dms(0.5)

        assert degrees == 0
        assert minutes == 30
        assert seconds == 0.0


class TestDmsToRationalString:
    """Tests for dms_to_rational_string()."""

    def test_whole_numbers(self):
        """Convert whole DMS values to rational string."""
        result = dms_to_rational_string(37, 46, 29.0)

        assert result == "37/1 46/1 290000/10000"

    def test_fractional_seconds(self):
        """Convert DMS with fractional seconds."""
        result = dms_to_rational_string(122, 25, 9.84)

        assert result == "122/1 25/1 98400/10000"

    def test_zero_coordinate(self):
        """Convert all-zero DMS to rational string."""
        result = dms_to_rational_string(0, 0, 0.0)

        assert result == "0/1 0/1 0/10000"

    def test_extreme_latitude(self):
        """Convert 90 degrees (pole) to rational string."""
        result = dms_to_rational_string(90, 0, 0.0)

        assert result == "90/1 0/1 0/10000"

    def test_roundtrip_precision(self):
        """Verify decimal → DMS → rational string preserves precision."""
        # San Francisco: 37.7749° N
        deg, min_, sec = decimal_to_dms(37.7749)
        result = dms_to_rational_string(deg, min_, sec)

        # Parse back to verify
        parts = result.split(" ")
        d = int(parts[0].split("/")[0])
        m = int(parts[1].split("/")[0])
        s_num, s_den = int(parts[2].split("/")[0]), int(parts[2].split("/")[1])
        decimal_back = d + m / 60 + (s_num / s_den) / 3600

        assert abs(decimal_back - 37.7749) < 0.0001


class TestGetCoordinateRef:
    """Tests for get_coordinate_ref()."""

    def test_latitude_positive_negative(self):
        """Positive latitude → N, negative → S."""
        assert get_coordinate_ref(37.7749, 'lat') == 'N'
        assert get_coordinate_ref(-33.8688, 'lat') == 'S'
        assert get_coordinate_ref(0.0, 'lat') == 'N'

    def test_longitude_positive_negative(self):
        """Negative longitude → W, positive → E."""
        assert get_coordinate_ref(-122.4194, 'lon') == 'W'
        assert get_coordinate_ref(151.2093, 'lon') == 'E'
        assert get_coordinate_ref(0.0, 'lon') == 'E'

    def test_invalid_coord_type(self):
        """Invalid coord_type raises ValueError."""
        with pytest.raises(ValueError):
            get_coordinate_ref(37.7749, 'invalid')
