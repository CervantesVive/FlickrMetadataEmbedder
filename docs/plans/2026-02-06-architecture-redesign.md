# Architecture Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign FlickrMetadataEmbedder from piexif (EXIF-only, archived) to pyexiv2 (EXIF+IPTC+XMP, active), with Pydantic models, rich progress, O(n) file matching, and all Flickr metadata fields embedded.

**Architecture:** Linear pipeline: `file_scanner` (single-pass O(n) directory walk) -> `metadata_parser` (JSON -> Pydantic FlickrPhoto) -> `metadata_mapper` (FlickrPhoto -> MetadataTags via declarative tag_definitions) -> `image_writer` (pyexiv2 writes EXIF/IPTC/XMP). State manager handles resumability. Rich handles progress bars + logging.

**Tech Stack:** Python 3.12+, pyexiv2 (EXIF/IPTC/XMP), pydantic v2 (validation), rich (progress/logging), pytest

---

## Important Constraints

- **Do NOT modify test files** (per CLAUDE.md G-1: humans own tests)
- **Add `AIDEV-NOTE:` anchors** near non-trivial edited code (per CLAUDE.md G-2)
- Existing GPS tests import `piexif` — keep `piexif` importable until tests are migrated by the developer
- The existing test files (`test_metadata_parser.py`, `test_image_updater.py`, `test_logger.py`, `test_gps_converter.py`) test the OLD API. They WILL break after the rewrite. This is expected and intentional — the developer will update tests separately.

---

## Task 1: Update Dependencies

**Files:**
- Modify: `requirements.txt`
- Modify: `pyproject.toml`

**Step 1: Update requirements.txt**

Replace contents with:
```
pyexiv2>=2.15.0   # EXIF/IPTC/XMP metadata read/write (replaces piexif)
piexif>=1.1.3     # Legacy — kept until GPS converter tests are migrated
pydantic>=2.0     # Data validation for Flickr JSON parsing
rich>=13.0        # Progress bars and console logging
pytest>=7.0.0     # Testing framework
poethepoet>=0.24.0   # Task runner for Python projects
```

**Step 2: Update pyproject.toml dependencies**

In `[project] dependencies`, replace `piexif>=1.1.3` with:
```toml
dependencies = [
    "pyexiv2>=2.15.0",
    "piexif>=1.1.3",
    "pydantic>=2.0",
    "rich>=13.0",
]
```

**Step 3: Install and verify**

Run: `pip install -r requirements.txt`
Expected: All packages install successfully. pyexiv2 has native arm64 wheels for macOS.

If pyexiv2 fails: `brew install gettext inih` then retry.

**Step 4: Smoke-test pyexiv2 import**

Run: `python -c "import pyexiv2; print(pyexiv2.__version__)"`
Expected: Prints version (e.g., `2.15.5`)

**Step 5: Verify existing tests still pass**

Run: `poe test`
Expected: All 20+ GPS converter tests pass. Other tests pass too.

**Step 6: Commit**

```bash
git add requirements.txt pyproject.toml
git commit -m "deps: add pyexiv2, pydantic, rich; keep piexif for legacy tests [AI]"
```

---

## Task 2: Create Pydantic Models (`src/models.py`)

**Files:**
- Create: `src/models.py`

**Step 1: Create models.py with all data models**

This file defines 7 models/enums used across the entire project. No dependencies on other src/ modules.

```python
"""Pydantic models for FlickrMetadataEmbedder.

Defines data structures for the full processing pipeline:
FlickrPhoto (parsed JSON) -> MetadataTags (pyexiv2-ready) -> ProcessingResult (outcome).
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, model_validator


class GeoLocation(BaseModel):
    """GPS coordinates from Flickr JSON geo field."""

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy: int | None = None


class FlickrTag(BaseModel):
    """A single tag from Flickr JSON tags array."""

    tag: str


class FlickrAlbum(BaseModel):
    """Album membership from Flickr JSON albums array."""

    title: str


class FlickrPhoto(BaseModel):
    """Parsed and validated Flickr photo metadata.

    Handles field name variations and type coercion from Flickr JSON.
    The model_validator normalizes the geo field which can be:
    - [] (empty array when no geo data)
    - {"latitude": float, "longitude": float} (dict when populated)
    - Missing entirely
    """

    id: str
    name: str | None = None
    description: str | None = None
    date_taken: str | None = None
    geo: GeoLocation | None = None
    tags: list[FlickrTag] = []
    albums: list[FlickrAlbum] = []
    license: str | None = None
    rotation: int = 0

    # AIDEV-NOTE: model_validator handles geo=[] (empty array) and geolocation field name
    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: dict) -> dict:
        """Normalize Flickr JSON quirks before validation."""
        geo = data.get("geo") or data.pop("geolocation", None)
        if isinstance(geo, list):
            data["geo"] = None
        elif isinstance(geo, dict) and "latitude" in geo:
            data["geo"] = geo
        else:
            data["geo"] = None

        # Normalize empty string description to None
        if data.get("description") == "":
            data["description"] = None

        return data

    @property
    def has_embeddable_data(self) -> bool:
        """True if this photo has any metadata worth embedding."""
        return any([
            self.name,
            self.description,
            self.date_taken,
            self.geo,
            self.tags,
            self.license,
            self.rotation != 0,
            self.albums,
        ])


class PhotoFilePair(BaseModel):
    """Matched pair of JSON metadata file and image file for one photo."""

    photo_id: str
    json_path: Path
    image_path: Path


class ProcessingStatus(str, Enum):
    """Outcome status for a single photo's processing."""

    SUCCESS = "success"
    SKIPPED = "skipped"
    FAILED_PARSE = "failed_parse"
    FAILED_EMBED = "failed_embed"


class ProcessingResult(BaseModel):
    """Outcome of processing a single photo."""

    photo_id: str
    status: ProcessingStatus
    fields_embedded: list[str] = []
    error_message: str | None = None


class MetadataTags(BaseModel):
    """Tag dictionaries ready for pyexiv2.

    Keys are full pyexiv2 tag names like "Exif.Photo.DateTimeOriginal".
    Values are strings, ints, or lists of strings (for multi-value tags).
    """

    exif: dict[str, str | int] = {}
    iptc: dict[str, str | list[str]] = {}
    xmp: dict[str, str | list[str]] = {}

    @property
    def is_empty(self) -> bool:
        """True if no tags are set in any standard."""
        return not (self.exif or self.iptc or self.xmp)

    @property
    def field_count(self) -> int:
        """Total number of individual tags across all standards."""
        return len(self.exif) + len(self.iptc) + len(self.xmp)
```

