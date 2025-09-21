import json
import os

def extract_metadata(input_dir, logger):
    """
    Parse Flickr export JSON files to extract EXIF-embeddable metadata.

    Flickr exports store metadata separately from images in JSON files named
    'photo_<id>_<hash>.json'. This function maps photo IDs to their original
    capture metadata for later EXIF embedding.

    Args:
        input_dir: Root of Flickr export (contains 'data-download-*' subdirs)
        logger: Logger instance for error reporting

    Returns:
        dict: Maps photo_id (str) -> {'date_taken': str, 'geolocation': dict}
              Returns empty dict if no valid metadata found.

    Note:
        Flickr's date format varies by export version. Geolocation may include
        accuracy, context, and place IDs beyond just lat/lon coordinates.
    """
    metadata_dict = {}

    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.startswith("photo_") and file.endswith(".json"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        photo_id = data.get("id")
                        # Skip files without ID field - required for image matching
                        if photo_id is not None:
                            metadata_dict[str(photo_id)] = {
                                "date_taken": data.get("date_taken"),
                                "geolocation": data.get("geolocation")
                            }
                except (json.JSONDecodeError, KeyError) as e:
                    logger.log(f"[ERROR] Failed to parse {file}: {e}")

    return metadata_dict
