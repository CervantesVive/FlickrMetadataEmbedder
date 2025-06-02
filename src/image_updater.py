import os
import piexif


def embed_metadata(input_dir, output_dir, metadata, overwrite, logger):
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
