# Changelog

## [Unreleased]

## [0.3.1] - 2025-07-24

### Fixed

- The required `input_schema.json` and `template.html.jinja` are now correctly packaged.

## [0.3.0] - 2025-07-23

### Added

**User-facing features:**

- Absolute node positioning with `absoluteX` and `absoluteY` properties for precise chart control
- `c` key shortcut to copy current node labels to clipboard
- Enhanced chart titles with floating display for better visual hierarchy
- Improved chart dimension enforcement with automatic boundary calculation

**Developer improvements:**

- Deep Pydantic integration with comprehensive type annotations and schema validation
- Modular code structure with new `chart_internals.py` and `css.py` modules

### Changed

**User-facing changes:**

- **BREAKING:** Attribute names must now be valid CSS identifiers
- Chart titles (`header/metadata/displaytitle`) now render directly in charts
- Example JSON files renamed for clarity (`example4.json` → `curves.json`, etc.)

**Developer changes:**

- Complete internal refactoring from monolithic `main.py` to modular architecture
- Replaced manual JSON parsing with robust Pydantic models for type safety
- Enhanced CSS generation using custom properties for better maintainability
- Updated template to minimize boilerplate generation at runtime
- Switched to `uv` instead of Poetry for virtual environment management
- Switched to flake-based development environment instead of `devenv`

## [0.2.0] - 2025-04-17

### Added

- [[#4]][issue-4] New color customization options in JSON schema:
  - `backgroundColor`: Controls chart background color (defaults to "white")
  - `borderColor`: Controls border color (defaults to "black")
  - `textColor`: Controls text and label colors (defaults to "black")
- Dark theme example (`json/example6.json`) demonstrating the new color customization features
- Added changelog

### Fixed

- Updated `path-data-polyfill` to 1.0.9. Fixes [[#5]][issue-5].

[issue-4]: <https://github.com/JoeyBF/SeqSee/issues/4>
[issue-5]: <https://github.com/JoeyBF/SeqSee/issues/5>

## [0.1.1] - 2025-01-21

### Fixed

- Fix behavior when overriding defaults

## [0.1.0] - 2025-01-21

Initial release!
