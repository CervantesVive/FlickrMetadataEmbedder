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
