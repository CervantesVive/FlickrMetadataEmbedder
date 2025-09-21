### **Project Overview**

Create a Python-based command-line tool that reads Flickr export file directories to extract JSON metadata and update corresponding image files with EXIF metadata using the `piexif` library. The tool should also support a “sanity check mode” to verify mismatches between images and metadata.

### **Architecture & Components**

1. **Project Scaffolding & Initialization**
    - Set up a Git repository and a directory structure that separates source code (`src/`), tests (`tests/`), configuration (`config/`), and documentation files.
    - Create essential files like `README.md`, `requirements.txt`, `.gitignore`, etc.
2. **Dependency Management**
    - Manage dependencies using `requirements.txt`. The key libraries include `piexif` for EXIF handling and `pytest` for testing.
3. **Core Modules**
    - **Logger Module (**`src/logger.py`**)**: A simple logging class that writes errors, warnings, and optionally info messages to a log file (and to the console when in verbose mode).
    - **Metadata Parser Module (**`src/metadata_parser.py`**)**: Scans the input directory, locates JSON files with names starting with `"photo_"` and ending with `".json"`, extracts necessary metadata (e.g., `id`, `date_taken`, `geolocation`), and stores this in a dictionary.
    - **Image Updater Module (**`src/image_updater.py`**)**: Locates images based on the ID embedded in the filename (within directories named with the prefix `"data-download-"`) and embeds JSON metadata into the image EXIF using `piexif`. It preserves existing metadata (logging a warning on conflict) and supports an overwrite flag.
    - **Sanity Checker Module (**`src/sanity_checker.py`**)**: Validates the correspondence between metadata files and image files. It logs warnings for missing images, missing metadata, and multiple matches, and then outputs a summary count.
    - **Main CLI Module (**`src/main.py`**)**: Ties all modules together using `argparse` to parse command-line arguments (e.g., input directory, output directory, `-overwrite`, `-sanity-check`, `-verbose`).
4. **Testing Strategy**
    - **Unit Tests:** For each module, validate functionality through unit tests (e.g., correct metadata extraction, proper handling of edge cases, log format maintenance).
    - **Integration Tests:** Assemble dummy directories with test data to simulate the process and verify the complete flow.
5. **Error Handling & Logging**
    - Log errors and warnings when JSON parsing fails, files are missing, metadata conflicts occur, or other failures occur.
    - Use exit codes `0` (if no errors/warnings) or `1` otherwise.

## **Iterative Chunks & Steps**

Below is an iterative breakdown of the work. Each chunk builds on the previous one and ends with wiring things together:

### **Chunk 1: Project Initialization and Scaffolding**

- Create the Git repository.
- Set up the directory structure:
    - `src/` for source files.
    - `tests/` for unit and integration tests.
    - `config/` for configuration/settings (if needed).
    - Root-level files: `README.md`, `requirements.txt`, `.gitignore`.
- Create placeholder files for `src/main.py`, `src/logger.py`, etc.

### **Chunk 2: Dependency Management**

- Create a `requirements.txt` listing `piexif` and `pytest` (and possibly any future dependencies).
- Ensure that the project installs dependencies correctly.

### **Chunk 3: Logger Module**

- Write `src/logger.py` to create a `Logger` class that writes messages to a log file and, in verbose mode, echoes to the console.
- Create simple unit tests (in `tests/test_logger.py`).

### **Chunk 4: Metadata Parser Module**

- Build `src/metadata_parser.py` that walks through the input directory, identifies JSON metadata files (using naming conventions), and extracts required fields.
- Write tests to ensure correct parsing and handling of invalid JSON.

### **Chunk 5: Image Updater Module**

- Develop `src/image_updater.py`:
    - Use the `piexif` library to load current EXIF data from images.
    - Embed new EXIF metadata taken from the JSON.
    - Ensure that if there’s conflicting metadata, the existing image metadata is preserved.
    - Handle file I/O errors gracefully.
- Write tests (in `tests/test_image_updater.py`) with sample images.

### **Chunk 6: Sanity Checker Module**

- Create `src/sanity_checker.py` to:
    - Walk through the input directory.
    - Identify matching pairs based on the photo ID embedded in file names.
    - Log warnings for any orphan metadata files, images without metadata, or multiple matches.
- Write tests to cover these cases.

### **Chunk 7: Main CLI Module**

- Implement `src/main.py`:
    - Set up command-line argument parsing using `argparse`.
    - Wire together the modules:
        - If `-sanity-check` is provided, run the sanity check.
        - Otherwise, run the metadata extraction and then perform image updates.
    - Integrate logging throughout.

### **Chunk 8: Integration Testing & Final Wiring**

- Write integration tests invoking the full flow (from metadata parsing, to updating images, and sanity checks) using test directories with dummy data.
- Validate that proper exit codes are returned and logging occurs as expected.
- Ensure that unit tests for individual modules are passing.

### **Chunk 9: Final Review and Documentation**

- Update `README.md` with project overview, setup instructions, and usage examples.
- Finalize unit tests, integration tests, and prepare the project for further extension.
- Commit changes with well-written messages.

## **Series of LLM Prompts**

Each prompt is separated by a markdown code block tagged as `text`.

### **Prompt 1: Project Initialization & Scaffolding**

