import piexif


def decimal_to_dms(decimal_coord):
    """
    Convert decimal coordinate to degrees, minutes, seconds.

    Args:
        decimal_coord (float): Decimal coordinate (e.g., 37.7749)

    Returns:
        tuple: (degrees, minutes, seconds) as floats
    """
    # AIDEV-NOTE: EXIF requires absolute values - direction stored separately
    abs_coord = abs(decimal_coord)
    degrees = int(abs_coord)
    minutes_float = (abs_coord - degrees) * 60
    minutes = int(minutes_float)
    seconds = (minutes_float - minutes) * 60

    return degrees, minutes, seconds


def dms_to_rational(degrees, minutes, seconds):
    """
    Convert DMS to piexif-compatible rational format.

    EXIF stores coordinates as three rational numbers (numerator/denominator pairs).
    Uses precision of 10000 for seconds to preserve fractional precision.

    Args:
        degrees (int): Degrees component
        minutes (int): Minutes component
        seconds (float): Seconds component with fractional precision

    Returns:
        list: Three tuples [(deg_num, deg_den), (min_num, min_den), (sec_num, sec_den)]
    """
    return [
        (degrees, 1),                    # degrees as whole number
        (minutes, 1),                    # minutes as whole number
        (int(seconds * 10000), 10000)    # seconds with 4 decimal precision
    ]


def get_coordinate_ref(decimal_coord, coord_type):
    """
    Get EXIF coordinate reference (N/S for lat, E/W for lon).

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


def flickr_to_exif_gps(flickr_geolocation):
    """
    Convert Flickr JSON geolocation to EXIF GPS format for piexif.

    Flickr exports GPS data as decimal degrees in JSON. EXIF requires
    degrees/minutes/seconds as rational numbers with separate direction refs.

    Args:
        flickr_geolocation (dict): Flickr GPS data with 'latitude' and 'longitude' keys

    Returns:
        dict: EXIF GPS IFD data ready for piexif insertion, or None if invalid data

    Example:
        flickr_geo = {"latitude": 37.7749, "longitude": -122.4194}
        exif_gps = flickr_to_exif_gps(flickr_geo)
        # Returns GPS IFD dict with proper rational format
    """
    if not flickr_geolocation or 'latitude' not in flickr_geolocation or 'longitude' not in flickr_geolocation:
        return None

    try:
        lat = float(flickr_geolocation['latitude'])
        lon = float(flickr_geolocation['longitude'])
    except (ValueError, TypeError):
        return None

    # Convert to DMS
    lat_deg, lat_min, lat_sec = decimal_to_dms(lat)
    lon_deg, lon_min, lon_sec = decimal_to_dms(lon)

    # Convert to rational format
    lat_rational = dms_to_rational(lat_deg, lat_min, lat_sec)
    lon_rational = dms_to_rational(lon_deg, lon_min, lon_sec)

    # Get direction references
    lat_ref = get_coordinate_ref(lat, 'lat')
    lon_ref = get_coordinate_ref(lon, 'lon')

    # AIDEV-NOTE: Only set required GPS fields - avoid overwriting other GPS data
    gps_data = {
        piexif.GPSIFD.GPSLatitude: lat_rational,
        piexif.GPSIFD.GPSLatitudeRef: lat_ref,
        piexif.GPSIFD.GPSLongitude: lon_rational,
        piexif.GPSIFD.GPSLongitudeRef: lon_ref,
    }

    # Include additional Flickr GPS metadata if available
    if 'accuracy' in flickr_geolocation:
        # GPS accuracy in meters - no direct EXIF equivalent but preserve if needed
        pass

    return gps_data


def exif_to_decimal_gps(exif_gps):
    """
    Convert EXIF GPS data back to decimal coordinates for validation/testing.

    Args:
        exif_gps (dict): EXIF GPS IFD data from piexif

    Returns:
        tuple: (latitude, longitude) as decimal degrees, or (None, None) if invalid
    """
    try:
        # Extract latitude
        lat_rational = exif_gps.get(piexif.GPSIFD.GPSLatitude)
        lat_ref = exif_gps.get(piexif.GPSIFD.GPSLatitudeRef, b'N').decode()

        # Extract longitude
        lon_rational = exif_gps.get(piexif.GPSIFD.GPSLongitude)
        lon_ref = exif_gps.get(piexif.GPSIFD.GPSLongitudeRef, b'E').decode()

        if not all([lat_rational, lon_rational]):
            return None, None

        # Convert rational to decimal
        def rational_to_decimal(rational_list):
            degrees = rational_list[0][0] / rational_list[0][1]
            minutes = rational_list[1][0] / rational_list[1][1]
            seconds = rational_list[2][0] / rational_list[2][1]
            return degrees + minutes/60 + seconds/3600

        lat_decimal = rational_to_decimal(lat_rational)
        lon_decimal = rational_to_decimal(lon_rational)

        # Apply direction
        if lat_ref == 'S':
            lat_decimal = -lat_decimal
        if lon_ref == 'W':
            lon_decimal = -lon_decimal

        return lat_decimal, lon_decimal

    except (KeyError, IndexError, ZeroDivisionError, AttributeError):
        return None, None