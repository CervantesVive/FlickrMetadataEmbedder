import argparse
from src.metadata_parser import extract_metadata
from src.image_updater import embed_metadata
from src.sanity_checker import check_sanity
from src.logger import Logger

def main():
    parser = argparse.ArgumentParser(description="Embed EXIF metadata into images from Flickr exports.")
    parser.add_argument("--input-dir", required=True, help="Directory containing Flickr export.")
    parser.add_argument("--output-dir", required=True, help="Directory to store updated images.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files.")
    parser.add_argument("--sanity-check", action="store_true", help="Run metadata validation without modifying images.")
    parser.add_argument("--verbose", action="store_true", help="Enable detailed logging.")

    args = parser.parse_args()
    logger = Logger(args.output_dir, args.verbose)

    if args.sanity_check:
        check_sanity(args.input_dir, logger)
    else:
        metadata = extract_metadata(args.input_dir, logger)
        embed_metadata(args.input_dir, args.output_dir, metadata, args.overwrite, logger)

if __name__ == "__main__":
    main()
