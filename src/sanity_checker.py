import os

def check_sanity(input_dir, logger):
    photos = set()
    metadata_files = set()

    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.startswith("photo_") and file.endswith(".json"):
                metadata_files.add(file.split("_")[1].split(".json")[0])
            elif "_data-download-" in root:
                photo_id = next((pid for pid in metadata_files if pid in file), None)
                if photo_id:
                    photos.add(photo_id)

    unmatched_metadata = metadata_files - photos
    unmatched_photos = photos - metadata_files

    for photo in unmatched_photos:
        logger.log(f"[WARNING] No metadata for image with ID {photo}")

    for metadata in unmatched_metadata:
        logger.log(f"[WARNING] No matching image for metadata with ID {metadata}")

    logger.log(f"[INFO] Sanity Check: {len(photos)} matched, {len(unmatched_photos)} orphan photos, {len(unmatched_metadata)} orphan metadata.")