**Step 2: Verify import works**

Run: `python -c "from src.models import FlickrPhoto, MetadataTags; print('OK')"`
Expected: `OK`

**Step 3: Quick validation smoke test**

Run:
```python
python -c "
from src.models import FlickrPhoto
# Test with real Flickr JSON structure
p = FlickrPhoto.model_validate({'id': '123', 'name': 'test', 'geo': [], 'tags': [], 'date_taken': '2016-09-03 12:44:09'})
print(f'id={p.id}, geo={p.geo}, has_data={p.has_embeddable_data}')
# Test geo normalization
p2 = FlickrPhoto.model_validate({'id': '456', 'geo': {'latitude': 37.7, 'longitude': -122.4}})
print(f'geo={p2.geo}')
"
```
Expected: `id=123, geo=None, has_data=True` and `geo=latitude=37.7 longitude=-122.4 accuracy=None`

**Step 4: Commit**

```bash
git add src/models.py
git commit -m "feat: add Pydantic models for Flickr JSON, metadata tags, and processing results [AI]"
```

---

## Task 3: Create File Scanner (`src/file_scanner.py`)

**Files:**
- Create: `src/file_scanner.py`

**Step 1: Create file_scanner.py**

```python
"""Single-pass directory scanner with O(n) JSON-to-image matching.

Replaces O(n*m) substring matching in old image_updater.py.
Builds {photo_id -> Path} indexes for both JSONs and images in one walk,
then matches pairs via dict lookup.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from src.models import PhotoFilePair

# AIDEV-NOTE: Image naming is <original_name>_<photo_id>_o.jpg in data-download-* dirs
_IMAGE_ID_PATTERN = re.compile(r"_(\d+)_o\.\w+$")

# AIDEV-NOTE: JSON naming is photo_<id>.json (no hash suffix, confirmed from real export)
_JSON_ID_PATTERN = re.compile(r"^photo_(\d+)\.json$")

_IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".tiff", ".tif", ".gif"})


def scan_directory(input_dir: str | Path) -> tuple[dict[str, Path], dict[str, Path]]:
    """Single-pass walk building {photo_id -> path} for JSONs and images.

    Args:
        input_dir: Root Flickr export directory.

    Returns:
        Tuple of (json_index, image_index) where each maps photo_id -> file path.
    """
    json_index: dict[str, Path] = {}
    image_index: dict[str, Path] = {}

    for root, _, files in os.walk(input_dir):
        root_path = Path(root)
        dir_name = root_path.name

        for filename in files:
            file_path = root_path / filename

            # JSON metadata files (any directory)
            json_match = _JSON_ID_PATTERN.match(filename)
            if json_match:
                photo_id = json_match.group(1)
                json_index[photo_id] = file_path
                continue

            # Image files (only in data-download-* directories)
            # AIDEV-NOTE: Flickr exports put images only in data-download-* subdirs
            if dir_name.startswith("data-download-"):
                ext = file_path.suffix.lower()
                if ext in _IMAGE_EXTENSIONS:
                    img_match = _IMAGE_ID_PATTERN.search(filename)
                    if img_match:
                        photo_id = img_match.group(1)
                        image_index[photo_id] = file_path

    return json_index, image_index


def match_pairs(
    json_index: dict[str, Path],
    image_index: dict[str, Path],
) -> tuple[list[PhotoFilePair], list[str], list[str]]:
    """Match JSON metadata files to image files by photo_id.

    Args:
        json_index: Dict mapping photo_id -> json file path.
        image_index: Dict mapping photo_id -> image file path.

    Returns:
        Tuple of (matched_pairs, orphan_json_ids, orphan_image_ids).
    """
    all_ids = set(json_index.keys()) | set(image_index.keys())

    matched: list[PhotoFilePair] = []
    orphan_jsons: list[str] = []
    orphan_images: list[str] = []

    for photo_id in sorted(all_ids):
        has_json = photo_id in json_index
        has_image = photo_id in image_index

        if has_json and has_image:
            matched.append(PhotoFilePair(
                photo_id=photo_id,
                json_path=json_index[photo_id],
                image_path=image_index[photo_id],
            ))
        elif has_json:
            orphan_jsons.append(photo_id)
        else:
            orphan_images.append(photo_id)

    return matched, orphan_jsons, orphan_images
```

