# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Non-negotiable golden rules

| #: | AI *may* do                                                            | AI *must NOT* do                                                                    |
|---|------------------------------------------------------------------------|-------------------------------------------------------------------------------------|
| G-0 | Whenever unsure about something that's related to the project, ask the developer for clarification before making changes.   |  ❌ Write changes or use tools when you are not sure about something project specific, or if you don't have context for a particular feature/decision. |
| G-1 | Generate code **only inside** relevant source directories or explicitly pointed files.    | ❌ Touch `tests/`, `SPEC.md`, or any `*_spec.py` / `*.ward` files (humans own tests & specs). |
| G-2 | Add/update **`AIDEV-NOTE:` anchor comments** near non-trivial edited code. | ❌ Delete or mangle existing `AIDEV-` comments.                                     |
| G-3 | Follow lint/style configs (`pyproject.toml`, `.ruff.toml`, `.pre-commit-config.yaml`). Use the project's configured linter, if available, instead of manually re-formatting code. | ❌ Re-format code to any other style.                                               |
| G-4 | For changes >300 LOC or >3 files, **ask for confirmation**.            | ❌ Refactor large modules without human guidance.                                     |
| G-5 | Stay within the current task context. Inform the dev if it'd be better to start afresh.                                 | ❌ Continue work from a prior prompt after "new task" – start a fresh session.      |

---

## Common Commands

### Testing
```bash
pytest                    # Run all tests
pytest tests/test_specific_module.py  # Run specific test file
```

### Running the Application
```bash
python -m src.main --input-dir /path/to/flickr/export --output-dir /path/to/output
python -m src.main --input-dir /path/to/flickr/export --output-dir /path/to/output --overwrite
python -m src.main --input-dir /path/to/flickr/export --output-dir /path/to/output --sanity-check --verbose
```

### Development Setup
```bash
pip install -r requirements.txt
```

## Architecture Overview

FlickrMetadataEmbedder is a CLI tool that processes Flickr export data to embed EXIF metadata into images. The architecture follows a linear data processing pipeline:

**Data Flow**: Flickr Export → Metadata Parser → Image Updater → Output Directory

### Core Modules

- **main.py**: CLI orchestration and argument parsing
- **metadata_parser.py**: Extracts metadata from Flickr JSON files, returns dict mapping photo_id → {date_taken, geolocation}
- **image_updater.py**: Embeds metadata into image EXIF using piexif library
- **sanity_checker.py**: Validates matching between metadata files and images
- **logger.py**: Centralized logging with file output and configurable console verbosity

### Key Patterns

**File Processing**: Uses `os.walk()` for recursive traversal, matches JSON metadata files (prefixed with "photo_") to corresponding images by photo_id

**Error Handling**: Non-fatal approach - logs errors but continues processing remaining files

**Logging**: Dual output (file + console) with log files stored in output directory as `metadata_processing.log`

**Configuration**: CLI-driven with no external config files; all settings passed through function parameters

## Testing Structure

Tests use pytest framework with one test file per module (`test_<module_name>.py`). Note: Test files currently exist but are empty - test implementations need to be added.

## Dependencies

- **piexif**: EXIF metadata manipulation
- **pytest**: Testing framework
- Standard library: os, json, argparse

## Development Notes

The codebase uses functional programming patterns with standalone functions (except Logger class). The config/settings.py file exists but is empty, indicating configuration management could be enhanced.

## Coding standards

*   **Python**: 3.12+, FastAPI, `async/await` preferred.
*   **Formatting**: `ruff` enforces 96-char lines, double quotes, sorted imports. Standard `ruff` linter rules.
*   **Typing**: Strict (Pydantic v2 models preferred); `from __future__ import annotations`.
*   **Naming**: `snake_case` (functions/variables), `PascalCase` (classes), `SCREAMING_SNAKE` (constants).
*   **Error Handling**: Typed exceptions; context managers for resources.
*   **Documentation**: Google-style docstrings for public functions/classes.
*   **Testing**: Separate test files matching source file patterns.

## Anchor comments

Add specially formatted comments throughout the codebase, where appropriate, for yourself as inline knowledge that can be easily `grep`ped for. 

### Guidelines:

- Use `AIDEV-NOTE:`, `AIDEV-TODO:`, or `AIDEV-QUESTION:` (all-caps prefix) for comments aimed at AI and developers.
- Keep them concise (≤ 120 chars).
- **Important:** Before scanning files, always first try to **locate existing anchors** `AIDEV-*` in relevant subdirectories.
- **Update relevant anchors** when modifying associated code.
- **Do not remove `AIDEV-NOTE`s** without explicit human instruction.
- Make sure to add relevant anchor comments, whenever a file or piece of code is:
  * too long, or
  * too complex, or
  * very important, or
  * confusing, or
  * could have a bug unrelated to the task you are currently working on.

Example:
```python
# AIDEV-NOTE: perf-hot-path; avoid extra allocations (see ADR-24)
async def render_feed(...):
    ...
```

---

## 6. Commit discipline

*   **Granular commits**: One logical change per commit.
*   **Tag AI-generated commits**: e.g., `feat: optimise feed query [AI]`.
*   **Clear commit messages**: Explain the *why*; link to issues/ADRs if architectural.
*   **Use `git worktree`** for parallel/long-running AI branches (e.g., `git worktree add ../wip-foo -b wip-foo`).
*   **Review AI-generated code**: Never merge code you don't understand.

---

## AI Assistant Workflow: Step-by-Step Methodology

When responding to user instructions, the AI assistant (Claude, Cursor, GPT, etc.) should follow this process to ensure clarity, correctness, and maintainability:

1. **Consult Relevant Guidance**: When the user gives an instruction, consult the relevant instructions from `CLAUDE.md` files (both root and directory-specific) for the request.
2. **Clarify Ambiguities**: Based on what you could gather, see if there's any need for clarifications. If so, ask the user targeted questions before proceeding.
3. **Break Down & Plan**: Break down the task at hand and chalk out a rough plan for carrying it out, referencing project conventions and best practices.
4. **Trivial Tasks**: If the plan/request is trivial, go ahead and get started immediately.
5. **Non-Trivial Tasks**: Otherwise, present the plan to the user for review and iterate based on their feedback.
6. **Track Progress**: Use a to-do list (internally, or optionally in a `TODOS.md` file) to keep track of your progress on multi-step or complex tasks.
7. **If Stuck, Re-plan**: If you get stuck or blocked, return to step 3 to re-evaluate and adjust your plan.
8. **Update Documentation**: Once the user's request is fulfilled, update relevant anchor comments (`AIDEV-NOTE`, etc.) and `CLAUDE.md` files in the files and directories you touched.
9. **User Review**: After completing the task, ask the user to review what you've done, and repeat the process as needed.
10. **Session Boundaries**: If the user's request isn't directly related to the current context and can be safely started in a fresh session, suggest starting from scratch to avoid context confusion.
