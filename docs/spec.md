# **Metadata Embedding Script Specification**

## **1. Overview**

This Python script is designed to embed EXIF metadata (date taken and geolocation) into images from Flickr exports. Metadata is extracted from JSON files and matched to image files based on an ID-based naming convention.

## **2. Requirements**

### **2.1 Functional Requirements**

- Extract date taken and geolocation metadata from Flickr JSON files.
- Embed the extracted metadata into corresponding image files.
- Preserve original filenames.
- Log warnings and errors to both the console and a log file.
- Allow an optional parameter to **overwrite** existing image files.
- Support a **sanity check mode** to identify missing metadata or unmatched images without modifying files.
- Process images **sequentially** for reliability.
- Preserve existing EXIF metadata if conflicting values exist in the JSON file.
- Provide a **verbose mode** for debugging.

### **2.2 Non-Functional Requirements**

- Cross-platform compatibility (Windows, macOS, Linux).
- Modular architecture for future extensions (e.g., additional metadata fields).
- Well-structured, maintainable code.
- Exit with status codes:
    - `0` for success (no warnings or errors).
    - `1` if warnings/errors are encountered.

## **3. Directory & Naming Conventions**

- **Input Directory Structure:**
    - Subdirectories starting with **`data-download-`** contain images.
    - Other subdirectories contain JSON metadata files.
- **JSON Metadata Naming:**
    - Metadata files follow the pattern **`photo_<id>.json`** (e.g., `photo_958989.json`).
- **Matching Logic:**
    - Each JSON file contains a field **`id`**, which corresponds to an image filename that contains the substring **`_<id>_`**.

## **4. Architecture Design**

### **4.1 Main Components**

- **Metadata Extraction Module** (`metadata_parser.py`)
    - Reads JSON files and extracts required EXIF fields.
- **Image Processing Module** (`image_updater.py`)
    - Embeds metadata into images using a suitable library.
- **Sanity Check Module** (`sanity_checker.py`)
    - Validates metadata-image matching before processing.
- **Logging Module** (`logger.py`)
    - Handles logging to both the console and a text file.

### **4.2 Command-Line Interface**

Supported arguments:

- `-input-dir` (Required): Specifies the input directory containing Flickr export files.
- `-output-dir` (Required unless overwriting): Defines where updated images are saved.
- `-overwrite` (Optional, default: `False`): Determines if the script overwrites original files.
- `-sanity-check` (Optional, default: `False`): Runs a validation check without modifying images.
- `-verbose` (Optional, default: `False`): Enables debug-level logging.

## **5. Error Handling**

- **Missing JSON metadata for an image:** Logs a warning.
- **Missing image file for a JSON metadata entry:** Logs a warning.
- **Multiple matching images for a metadata entry:** Logs a warning.
- **Failure embedding metadata into an image:** Logs the error and skips processing that file.
- **Conflicting existing metadata in an image:** Preserves existing values and logs a warning.
- **Invalid/missing output directory:** Halts execution.

## **6. Logging Strategy**

- Errors and warnings are logged **both** to the console and a text file.
- The log file is stored inside the output directory (`metadata_processing.log`).
- Example log format:

```
[WARNING] Metadata file photo_123456.json has no matching image. [ERROR] Failed to write metadata to image IMG_7890.jpg.

```

## **7. Dependency Management**

- Dependencies specified via `requirements.txt`.
- The script selects an appropriate Python library for EXIF writing based on functionality and ease of use.

## **8. Testing Plan**

### **8.1 Unit Tests**

- Validate JSON parsing logic and field extraction.
- Ensure images are matched correctly using the ID-based naming convention.
- Check that metadata embedding functions as expected.
- Verify error handling cases (e.g., missing metadata, conflicting values).

### 8.1.1 Metadata Extraction (`metadata_parser.py`)

### Test JSON Parsing

- **Valid metadata file**: Ensure correct extraction of `id`, `date_taken`, and `geolocation`.
- **Missing fields**: Handle cases where `date_taken` or `geolocation` are absent.
- **Invalid JSON file**: Gracefully handle corrupted or improperly formatted JSON.
- **Extra fields**: Ignore unrelated metadata while still extracting needed values.

### 8.1.2 Image Processing (`image_updater.py`)

### Test Metadata Embedding

- **Valid EXIF update**: Confirm metadata is correctly embedded into an image.
- **Conflicting existing metadata**: Ensure original EXIF data is **preserved** when conflicting metadata exists.
- **Image format preservation**: Verify output images retain their original format (JPEG, PNG, etc.).
- **Invalid image file**: Properly handle cases where an image file is corrupted or unsupported.

### 8.1.3 Sanity Check (`sanity_checker.py`)

### Test Metadata-Image Matching

- **Perfect match scenario**: Confirm correct metadata-image pairing.
- **Missing metadata file**: Log a warning when an image has **no corresponding metadata**.
- **Missing image file**: Log a warning when a metadata entry has **no corresponding image**.
- **Multiple matching images**: Log a warning when **more than one image** matches the same metadata ID.

### 8.1.4 Logging (`logger.py`)

### Test Log Generation

- **Errors & warnings logging**: Ensure issues are correctly written to both the **console** and **log file**.
- **Log format validation**: Confirm each entry follows the structured **one-line-per-warning/error** format.

### 8.1.5 Command-Line Interface (`main.py`)

### Test CLI Arguments Handling

- **Valid argument combinations**: Ensure expected behavior when users provide correct arguments.
- **Missing required arguments**: Confirm the script **halts execution** when critical arguments are absent.
- **Sanity check mode functionality**: Verify metadata validation works without modifying images.
- **Verbose mode behavior**: Ensure **informational logging** is enabled when `-verbose` is used.

### **8.2 Integration Tests**

- Test script execution with a full Flickr export sample.
- Validate proper handling of metadata embedding.
- Ensure logging captures warnings/errors correctly.

### **8.3 Edge Cases**

- Metadata files with corrupted or missing fields.
- Images with unusual filenames.
- Directories with large numbers of files.
- Different operating systems