**Step 2: Smoke test with real export data**

Run:
```python
python -c "
from src.file_scanner import scan_directory, match_pairs
j, i = scan_directory('/Users/ivo/Documents/flickr-data/72157723356273830_b42a8f6668f0_part2')
print(f'JSONs: {len(j)}, Images: {len(i)}')
pairs, oj, oi = match_pairs(j, i)
print(f'Matched: {len(pairs)}, Orphan JSONs: {len(oj)}, Orphan images: {len(oi)}')
if pairs: print(f'Sample: {pairs[0]}')
"
```
Expected: Should find thousands of JSONs and images with a high match rate.

**Step 3: Commit**

```bash
git add src/file_scanner.py
git commit -m "feat: add O(n) file scanner with dict-based JSON-to-image matching [AI]"
```

---

## Task 4: Rewrite Metadata Parser (`src/metadata_parser.py`)

**Files:**
- Modify: `src/metadata_parser.py`

**Step 1: Rewrite metadata_parser.py**

Replace entire contents. The old version only extracted date_taken + geolocation (wrong field name). The new version parses ALL fields into FlickrPhoto.

```python
"""Parse Flickr JSON files into validated FlickrPhoto models.

Replaces the old extract_metadata() that only read date_taken + geolocation.
Now reads ALL Flickr fields via Pydantic validation with automatic
geo/geolocation field normalization.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import ValidationError

from src.models import FlickrPhoto

logger = logging.getLogger(__name__)


def parse_photo_json(json_path: Path) -> FlickrPhoto | None:
    """Parse a single Flickr JSON file into a FlickrPhoto model.

    Args:
        json_path: Path to a photo_<id>.json file.

    Returns:
        FlickrPhoto if successfully parsed, None otherwise.
    """
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to read %s: %s", json_path.name, e)
        return None

    if "id" not in data or data["id"] is None:
        logger.warning("No 'id' field in %s, skipping", json_path.name)
        return None

    try:
        # AIDEV-NOTE: FlickrPhoto.model_validator handles geo normalization and empty strings
        return FlickrPhoto.model_validate(data)
    except ValidationError as e:
        logger.error("Validation failed for %s: %s", json_path.name, e)
        return None


def parse_all_metadata(json_paths: dict[str, Path]) -> dict[str, FlickrPhoto]:
    """Parse all JSON files into FlickrPhoto models.

    Args:
        json_paths: Dict mapping photo_id -> json file path (from file_scanner).

    Returns:
        Dict mapping photo_id -> FlickrPhoto (only successfully parsed entries).
    """
    results: dict[str, FlickrPhoto] = {}

    for photo_id, json_path in json_paths.items():
        photo = parse_photo_json(json_path)
        if photo is not None:
            results[photo.id] = photo

    return results
```

**Step 2: Smoke test with real JSON file**

Run:
```python
python -c "
from pathlib import Path
from src.metadata_parser import parse_photo_json
import glob
# Find first JSON in real export
jsons = glob.glob('/Users/ivo/Documents/flickr-data/72157723356273830_b42a8f6668f0_part2/**/photo_*.json', recursive=True)
if jsons:
    photo = parse_photo_json(Path(jsons[0]))
    print(f'id={photo.id}, name={photo.name}, date={photo.date_taken}, geo={photo.geo}, tags={len(photo.tags)}, license={photo.license}')
"
```
Expected: Prints parsed metadata from a real Flickr JSON file.

**Step 3: Commit**

```bash
git add src/metadata_parser.py
git commit -m "feat: rewrite metadata_parser to parse all Flickr fields via Pydantic [AI]"
```

---

## Task 5: Create Tag Definitions (`src/tag_definitions.py`)

**Files:**
- Create: `src/tag_definitions.py`

**Step 1: Create tag_definitions.py**

Pure constants file — zero logic, just mapping Flickr fields to pyexiv2 tag names.

```python
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
```

**Step 2: Verify import**

Run: `python -c "from src.tag_definitions import ALL_FIELDS, TITLE_TAGS; print(ALL_FIELDS); print(TITLE_TAGS)"`
Expected: Prints the frozenset and title tags dict.

**Step 3: Commit**

```bash
git add src/tag_definitions.py
git commit -m "feat: add declarative tag definitions for EXIF/IPTC/XMP mapping [AI]"
```

---

## Task 6: Refactor GPS Converter (`src/gps_converter.py`)

**Files:**
- Modify: `src/gps_converter.py`

