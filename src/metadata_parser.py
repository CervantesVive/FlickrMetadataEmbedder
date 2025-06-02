import json
import os

def extract_metadata(input_dir, logger):
    metadata_dict = {}

    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.startswith("photo_") and file.endswith(".json"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        photo_id = str(data.get("id"))
                        if photo_id:
                            metadata_dict[photo_id] = {
                                "date_taken": data.get("date_taken"),
                                "geolocation": data.get("geolocation")
                            }
                except (json.JSONDecodeError, KeyError) as e:
                    logger.log(f"[ERROR] Failed to parse {file}: {e}")

    return metadata_dict
