"""Declarative mapping from Flickr JSON fields to EXIF/IPTC/XMP tag names.

Pure constants, zero logic. All tag names use pyexiv2 format: "Family.Group.TagName".
Docs: https://exiv2.org/tags.html (EXIF), https://exiv2.org/iptc.html (IPTC),
      https://exiv2.org/tags-xmp-dc.html (XMP Dublin Core)
"""

from __future__ import annotations

# AIDEV-NOTE: Each dict maps standard name -> pyexiv2 tag key

# --- Title (Flickr "name" field) ---
TITLE_TAGS = {
    "exif": "Exif.Image.ImageDescription",
    "iptc": "Iptc.Application2.ObjectName",
    "xmp": "Xmp.dc.title",
}

# --- Description ---
DESCRIPTION_TAGS = {
    "exif": "Exif.Photo.UserComment",
    "iptc": "Iptc.Application2.Caption",
    "xmp": "Xmp.dc.description",
}

# --- Date Taken ---
# AIDEV-NOTE: IPTC splits date and time into separate fields
DATE_TAGS = {
    "exif": "Exif.Photo.DateTimeOriginal",
    "iptc_date": "Iptc.Application2.DateCreated",
    "iptc_time": "Iptc.Application2.TimeCreated",
    "xmp": "Xmp.photoshop.DateCreated",
}

# --- Tags/Keywords ---
KEYWORDS_TAGS = {
    "iptc": "Iptc.Application2.Keywords",
    "xmp": "Xmp.dc.subject",
}

# --- License/Copyright ---
LICENSE_TAGS = {
    "iptc": "Iptc.Application2.Copyright",
    "xmp": "Xmp.dc.rights",
}

# --- Rotation -> EXIF Orientation ---
# AIDEV-NOTE: Flickr rotation is degrees (0, 90, 180, 270)
# EXIF Orientation: 1=normal, 6=90CW, 3=180, 8=90CCW
ROTATION_TO_ORIENTATION = {
    0: 1,
    90: 6,
    180: 3,
    270: 8,
}
ORIENTATION_TAG = "Exif.Image.Orientation"

# --- Albums -> Supplemental Categories ---
ALBUMS_TAGS = {
    "iptc": "Iptc.Application2.SuppCategory",
    "xmp": "Xmp.lr.hierarchicalSubject",
}

# --- GPS (coordinates handled by gps_converter.py) ---
GPS_TAGS = {
    "lat": "Exif.GPSInfo.GPSLatitude",
    "lat_ref": "Exif.GPSInfo.GPSLatitudeRef",
    "lon": "Exif.GPSInfo.GPSLongitude",
    "lon_ref": "Exif.GPSInfo.GPSLongitudeRef",
}

# All embeddable field names (for --fields / --skip-fields CLI filtering)
ALL_FIELDS = frozenset({
    "title", "description", "date", "gps", "tags", "license", "rotation", "albums",
})