**Step 1: Add `dms_to_rational_string()` for pyexiv2 format**

Add the new function AFTER the existing `dms_to_rational()`. Also add a legacy deprecation comment to the old piexif-specific functions. Do NOT remove any existing functions — the test file imports all of them.

Add this new function after `dms_to_rational()`:

```python
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
    # AIDEV-NOTE: Same 10000 precision as dms_to_rational() for consistency
    sec_num = int(seconds * 10000)
    return f"{degrees}/1 {minutes}/1 {sec_num}/10000"
```

Also add this comment before `flickr_to_exif_gps`:
```python
# AIDEV-NOTE: Legacy piexif-format functions below. Keep until GPS converter tests are migrated.
```

**Step 2: Verify new function works**

Run:
```python
python -c "
from src.gps_converter import dms_to_rational_string, decimal_to_dms
d, m, s = decimal_to_dms(37.7749)
result = dms_to_rational_string(d, m, s)
print(f'Result: {result}')
assert result == '37/1 46/1 296400/10000', f'Got: {result}'
print('OK')
"
```
Expected: `Result: 37/1 46/1 296400/10000` then `OK`

**Step 3: Run existing tests**

Run: `poe test`
Expected: All existing GPS converter tests still pass (we only added, not changed).

**Step 4: Commit**

```bash
git add src/gps_converter.py
git commit -m "feat: add dms_to_rational_string() for pyexiv2 GPS format [AI]"
```

---

## Task 7: Create Metadata Mapper (`src/metadata_mapper.py`)

**Files:**
- Create: `src/metadata_mapper.py`

**Step 1: Create metadata_mapper.py**

This is the core mapping layer — converts FlickrPhoto -> MetadataTags using tag_definitions constants.

```python
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
```

**Step 2: Smoke test the mapper**

Run:
```python
python -c "
from src.models import FlickrPhoto
from src.metadata_mapper import map_metadata

# Photo with multiple fields
photo = FlickrPhoto.model_validate({
    'id': '123',
    'name': 'Sunset Beach',
    'date_taken': '2016-09-03 12:44:09',
    'license': 'All Rights Reserved',
    'tags': [{'tag': 'sunset'}, {'tag': 'beach'}],
    'geo': [],
})
tags = map_metadata(photo)
print(f'EXIF tags: {len(tags.exif)}')
print(f'IPTC tags: {len(tags.iptc)}')
print(f'XMP tags: {len(tags.xmp)}')
print(f'EXIF date: {tags.exif.get(\"Exif.Photo.DateTimeOriginal\")}')
print(f'Total: {tags.field_count}')
"
```
Expected: Shows mapped tags with EXIF date as `2016:09:03 12:44:09`.

**Step 3: Test field filtering**

Run:
```python
python -c "
from src.models import FlickrPhoto
from src.metadata_mapper import map_metadata
photo = FlickrPhoto.model_validate({'id': '1', 'name': 'Test', 'date_taken': '2016-09-03 12:44:09', 'license': 'CC', 'geo': []})
# Only embed title
tags = map_metadata(photo, fields=frozenset({'title'}))
print(f'field_count={tags.field_count}')
assert 'Exif.Photo.DateTimeOriginal' not in tags.exif, 'Date should not be mapped'
assert 'Exif.Image.ImageDescription' in tags.exif, 'Title should be mapped'
print('Field filtering OK')
"
```
Expected: `field_count=3` then `Field filtering OK`

**Step 4: Commit**

```bash
git add src/metadata_mapper.py
git commit -m "feat: add metadata mapper converting FlickrPhoto to pyexiv2 tag dicts [AI]"
```

---

## Task 8: Create Image Writer (`src/image_writer.py`)

**Files:**
- Create: `src/image_writer.py`

**Step 1: Create image_writer.py**

pyexiv2 wrapper that writes EXIF/IPTC/XMP. Replaces the old piexif-based image_updater.py.

```python
"""Write EXIF/IPTC/XMP metadata to images using pyexiv2.

Replaces old image_updater.py (piexif-only, EXIF-only).
Supports all three metadata standards with preserve-existing behavior.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

import pyexiv2

from src.models import MetadataTags

logger = logging.getLogger(__name__)


def write_metadata(
    image_path: Path,
    output_path: Path,
    metadata: MetadataTags,
    *,
    overwrite: bool = False,
    preserve_existing: bool = True,
) -> list[str]:
    """Write metadata tags to an image file.

    Args:
        image_path: Source image file.
        output_path: Where to save (same as image_path if overwrite=True).
        metadata: MetadataTags with exif/iptc/xmp dicts.
        overwrite: If True, modify image_path in-place (output_path ignored).
        preserve_existing: If True, skip tags that already have values.

    Returns:
        List of tag names that were actually written.

    Raises:
        OSError: If file I/O fails.
        RuntimeError: If pyexiv2 fails to write.
    """
    if metadata.is_empty:
        return []

    # AIDEV-NOTE: Copy-then-modify prevents corruption if write fails mid-way
    target = image_path if overwrite else output_path
    if not overwrite:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(image_path, output_path)

    fields_written: list[str] = []

    # AIDEV-NOTE: pyexiv2.Image context manager ensures proper resource cleanup
    with pyexiv2.Image(str(target)) as img:
        if preserve_existing:
            existing_exif = img.read_exif()
            existing_iptc = img.read_iptc()
            existing_xmp = img.read_xmp()
        else:
            existing_exif = {}
            existing_iptc = {}
            existing_xmp = {}

        # Filter out tags that already exist in the image
        new_exif = {k: v for k, v in metadata.exif.items() if k not in existing_exif}
        new_iptc = {k: v for k, v in metadata.iptc.items() if k not in existing_iptc}
        new_xmp = {k: v for k, v in metadata.xmp.items() if k not in existing_xmp}

        if new_exif:
            img.modify_exif(new_exif)
            fields_written.extend(new_exif.keys())
        if new_iptc:
            img.modify_iptc(new_iptc)
            fields_written.extend(new_iptc.keys())
        if new_xmp:
            img.modify_xmp(new_xmp)
            fields_written.extend(new_xmp.keys())

    return fields_written
```

