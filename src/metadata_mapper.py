"""Map FlickrPhoto metadata to pyexiv2-ready MetadataTags.

Converts each Flickr field to the appropriate EXIF/IPTC/XMP tags
using constants from tag_definitions.py. GPS conversion uses gps_converter.py.
"""

from __future__ import annotations

from src.gps_converter import decimal_to_dms, dms_to_rational_string, get_coordinate_ref
from src.models import FlickrPhoto, GeoLocation, MetadataTags
from src import tag_definitions as tags


def map_metadata(
    photo: FlickrPhoto,
    fields: frozenset[str] | None = None,
) -> MetadataTags:
    """Convert a FlickrPhoto into pyexiv2-ready MetadataTags.

    Args:
        photo: Parsed Flickr metadata.
        fields: If set, only map these fields. None = all fields.

    Returns:
        MetadataTags with exif/iptc/xmp dicts populated.
    """
    result = MetadataTags()
    active = fields or tags.ALL_FIELDS

    if "title" in active and photo.name:
        _apply_title(result, photo.name)

    if "description" in active and photo.description:
        _apply_description(result, photo.description)

    if "date" in active and photo.date_taken:
        _apply_date(result, photo.date_taken)

    if "tags" in active and photo.tags:
        _apply_keywords(result, [t.tag for t in photo.tags])

    if "license" in active and photo.license:
        _apply_license(result, photo.license)

    if "rotation" in active and photo.rotation != 0:
        _apply_rotation(result, photo.rotation)

    if "albums" in active and photo.albums:
        _apply_albums(result, [a.title for a in photo.albums])

    if "gps" in active and photo.geo:
        _apply_gps(result, photo.geo)

    return result


def _apply_title(result: MetadataTags, title: str) -> None:
    result.exif[tags.TITLE_TAGS["exif"]] = title
    result.iptc[tags.TITLE_TAGS["iptc"]] = title
    result.xmp[tags.TITLE_TAGS["xmp"]] = title


def _apply_description(result: MetadataTags, description: str) -> None:
    result.exif[tags.DESCRIPTION_TAGS["exif"]] = description
    result.iptc[tags.DESCRIPTION_TAGS["iptc"]] = description
    result.xmp[tags.DESCRIPTION_TAGS["xmp"]] = description


def _apply_date(result: MetadataTags, date_taken: str) -> None:
    """Convert Flickr date format to EXIF/IPTC/XMP formats.

    Flickr: "2016-09-03 12:44:09"
    EXIF:   "2016:09:03 12:44:09"  (colons in date part)
    IPTC:   date="2016-09-03", time="12:44:09"
    XMP:    "2016-09-03T12:44:09"  (ISO 8601)
    """
    # AIDEV-NOTE: Flickr uses "YYYY-MM-DD HH:MM:SS", EXIF needs "YYYY:MM:DD HH:MM:SS"
    parts = date_taken.split(" ")
    if len(parts) == 2:
        date_part, time_part = parts
        exif_date = date_part.replace("-", ":") + " " + time_part
        result.exif[tags.DATE_TAGS["exif"]] = exif_date
        result.iptc[tags.DATE_TAGS["iptc_date"]] = date_part
        result.iptc[tags.DATE_TAGS["iptc_time"]] = time_part
        result.xmp[tags.DATE_TAGS["xmp"]] = f"{date_part}T{time_part}"


def _apply_keywords(result: MetadataTags, keyword_list: list[str]) -> None:
    result.iptc[tags.KEYWORDS_TAGS["iptc"]] = keyword_list
    result.xmp[tags.KEYWORDS_TAGS["xmp"]] = keyword_list


def _apply_license(result: MetadataTags, license_text: str) -> None:
    result.iptc[tags.LICENSE_TAGS["iptc"]] = license_text
    result.xmp[tags.LICENSE_TAGS["xmp"]] = license_text


def _apply_rotation(result: MetadataTags, rotation: int) -> None:
    orientation = tags.ROTATION_TO_ORIENTATION.get(rotation)
    if orientation is not None:
        result.exif[tags.ORIENTATION_TAG] = orientation


def _apply_albums(result: MetadataTags, album_titles: list[str]) -> None:
    result.iptc[tags.ALBUMS_TAGS["iptc"]] = album_titles
    result.xmp[tags.ALBUMS_TAGS["xmp"]] = album_titles


def _apply_gps(result: MetadataTags, geo: GeoLocation) -> None:
    """Convert decimal GPS to pyexiv2 rational string format.

    pyexiv2 expects: "deg/1 min/1 sec_num/sec_den" and "N"/"S"/"E"/"W" refs.
    """
    lat_deg, lat_min, lat_sec = decimal_to_dms(geo.latitude)
    lon_deg, lon_min, lon_sec = decimal_to_dms(geo.longitude)

    result.exif[tags.GPS_TAGS["lat"]] = dms_to_rational_string(lat_deg, lat_min, lat_sec)
    result.exif[tags.GPS_TAGS["lat_ref"]] = get_coordinate_ref(geo.latitude, "lat")
    result.exif[tags.GPS_TAGS["lon"]] = dms_to_rational_string(lon_deg, lon_min, lon_sec)
    result.exif[tags.GPS_TAGS["lon_ref"]] = get_coordinate_ref(geo.longitude, "lon")
