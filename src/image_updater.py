import os
import piexif


def embed_metadata(input_dir, output_dir, metadata, overwrite, logger):
    """
    Embed EXIF metadata into images based on Flickr export data.

    Searches for images matching photo IDs and updates their EXIF with date taken
    and GPS data. Flickr image filenames contain the photo ID (e.g., '12345678_original.jpg').
    Preserves the existing EXIF structure and only updates specified fields.

    Args:
        input_dir: Root of Flickr export containing image files in subdirs
        output_dir: Destination for updated images (ignored if overwrite=True)
        metadata: Dict mapping photo_id -> {'date_taken', 'geolocation'} from parser
        overwrite: If True, updates files in-place; if False, saves to output_dir
        logger: Logger instance for progress and error reporting

    Note:
        GPS data format conversion from Flickr JSON to EXIF GPS IFD may be incomplete.
        The current implementation assumes direct assignment; production needs proper
        lat/lon to degrees/minutes/seconds conversion per EXIF specification.
        Only processes JPEG/TIFF files with existing EXIF support.
    """
    for root, _, files in os.walk(input_dir):
        for file in files:
            if any(photo_id in file for photo_id in metadata.keys()):
                file_path = os.path.join(root, file)
                output_path = os.path.join(output_dir, file) if not overwrite else file_path

                try:
                    exif_dict = piexif.load(file_path)
                    photo_id = [pid for pid in metadata.keys() if pid in file][0]

                    if metadata[photo_id]["date_taken"]:
                        exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = metadata[photo_id]["date_taken"].encode()

                    if metadata[photo_id]["geolocation"]:
                        exif_dict["GPS"] = metadata[photo_id]["geolocation"]  # Adjust format if needed

                    piexif.insert(piexif.dump(exif_dict), output_path)
                    logger.log(f"[INFO] Metadata embedded into {file}")

                except Exception as e:
                    logger.log(f"[ERROR] Failed to embed metadata in {file}: {e}")