**Step 2: Verify import**

Run: `python -c "from src.image_writer import write_metadata; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add src/image_writer.py
git commit -m "feat: add pyexiv2-based image writer supporting EXIF/IPTC/XMP [AI]"
```

---

## Task 9: Create State Manager (`src/state_manager.py`)

**Files:**
- Create: `src/state_manager.py`

**Step 1: Create state_manager.py**

```python
"""Track processed photos for resumability.

State file is a JSON dict: {photo_id: unix_timestamp, ...}
Batch-saves every 50 photos to reduce I/O overhead.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_STATE_FILENAME = ".flickr_embed_state.json"
_BATCH_SIZE = 50


class StateManager:
    """Tracks processed photos for --resume support.

    Saves state to a JSON file in the output directory.
    Batch-writes every _BATCH_SIZE photos to minimize disk I/O.
    """

    def __init__(self, state_dir: str | Path) -> None:
        self._state_path = Path(state_dir) / _STATE_FILENAME
        self._state: dict[str, float] = {}
        self._dirty_count = 0

    def load(self) -> set[str]:
        """Load state from disk.

        Returns:
            Set of already-processed photo_ids.
        """
        if self._state_path.exists():
            try:
                with open(self._state_path, "r") as f:
                    self._state = json.load(f)
                logger.info("Loaded state: %d already processed", len(self._state))
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to load state file: %s", e)
                self._state = {}
        return set(self._state.keys())

    def mark_processed(self, photo_id: str) -> None:
        """Mark a photo as processed. Batch-saves to disk."""
        self._state[photo_id] = time.time()
        self._dirty_count += 1
        if self._dirty_count >= _BATCH_SIZE:
            self.save()

    def save(self) -> None:
        """Flush pending state to disk."""
        if self._dirty_count > 0:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._state_path, "w") as f:
                json.dump(self._state, f)
            self._dirty_count = 0

    @property
    def processed_count(self) -> int:
        """Number of photos tracked in state."""
        return len(self._state)


def load_state(state_dir: str | Path) -> set[str]:
    """Convenience function to load state without keeping a StateManager."""
    mgr = StateManager(state_dir)
    return mgr.load()
```

**Step 2: Verify import**

Run: `python -c "from src.state_manager import StateManager; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add src/state_manager.py
git commit -m "feat: add state manager for resume/checkpoint support [AI]"
```

---

## Task 10: Rewrite Logger (`src/logger.py`)

**Files:**
- Modify: `src/logger.py`

**Step 1: Rewrite logger.py**

Replace the old Logger class (opens/closes file per message) with stdlib logging + rich handler.

```python
"""Logging setup with rich console output and file handler.

Replaces the old Logger class that opened/closed the log file on every message.
Uses stdlib logging with a rich console handler for pretty output.
"""

from __future__ import annotations

import logging
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler


def setup_logging(
    output_dir: str | Path | None = None,
    verbose: bool = False,
    quiet: bool = False,
) -> None:
    """Configure logging for the application.

    Args:
        output_dir: Directory for log file. If None, console-only.
        verbose: Enable DEBUG-level console output.
        quiet: Suppress INFO, show WARNING+ only.
    """
    root_logger = logging.getLogger("src")
    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers.clear()

    # Rich console handler
    console_level = logging.DEBUG if verbose else (logging.WARNING if quiet else logging.INFO)
    console = Console(stderr=True)
    rich_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=False,
        rich_tracebacks=True,
    )
    rich_handler.setLevel(console_level)
    root_logger.addHandler(rich_handler)

    # AIDEV-NOTE: File handler always captures DEBUG for complete audit trail
    if output_dir:
        log_path = Path(output_dir) / "metadata_processing.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        root_logger.addHandler(file_handler)
```

Note: The old `Logger` class API (`Logger(dir, verbose)` + `logger.log(msg)`) is used by old test files. Those tests will break — this is expected. The developer will update tests separately.

**Step 2: Verify import**

Run: `python -c "from src.logger import setup_logging; setup_logging(verbose=True); import logging; logging.getLogger('src').info('test message')"`
Expected: Prints a rich-formatted "test message" to stderr.

