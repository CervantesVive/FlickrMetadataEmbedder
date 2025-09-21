
This checklist outlines all the tasks required to build the metadata embedding project, from initial setup to final integration and documentation.

---

## 1. Project Initialization & Scaffolding
- [x] **Initialize Git Repository**
  - [x] Run `git init` in the project root.
- [x] **Create Directory Structure**
  - [x] Create `src/` for source code.
      - [x] Create `src/__init__.py`
      - [x] Create `src/main.py`
      - [x] Create `src/logger.py`
      - [x] Create `src/metadata_parser.py`
      - [x] Create `src/image_updater.py`
      - [x] Create `src/sanity_checker.py`
  - [x] Create `tests/` for unit and integration tests.
      - [x] Create `tests/test_logger.py`
      - [x] Create `tests/test_metadata_parser.py`
      - [x] Create `tests/test_image_updater.py`
      - [x] Create `tests/test_sanity_checker.py`
  - [x] Create `config/` for configuration files.
      - [x] Create `config/settings.py`
  - [x] Create root-level files:
      - [x] `README.md` – Include project overview and purpose.
      - [x] `requirements.txt`
      - [x] `.gitignore` – Exclude logs, virtual environments, etc.

---

## 2. Dependency Management
- [x] **Set Up `requirements.txt`**
  - [x] Add dependency for `piexif` (e.g., `piexif>=1.1.3`).
  - [x] Add dependency for `pytest` (e.g., `pytest>=7.0.0`).
- [x] **Configure `.gitignore`**
  - [x] Exclude common files/directories such as `venv/`, `__pycache__/`, log files, etc.

---

## 3. Module Implementation

### Logger Module (`src/logger.py`)
- [x] **Implement Logger Class**
  - [x] Initialize with output directory and verbose flag.
  - [x] Write a method to log messages to `metadata_processing.log`.
  - [x] Print errors/warnings to console (and info messages when verbose mode is on).
- [x] **Unit Test the Logger**
  - [x] Write tests in `tests/test_logger.py` to simulate logging at various levels.

### Metadata Parser Module (`src/metadata_parser.py`)
- [x] **Implement Metadata Extraction**
  - [x] Walk through the input directory recursively.
  - [x] Identify JSON files starting with `"photo_"` and ending with `".json"`.
  - [x] Extract required metadata fields: `id`, `date_taken`, and `geolocation`.
  - [x] Construct and return a dictionary mapping photo IDs to their metadata.
  - [x] Log any JSON parsing errors using Logger.
- [ ] **Unit Test the Metadata Parser**
  - [x] Create tests in `tests/test_metadata_parser.py` for valid JSONs, missing fields, and invalid files.

### Image Updater Module (`src/image_updater.py`)
- [x] **Implement Image Updating Functionality**
  - [x] Locate image files within subdirectories named with `data-download-` and match their IDs.
  - [x] Use `piexif` to load an image’s EXIF data.
  - [x] Update the `DateTimeOriginal` and `GPS` EXIF fields if provided.
  - [x] Maintain original file format and preserve existing conflicting metadata (log a warning).
  - [x] Write the updated EXIF back to the image, handling any I/O errors gracefully.
- [x] **Unit Test the Image Updater**
  - [x] Create tests in `tests/test_image_updater.py` to verify correct metadata embedding and error handling.

### Sanity Checker Module (`src/sanity_checker.py`)
- [ ] **Implement Sanity Validation**
  - [ ] Traverse the input directory for JSON metadata and image files.
  - [ ] Determine matches using the photo ID embedded in filenames.
  - [ ] Log warnings for:
      - [ ] Metadata files with no matching image.
      - [ ] Image files with no corresponding metadata.
      - [ ] Cases where multiple images match one metadata file.
  - [ ] Log a summary count: matched pairs, orphan images, and orphan metadata files.
- [ ] **Unit Test the Sanity Checker**
  - [ ] Write tests in `tests/test_sanity_checker.py` to create dummy structures and validate logs.

### Main CLI Module (`src/main.py`)
- [ ] **Implement the Command-Line Interface**
  - [ ] Use `argparse` to parse CLI arguments:
      - [ ] `--input-dir` (required)
      - [ ] `--output-dir` (required, unless overwrite is enabled)
      - [ ] `--overwrite` flag
      - [ ] `--sanity-check` flag
      - [ ] `--verbose` flag
  - [ ] Initialize Logger with appropriate parameters.
  - [ ] If `--sanity-check` is set, run the sanity checker and exit.
  - [ ] Otherwise, run the metadata parser to extract data and call the image updater to embed metadata.
- [ ] **Integration Testing for CLI**
  - [ ] Write integration tests in a file (e.g., `tests/test_integration.py`) that simulates:
      - [ ] Full run of the process.
      - [ ] Sanity-check mode and expected log output.

---

## 4. Testing & Documentation
- [ ] **Unit Tests**
  - [ ] Ensure every module has unit tests covering typical and edge cases.
- [ ] **Integration Tests**
  - [ ] Evaluate the complete flow from reading metadata to updating images.
- [ ] **Update Documentation**
  - [ ] Revise `README.md` with:
      - [ ] Project overview, purpose, and dependencies.
      - [ ] Installation instructions.
      - [ ] Usage examples (including all CLI flags).
      - [ ] Testing instructions.
- [ ] **Final Review**
  - [ ] Run all tests (e.g., using `pytest`) to verify functionality.
  - [ ] Ensure all code is properly integrated and there is no orphaned or unconnected code.

---

## 5. Finalization & Deployment
- [ ] **Code Review & Commit**
  - [ ] Review code for adherence to best practices.
  - [ ] Commit the project with clear commit messages (e.g., initial commit, module additions, test implementations, etc.).
- [ ] **Prepare for Distribution**
  - [ ] Confirm the project runs on all intended platforms.
  - [ ] Document any additional steps or considerations for future extensions.