text

```
Prompt 1:
"Initialize the project repository. Create the following directory structure:

metadata_embedder/
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── logger.py
│   ├── metadata_parser.py
│   ├── image_updater.py
│   └── sanity_checker.py
├── tests/
│   ├── __init__.py
│   ├── test_logger.py
│   ├── test_metadata_parser.py
│   ├── test_image_updater.py
│   └── test_sanity_checker.py
├── config/
│   └── settings.py
├── README.md
├── requirements.txt
└── .gitignore

Please output the scaffold as a series of empty files and basic placeholders (e.g., file headers or TODO comments). Ensure that this initial scaffold is well-organized and ready for further development. Also, include a basic message in README.md describing the project purpose."

```

### **Prompt 2: Setting Up** `requirements.txt`

text

```
Prompt 2:
"Create the 'requirements.txt' file for the project. This file should list:
- piexif (for EXIF metadata handling)
- pytest (for testing)

Include version specifiers that are reasonable (for example, piexif>=1.1.3 and pytest>=7.0.0). Output the content of the 'requirements.txt' file."

```

### **Prompt 3: Implementing the Logger Module**

text

```
Prompt 3:
"Implement the Logger module in 'src/logger.py'. Create a Logger class that:
- Initializes with an output directory and a verbose flag.
- Writes log messages to a file named 'metadata_processing.log' in the output directory.
- Prints error and warning messages to the console; if verbose mode is enabled, also print informational messages.
Include basic error handling for file writes. Provide the full code for logger.py."

```

### **Prompt 4: Implementing the Metadata Parser Module**

text

```
Prompt 4:
"Develop the metadata extraction module in 'src/metadata_parser.py'. This module should have a function (e.g., extract_metadata) that:
- Walks through a given input directory.
- Identifies JSON files whose names start with 'photo_' and end with '.json'.
- Parses each JSON file and extracts the photo 'id', 'date_taken', and 'geolocation'.
- Constructs and returns a dictionary mapping each photo ID to its metadata.
Ensure that the module logs any parsing errors using the Logger. Provide the full code implementation for metadata_parser.py."

```

### **Prompt 5: Implementing the Image Updater Module**

text

```
Prompt 5:
"Develop the image updater module in 'src/image_updater.py'. This module should:
- Provide a function (e.g., embed_metadata) that receives the input directory, output directory, a metadata dictionary (from the metadata_parser), and an 'overwrite' flag.
- Search through the input directory (specifically in subdirectories whose names start with 'data-download-') for image files that contain a photo ID (embedded in the filename).
- Use the 'piexif' library to load the image's EXIF data, update the DateTimeOriginal and GPS fields (if provided), and then write the modified EXIF back into the image.
- Preserve existing metadata if there is a conflict, and log a warning in such cases.
- Handle image I/O and EXIF rewriting errors gracefully.
Provide the complete code for image_updater.py."

```

### **Prompt 6: Implementing the Sanity Checker Module**

text

```
Prompt 6:
"Develop the sanity checker module in 'src/sanity_checker.py'. This module should:
- Walk through the input directory.
- Identify metadata files and locate corresponding image files based on the photo ID in the filename.
- Log a warning if a JSON metadata file does not have a matching image, if an image lacks corresponding metadata, or if multiple images match one metadata file.
- At the end, log a summary: the number of matching photo-metadata pairs, the number of orphan photos, and the number of orphan metadata files.
Provide the complete code for sanity_checker.py."

```

### **Prompt 7: Building the Main CLI Module and Wiring Everything Together**

text

```
Prompt 7:
"Implement the main command-line interface in 'src/main.py'. This file should:
- Use the 'argparse' library to parse command-line arguments: --input-dir, --output-dir, --overwrite, --sanity-check, and --verbose.
- Initialize the Logger with the provided output directory and verbose flag.
- If the --sanity-check flag is set, call the sanity_checker module to perform the validation and then exit.
- Otherwise, call the metadata_parser to extract metadata and then call the image_updater to embed the EXIF metadata into the images.
- Ensure that all modules interoperate correctly and that appropriate logging is performed.
Provide the complete code for main.py that wires all the modules together."

```

### **Prompt 8: Writing Integration Tests**

text

```
Prompt 8:
"Develop a few integration tests in the 'tests/' folder that simulate the full project flow. For example:
- Create dummy test directories with sample JSON metadata files and dummy image files.
- Test that running the main script with valid arguments updates image files correctly.
- Test that running the script with the --sanity-check flag logs the appropriate warnings for missing or orphan files.
Provide example code in, for instance, 'tests/test_integration.py' that demonstrates running the full process and verifies the expected log outputs and file modifications."

```

### **Prompt 9: Final Review, Documentation, and Wiring Finalization**

text

```
Prompt 9:
"Finalize the project integration by updating the README.md with clear instructions on:
- Project purpose
- Installation (including dependency installation via 'pip install -r requirements.txt')
- Usage examples (how to run the script in standard and sanity-check modes)
- Testing instructions (how to run the tests)
Also, ensure that every module (logger, metadata_parser, image_updater, sanity_checker, and main) is integrated and that there are no orphan pieces of code. Provide the final version of the README.md and a brief summary of how the modules interconnect."

```