**Step 3: Commit**

```bash
git add src/logger.py
git commit -m "feat: rewrite logger with stdlib logging + rich console handler [AI]"
```

---

## Task 11: Rewrite Sanity Checker (`src/sanity_checker.py`)

**Files:**
- Modify: `src/sanity_checker.py`

**Step 1: Rewrite sanity_checker.py**

Replace the buggy implementation (splits on `_`, wrong directory matching) with one that uses file_scanner.

```python
"""Validate JSON-to-image matching using file_scanner.

Replaces old implementation that had bugs with filename splitting
and directory name matching.
"""

from __future__ import annotations

import logging
from pathlib import Path

from rich.console import Console
from rich.table import Table

from src.file_scanner import scan_directory, match_pairs

logger = logging.getLogger(__name__)


def run_sanity_check(input_dir: str | Path) -> int:
    """Run sanity check and print results.

    Args:
        input_dir: Root Flickr export directory.

    Returns:
        Exit code: 0 if all matched, 1 if orphans found.
    """
    # AIDEV-NOTE: Reuses file_scanner for consistent matching logic across the app
    json_index, image_index = scan_directory(input_dir)
    pairs, orphan_jsons, orphan_images = match_pairs(json_index, image_index)

    console = Console()
    table = Table(title="Sanity Check Results")
    table.add_column("Category", style="bold")
    table.add_column("Count", justify="right")
    table.add_row("Matched pairs", f"[green]{len(pairs)}[/green]")
    table.add_row(
        "Orphan JSONs (no image)",
        f"[yellow]{len(orphan_jsons)}[/yellow]" if orphan_jsons else "0",
    )
    table.add_row(
        "Orphan images (no JSON)",
        f"[yellow]{len(orphan_images)}[/yellow]" if orphan_images else "0",
    )
    console.print(table)

    if orphan_jsons:
        logger.warning("Orphan JSON IDs (first 20): %s", orphan_jsons[:20])
    if orphan_images:
        logger.warning("Orphan image IDs (first 20): %s", orphan_images[:20])

    return 1 if (orphan_jsons or orphan_images) else 0
```

**Step 2: Commit**

```bash
git add src/sanity_checker.py
git commit -m "feat: rewrite sanity_checker using file_scanner for correct matching [AI]"
```

---

## Task 12: Rewrite Main CLI (`src/main.py`)

**Files:**
- Modify: `src/main.py`

**Step 1: Rewrite main.py**

Full CLI orchestration with rich progress bars, resume support, field filtering, and all new modules wired together.

