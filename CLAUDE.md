# CLAUDE.md

## Workflow Requirements

**MANDATORY**: Before ANY implementation work, invoke the appropriate skill:

- **New features/functionality** → `/brainstorming` FIRST, then implementation
- **Bug fixes/failures** → `/systematic-debugging` BEFORE proposing fixes
- **Writing code** → `/test-driven-development` BEFORE implementation
- **Multi-step tasks** → `/writing-plans` BEFORE touching code
- **Executing plans** → `/executing-plans` OR `/subagent-driven-development`
- **Task completion** → `/verification-before-completion` BEFORE claiming done
- **Code review needed** → `/requesting-code-review` when work is complete

**Rule**: If there's even 1% chance a skill applies, invoke it. No exceptions.

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

### Using Poe the Poet (Recommended)
```bash
poe install              # Install dependencies
poe dev-setup           # Complete development setup
poe test                # Run all tests
poe test-verbose        # Run tests with verbose output
poe run                 # Run application (requires --input-dir and --output-dir args)
poe run-example         # Example run command (modify paths as needed)
poe clean               # Clean __pycache__ directories
poe help                # Show all available tasks
```

### Direct Commands (Alternative)

#### Testing
```bash
pytest                    # Run all tests
pytest tests/test_specific_module.py  # Run specific test file
```

#### Running the Application
```bash
python -m src.main --input-dir /path/to/flickr/export --output-dir /path/to/output
python -m src.main --input-dir /path/to/flickr/export --output-dir /path/to/output --overwrite
python -m src.main --input-dir /path/to/flickr/export --sanity-check --verbose
python -m src.main --input-dir /path/to/flickr/export --dry-run --verbose
python -m src.main --input-dir /path/to/flickr/export --output-dir /path/to/output --resume
python -m src.main --input-dir /path/to/flickr/export --output-dir /path/to/output --fields title,date,license
```

#### Development Setup
```bash
pip install -r requirements.txt
```

## Architecture Overview

FlickrMetadataEmbedder is a CLI tool that processes Flickr export data to embed EXIF/IPTC/XMP metadata into images. The architecture follows a linear data processing pipeline with Pydantic validation, O(n) file matching, and rich progress output.

**Data Flow**: `file_scanner` → `metadata_parser` → `metadata_mapper` → `image_writer`

### Core Modules

- **main.py**: CLI orchestration with rich progress bars, resume support, field filtering, --dry-run, --strict mode
- **models.py**: Pydantic models — FlickrPhoto, GeoLocation, MetadataTags, ProcessingResult, PhotoFilePair
- **file_scanner.py**: Single-pass O(n) directory walk building {photo_id → Path} indexes, then dict-lookup matching
- **metadata_parser.py**: Parses Flickr JSON into FlickrPhoto Pydantic models (all fields, not just date+GPS)
- **tag_definitions.py**: Pure constants mapping Flickr fields → pyexiv2 EXIF/IPTC/XMP tag names
- **metadata_mapper.py**: Converts FlickrPhoto → MetadataTags using tag_definitions, with field filtering support
- **image_writer.py**: pyexiv2 wrapper writing EXIF/IPTC/XMP with preserve-existing and copy-then-modify safety
- **gps_converter.py**: GPS coordinate math (decimal ↔ DMS ↔ rational string). Legacy piexif functions kept for tests.
- **state_manager.py**: Resume/checkpoint tracking via JSON state file with batch-save every 50 photos
- **sanity_checker.py**: Validates JSON-to-image matching using file_scanner, outputs rich table
- **logger.py**: stdlib logging + rich console handler (replaces old file-open-per-message Logger class)

### Metadata Fields Embedded

| Flickr JSON field | EXIF | IPTC | XMP |
|---|---|---|---|
| `name` | ImageDescription | ObjectName | dc:title |
| `description` | UserComment | Caption | dc:description |
| `date_taken` | DateTimeOriginal | DateCreated + TimeCreated | photoshop:DateCreated |
| `tags[*].tag` | — | Keywords | dc:subject |
| `license` | — | Copyright | dc:rights |
| `rotation` | Orientation | — | — |
| `albums[*].title` | — | SuppCategory | lr:hierarchicalSubject |
| `geo` (lat/lon) | GPSInfo | — | — |

### Key Patterns

**File Matching**: Single-pass `os.walk()` builds `{photo_id → Path}` dicts for JSONs and images, then O(n) dict-lookup matching (replaces old O(n*m) substring search)

**Error Handling**: Non-fatal by default — logs errors, continues processing. `--strict` stops on first error.

**Logging**: stdlib `logging` + `rich.logging.RichHandler` for console, `FileHandler` for audit trail

**Resumability**: State file (`.flickr_embed_state.json`) tracks processed photo_ids. `--resume` skips already-processed, `--force` reprocesses all.

**Configuration**: CLI-driven with `--fields`/`--skip-fields` for selective embedding

## Testing Structure

Tests use pytest framework with one test file per module (`test_<module_name>.py`). GPS converter tests (20+ tests) are comprehensive and passing. Other test files need updating for the new API (old tests tested the piexif-based API).

## Dependencies

- **pyexiv2**: EXIF/IPTC/XMP metadata read/write (replaces piexif)
- **piexif**: Legacy — kept until GPS converter tests are migrated
- **pydantic**: Data validation for Flickr JSON parsing
- **rich**: Progress bars and console logging
- **pytest**: Testing framework
- **poethepoet**: Task runner

## Coding standards

*   **Python**: 3.12+, FastAPI, `async/await` preferred.
*   **Formatting**: `ruff` enforces 96-char lines, double quotes, sorted imports. Standard `ruff` linter rules.
*   **Typing**: Strict (Pydantic v2 models preferred); `from __future__ import annotations`.
*   **Naming**: `snake_case` (functions/variables), `PascalCase` (classes), `SCREAMING_SNAKE` (constants). Always use descriptive variable names.
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
