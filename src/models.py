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