```python
"""CLI entry point for FlickrMetadataEmbedder.

Orchestrates the full pipeline: scan -> parse -> map -> write.
Supports --dry-run, --sanity-check, --resume, --fields, --strict.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from collections import Counter
from pathlib import Path

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table

from src.file_scanner import scan_directory, match_pairs
from src.image_writer import write_metadata
from src.logger import setup_logging
from src.metadata_mapper import map_metadata
from src.metadata_parser import parse_all_metadata
from src.models import ProcessingResult, ProcessingStatus
from src.sanity_checker import run_sanity_check
from src.state_manager import StateManager
from src.tag_definitions import ALL_FIELDS

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Embed Flickr metadata into image EXIF/IPTC/XMP",
    )
    parser.add_argument("--input-dir", required=True, help="Flickr export directory")
    parser.add_argument("--output-dir", help="Output directory for modified images")
    parser.add_argument("--overwrite", action="store_true", help="Modify originals in-place")
    parser.add_argument("--sanity-check", action="store_true", help="Validate matching only")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be embedded")
    parser.add_argument("--resume", action="store_true", help="Skip already-processed files")
    parser.add_argument("--force", action="store_true", help="Reprocess everything")
    parser.add_argument("--fields", help="Comma-separated fields to embed")
    parser.add_argument("--skip-fields", help="Comma-separated fields to skip")
    parser.add_argument("--verbose", action="store_true", help="Debug-level output")
    parser.add_argument("--quiet", action="store_true", help="Warnings and errors only")
    parser.add_argument("--strict", action="store_true", help="Stop on first error")
    return parser.parse_args()


def resolve_fields(args: argparse.Namespace) -> frozenset[str] | None:
    """Parse --fields and --skip-fields into a frozenset, or None for all."""
    if args.fields:
        requested = frozenset(f.strip() for f in args.fields.split(","))
        invalid = requested - ALL_FIELDS
        if invalid:
            print(f"Error: Unknown fields: {invalid}. Valid: {sorted(ALL_FIELDS)}")
            sys.exit(2)
        return requested
    if args.skip_fields:
        skip = frozenset(f.strip() for f in args.skip_fields.split(","))
        invalid = skip - ALL_FIELDS
        if invalid:
            print(f"Error: Unknown fields: {invalid}. Valid: {sorted(ALL_FIELDS)}")
            sys.exit(2)
        return ALL_FIELDS - skip
    return None


def main() -> int:
    """Main entry point. Returns exit code."""
    args = parse_args()

    # Validate args
    if not args.overwrite and not args.output_dir and not args.sanity_check and not args.dry_run:
        print("Error: --output-dir or --overwrite required (unless --sanity-check or --dry-run)")
        return 2

    output_target = args.output_dir if not args.overwrite else args.input_dir
    setup_logging(output_dir=output_target, verbose=args.verbose, quiet=args.quiet)

    # Sanity check mode — just validate and exit
    if args.sanity_check:
        setup_logging(verbose=args.verbose, quiet=args.quiet)
        return run_sanity_check(args.input_dir)

    # Phase 1: Scan files
    logger.info("Scanning %s...", args.input_dir)
    json_index, image_index = scan_directory(args.input_dir)
    pairs, orphan_jsons, orphan_images = match_pairs(json_index, image_index)
    logger.info(
        "Found %d matched pairs, %d orphan JSONs, %d orphan images",
        len(pairs), len(orphan_jsons), len(orphan_images),
    )

    # Phase 2: Parse metadata
    logger.info("Parsing metadata...")
    all_metadata = parse_all_metadata(json_index)
    logger.info("Parsed %d photo metadata files", len(all_metadata))

    # Phase 3: Process each pair
    fields = resolve_fields(args)
    results: list[ProcessingResult] = []
    console = Console()

    # State manager for resume support
    state_mgr = StateManager(output_target) if not args.dry_run else None
    processed_ids: set[str] = set()
    if args.resume and state_mgr and not args.force:
        processed_ids = state_mgr.load()

    start_time = time.time()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Embedding metadata", total=len(pairs))

        for pair in pairs:
            progress.update(task, advance=1)

            # Skip if already processed (resume mode)
            if pair.photo_id in processed_ids:
                results.append(ProcessingResult(
                    photo_id=pair.photo_id,
                    status=ProcessingStatus.SKIPPED,
                ))
                continue

            # Get parsed metadata for this photo
            photo = all_metadata.get(pair.photo_id)
            if not photo or not photo.has_embeddable_data:
                results.append(ProcessingResult(
                    photo_id=pair.photo_id,
                    status=ProcessingStatus.SKIPPED,
                ))
                continue

            # Map to tags
            mapped_tags = map_metadata(photo, fields)
            if mapped_tags.is_empty:
                results.append(ProcessingResult(
                    photo_id=pair.photo_id,
                    status=ProcessingStatus.SKIPPED,
                ))
                continue

            if args.dry_run:
                logger.info(
                    "[DRY RUN] Would embed %d tags into %s",
                    mapped_tags.field_count, pair.image_path.name,
                )
                results.append(ProcessingResult(
                    photo_id=pair.photo_id,
                    status=ProcessingStatus.SUCCESS,
                    fields_embedded=(
                        list(mapped_tags.exif.keys())
                        + list(mapped_tags.iptc.keys())
                        + list(mapped_tags.xmp.keys())
                    ),
                ))
                continue

            # Write metadata to image
            try:
                output_path = (
                    Path(args.output_dir) / pair.image_path.name
                    if args.output_dir
                    else pair.image_path
                )
                fields_written = write_metadata(
                    pair.image_path,
                    output_path,
                    mapped_tags,
                    overwrite=args.overwrite,
                )
                results.append(ProcessingResult(
                    photo_id=pair.photo_id,
                    status=ProcessingStatus.SUCCESS,
                    fields_embedded=fields_written,
                ))
                if state_mgr:
                    state_mgr.mark_processed(pair.photo_id)
            except Exception as e:
                logger.error("Failed to embed %s: %s", pair.image_path.name, e)
                results.append(ProcessingResult(
                    photo_id=pair.photo_id,
                    status=ProcessingStatus.FAILED_EMBED,
                    error_message=str(e),
                ))
                if args.strict:
                    logger.error("Stopping (--strict mode)")
                    break

    # Flush remaining state
    if state_mgr:
        state_mgr.save()

    duration = time.time() - start_time
    _print_summary(results, duration, console)

    has_failures = any(
        r.status in (ProcessingStatus.FAILED_PARSE, ProcessingStatus.FAILED_EMBED)
        for r in results
    )
    return 1 if has_failures else 0


def _print_summary(
    results: list[ProcessingResult],
    duration: float,
    console: Console,
) -> None:
    """Print processing summary using rich table."""
    status_counts = Counter(r.status for r in results)

    table = Table(title="Processing Summary")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")
    table.add_row("Total photos", str(len(results)))
    table.add_row("Embedded", str(status_counts.get(ProcessingStatus.SUCCESS, 0)))
    table.add_row("Skipped", str(status_counts.get(ProcessingStatus.SKIPPED, 0)))
    table.add_row("Failed (parse)", str(status_counts.get(ProcessingStatus.FAILED_PARSE, 0)))
    table.add_row("Failed (embed)", str(status_counts.get(ProcessingStatus.FAILED_EMBED, 0)))

    # Format duration
    minutes, seconds = divmod(int(duration), 60)
    table.add_row("Duration", f"{minutes}m {seconds}s")

    console.print(table)


if __name__ == "__main__":
    sys.exit(main())
```

**Step 2: Verify CLI help works**

Run: `python -m src.main --help`
Expected: Shows all argument descriptions.

