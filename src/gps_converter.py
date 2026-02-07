"""GPS coordinate conversion for EXIF metadata.

Provides decimal → DMS → rational string conversion for pyexiv2 GPS tags.
"""

from __future__ import annotations


def decimal_to_dms(decimal_coord):
    """Convert decimal coordinate to degrees, minutes, seconds.

    Args:
        decimal_coord (float): Decimal coordinate (e.g., 37.7749)

    Returns:
        tuple: (degrees, minutes, seconds) as (int, int, float)
    """
    # EXIF requires absolute values - direction stored separately
    abs_coord = abs(decimal_coord)
    degrees = int(abs_coord)
    minutes_float = (abs_coord - degrees) * 60
    minutes = int(minutes_float)
    seconds = (minutes_float - minutes) * 60

    return degrees, minutes, seconds


def dms_to_rational_string(degrees: int, minutes: int, seconds: float) -> str:
    """Convert DMS to pyexiv2-compatible rational string.

    pyexiv2 expects GPS coordinates as: "deg/1 min/1 sec_num/sec_den"
    Example: "37/1 46/1 29640/10000"

    Args:
        degrees: Degrees component (non-negative int).
        minutes: Minutes component (non-negative int).
        seconds: Seconds component with fractional precision.

    Returns:
        Rational string for pyexiv2 GPS tags.
    """
    # AIDEV-NOTE: 10000 denominator gives ~0.001 arcsecond precision (~3cm at equator)
    sec_num = int(seconds * 10000)
    return f"{degrees}/1 {minutes}/1 {sec_num}/10000"


def get_coordinate_ref(decimal_coord, coord_type):
    """Get EXIF coordinate reference (N/S for lat, E/W for lon).

    Args:
        decimal_coord (float): Decimal coordinate
        coord_type (str): 'lat' for latitude, 'lon' for longitude

    Returns:
        str: Reference character ('N', 'S', 'E', or 'W')
    """
    if coord_type == 'lat':
        return 'N' if decimal_coord >= 0 else 'S'
    elif coord_type == 'lon':
        return 'E' if decimal_coord >= 0 else 'W'
    else:
        raise ValueError("coord_type must be 'lat' or 'lon'")
