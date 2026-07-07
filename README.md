# FlickrMetadataEmbedder

A Python CLI tool that processes Flickr export data to embed EXIF, IPTC, and XMP metadata directly into image files. This preserves your photo metadata when migrating away from Flickr.

## Purpose

When you export your photos from Flickr, the metadata is stored separately in JSON files rather than embedded in the images themselves. This tool:

- Reads Flickr's exported JSON metadata files
- Matches them with corresponding image files by photo ID
- Embeds metadata into EXIF, IPTC, and XMP standards simultaneously
- Preserves existing metadata already in your images
- Supports resumable processing for large exports (10,000+ photos)

### Metadata Embedded

| Flickr JSON field | EXIF | IPTC | XMP |
|---|---|---|---|
| `name` (title) | ImageDescription | ObjectName | dc:title |
| `description` | UserComment | Caption | dc:description |
| `date_taken` | DateTimeOriginal | DateCreated | photoshop:DateCreated |
| `tags` | -- | Keywords | dc:subject |
| `license` | -- | Copyright | dc:rights |
| `rotation` | Orientation | -- | -- |
| `albums` | -- | SuppCategory | lr:hierarchicalSubject |
| `geo` (lat/lon) | GPSInfo | -- | -- |

## Requirements

- Python 3.12 or higher
- pyexiv2 (EXIF/IPTC/XMP read/write)
- pydantic (JSON validation)
- rich (progress bars and console output)

On macOS, you may need: `brew install inih`

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/FlickrMetadataEmbedder.git
cd FlickrMetadataEmbedder
```

### 2. Set Up Virtual Environment (Recommended)

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

Using Poe the Poet (recommended):
```bash
pip install poethepoet
poe install
```

Or directly with pip:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Process your Flickr export and save modified copies to an output directory:

```bash
python -m src.main --input-dir /path/to/flickr/export --output-dir /path/to/output
```

### Command-Line Options

| Option | Description | Required |
|--------|-------------|----------|
| `--input-dir` | Directory containing your Flickr export | Yes |
| `--output-dir` | Directory where processed images will be saved | One of output-dir/overwrite required |
| `--overwrite` | Modify original images in-place | One of output-dir/overwrite required |
| `--sanity-check` | Validate metadata/image matching without processing | No |
| `--dry-run` | Show what would be embedded, write nothing | No |
| `--resume` | Skip already-processed files | No |
| `--force` | Reprocess everything (ignore resume state) | No |
| `--fields` | Only embed these fields (comma-separated) | No |
| `--skip-fields` | Embed all fields except these (comma-separated) | No |
| `--verbose` | Enable debug-level console logging | No |
| `--quiet` | Only show warnings and errors | No |
| `--strict` | Stop on first error | No |

Available field names for `--fields` / `--skip-fields`: `title`, `description`, `date`, `gps`, `tags`, `license`, `rotation`, `albums`

### Examples

#### Standard Processing
```bash
python -m src.main \
  --input-dir ~/Downloads/flickr-export \
  --output-dir ~/Pictures/flickr-processed
```

#### Sanity Check Before Processing
Validate that metadata files and images match correctly:
```bash
python -m src.main \
  --input-dir ~/Downloads/flickr-export \
  --sanity-check --verbose
```

#### Dry Run
See what would be embedded without writing anything:
```bash
python -m src.main \
  --input-dir ~/Downloads/flickr-export \
  --dry-run --verbose
```

#### Resume After Interruption
```bash
python -m src.main \
  --input-dir ~/Downloads/flickr-export \
  --output-dir ~/Pictures/flickr-processed \
  --resume
```

#### Embed Only Specific Fields
```bash
python -m src.main \
  --input-dir ~/Downloads/flickr-export \
  --output-dir ~/Pictures/flickr-processed \
  --fields title,date,license
```

#### Modify Originals In-Place
```bash
python -m src.main \
  --input-dir ~/Downloads/flickr-export \
  --overwrite
```

### Using Poe Task Runner

```bash
poe run                    # Basic run (requires arguments)
poe run-with-overwrite     # Run with --overwrite flag
poe run-sanity-check       # Run sanity check with --verbose
poe test                   # Run all tests
poe test-verbose           # Run tests with verbose output
poe clean                  # Clean __pycache__ directories
```

## How It Works

1. **File Scanning**: Single-pass directory walk builds `{photo_id -> path}` indexes for both JSON and image files, then matches them in O(n) via dict lookup
2. **Metadata Parsing**: Each JSON file is parsed into a validated Pydantic model (`FlickrPhoto`), handling field variations like empty `geo` arrays
3. **Metadata Mapping**: `FlickrPhoto` is converted to pyexiv2-ready tag dictionaries for EXIF, IPTC, and XMP
4. **Image Writing**: Tags are written to a copy of the image (or in-place with `--overwrite`), preserving any existing metadata
5. **State Tracking**: Successfully processed photo IDs are saved to a state file for resumability

## Project Structure

```
FlickrMetadataEmbedder/
├── src/
│   ├── main.py              # CLI entry point and orchestration
│   ├── models.py            # Pydantic data models
│   ├── file_scanner.py      # Directory scanning and file matching
│   ├── metadata_parser.py   # Flickr JSON parsing
│   ├── tag_definitions.py   # Metadata tag name constants
│   ├── metadata_mapper.py   # FlickrPhoto -> tag dictionaries
│   ├── image_writer.py      # pyexiv2 wrapper for writing metadata
│   ├── gps_converter.py     # GPS decimal -> DMS conversion
│   ├── state_manager.py     # Resume/checkpoint tracking
│   ├── sanity_checker.py    # Validates file matching
│   └── logger.py            # Logging configuration
├── tests/
│   ├── conftest.py          # Shared fixtures (MINIMAL_JPEG, etc.)
│   ├── test_gps_converter.py
│   ├── test_image_writer.py
│   ├── test_logger.py
│   ├── test_metadata_parser.py
│   └── test_sanity_checker.py
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Logging

The tool creates a log file (`metadata_processing.log`) in the output directory with a complete audit trail at DEBUG level. Console output uses rich formatting with:
- `--verbose` for debug-level detail
- Default INFO level for progress
- `--quiet` for warnings and errors only

## Error Handling

- **Non-fatal by default**: Individual file errors are logged but processing continues
- **`--strict` mode**: Stops on first error
- **Tolerant image opening**: Retries with muted libexiv2 log level when encountering corrupt MakerNote data from older cameras
- **Idempotent**: Re-running on already-processed images writes nothing (returns empty result)

Exit codes: `0` = all succeeded, `1` = partial failures, `2` = fatal error.

## Known Limitations

- Supports JPEG images (pyexiv2 also supports TIFF, PNG with limited metadata support)
- Requires Flickr's standard export format with `photo_<id>.json` metadata files
- Images must follow `<name>_<photo_id>_o.<ext>` naming in `data-download-*` directories

## Contributing

Contributions are welcome! Please ensure:
1. Code follows the project's style guidelines (see CLAUDE.md)
2. All tests pass before submitting PRs
3. New features include appropriate tests

## License

MIT — see [LICENSE](LICENSE).

## Author

Ivo Pletikosic (ivo@pletikosic.com)