**Step 3: Commit**

```bash
git add src/main.py
git commit -m "feat: rewrite main CLI with rich progress, resume, field filtering [AI]"
```

---

## Task 13: Delete Old Image Updater

**Files:**
- Delete: `src/image_updater.py`

**Step 1: Delete image_updater.py**

```bash
git rm src/image_updater.py
```

Note: `tests/test_image_updater.py` will lose its import target. The test file is owned by the developer and should be updated/replaced by them.

**Step 2: Commit**

```bash
git commit -m "chore: remove old piexif-based image_updater.py, replaced by image_writer.py [AI]"
```

---

## Task 14: Integration Testing with Real Export

**Files:** None (verification only)

**Step 1: Run dry-run with real export**

Run:
```bash
python -m src.main --input-dir ~/Documents/flickr-data/72157723356273830_b42a8f6668f0_part2 --dry-run --verbose
```
Expected: Scans directory, shows progress bar, prints summary with tag counts per photo. No files modified.

**Step 2: Run sanity check**

Run:
```bash
python -m src.main --input-dir ~/Documents/flickr-data/72157723356273830_b42a8f6668f0_part2 --sanity-check
```
Expected: Rich-formatted table showing matched pairs, orphan JSONs, orphan images.

**Step 3: Embed a small batch to temp dir**

Run:
```bash
mkdir -p /tmp/flickr-test
python -m src.main --input-dir ~/Documents/flickr-data/72157723356273830_b42a8f6668f0_part2 --output-dir /tmp/flickr-test
```
Expected: Progress bar, photos processed, summary table printed.

**Step 4: Verify embedded metadata**

Run:
```python
python -c "
import pyexiv2, glob
imgs = glob.glob('/tmp/flickr-test/*.jpg')
if imgs:
    with pyexiv2.Image(imgs[0]) as img:
        exif = img.read_exif()
        iptc = img.read_iptc()
        xmp = img.read_xmp()
        print(f'EXIF keys: {list(exif.keys())[:5]}')
        print(f'IPTC keys: {list(iptc.keys())[:5]}')
        print(f'XMP keys: {list(xmp.keys())[:5]}')
        if 'Exif.Photo.DateTimeOriginal' in exif:
            print(f'DateTimeOriginal: {exif[\"Exif.Photo.DateTimeOriginal\"]}')
        if 'Exif.Image.ImageDescription' in exif:
            print(f'Title: {exif[\"Exif.Image.ImageDescription\"]}')
"
```
Expected: Shows embedded EXIF/IPTC/XMP keys with correct values.

**Step 5: Test resume**

Run:
```bash
# Process, then re-run with --resume
python -m src.main --input-dir ~/Documents/flickr-data/72157723356273830_b42a8f6668f0_part2 --output-dir /tmp/flickr-test --resume
```
Expected: All photos show as "Skipped" (already processed). Fast completion.

---

## Task 15: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Update Architecture Overview section**

Replace the current Architecture Overview in CLAUDE.md with the new module descriptions, data flow, and dependency list. Update the Dependencies section to list pyexiv2, pydantic, and rich instead of just piexif.

Key changes:
- Data flow: `file_scanner -> metadata_parser -> metadata_mapper -> image_writer`
- New modules: `models.py`, `file_scanner.py`, `tag_definitions.py`, `metadata_mapper.py`, `image_writer.py`, `state_manager.py`
- Removed: `image_updater.py`
- Dependencies: pyexiv2, pydantic, rich (piexif kept for legacy tests)

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md architecture for pyexiv2 redesign [AI]"
```

---

## Summary: File Changes

| File | Action | Task |
|---|---|---|
| `requirements.txt` | Modify | 1 |
| `pyproject.toml` | Modify | 1 |
| `src/models.py` | **Create** | 2 |
| `src/file_scanner.py` | **Create** | 3 |
| `src/metadata_parser.py` | Rewrite | 4 |
| `src/tag_definitions.py` | **Create** | 5 |
| `src/gps_converter.py` | Add function | 6 |
| `src/metadata_mapper.py` | **Create** | 7 |
| `src/image_writer.py` | **Create** | 8 |
| `src/state_manager.py` | **Create** | 9 |
| `src/logger.py` | Rewrite | 10 |
| `src/sanity_checker.py` | Rewrite | 11 |
| `src/main.py` | Rewrite | 12 |
| `src/image_updater.py` | **Delete** | 13 |
| `CLAUDE.md` | Update | 15 |

**Total: 5 new files, 6 modified files, 1 deleted file**

## Known Test Breakage

After this plan completes, the following test files will need updating by the developer:
- `tests/test_metadata_parser.py` — tests old `extract_metadata()` API, needs update to `parse_photo_json()` / `parse_all_metadata()`
- `tests/test_image_updater.py` — tests deleted module, needs rewrite for `image_writer.py`
- `tests/test_logger.py` — tests old `Logger` class, needs rewrite for `setup_logging()`
- `tests/test_sanity_checker.py` — empty, needs tests for `run_sanity_check()`
- `tests/test_gps_converter.py` — still passes (piexif kept), but will need pyexiv2 format tests added
