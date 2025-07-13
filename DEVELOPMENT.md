# Development Guide

This guide is for contributors and developers working on SeqSee.

## Development Environment

### Prerequisites

- **Python** 3.11+
- **uv** for fast dependency management
- **Nix** (optional, but recommended for reproducible environments)

### Setup Options

#### Option 1: NixOS/Nix Users (Recommended)

This project includes a Nix flake for reproducible development environments:

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/JoeyBF/SeqSee.git
   cd SeqSee
   ```

2. **Enter the development shell:**

   ```bash
   nix develop
   ```

   Or with direnv (if you have `.envrc` configured):

   ```bash
   direnv allow
   ```

   The flake provides:
   - Python 3.11 with essential build tools
   - uv for fast package management
   - ruff for linting and formatting
   - pyright for type checking

3. **Install dependencies:**

   ```bash
   uv sync --extra dev
   ```

#### Option 2: Other Systems

1. **Install uv** (if not already installed):

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Clone and setup:**

   ```bash
   git clone https://github.com/JoeyBF/SeqSee.git
   cd SeqSee
   uv sync --extra dev
   ```

### Development Commands

```bash
# Install all dependencies including dev tools
uv sync --extra dev

# Run the tools locally
uv run seqsee input.json output.html
uv run seqsee-jsonmaker input.csv output.json
uv run seqsee-convert-all

# Code quality
uv run ruff check .              # Linting
uv run ruff format .             # Formatting
uv run mypy seqsee/              # Type checking

# Build and test
uv build                         # Build distribution packages
uv run python -m pytest         # Run tests (when available)

# Publishing
uv publish                       # Publish to PyPI
```

### Project Structure

```
SeqSee/
├── flake.nix              # Nix development environment
├── pyproject.toml         # Project configuration and dependencies
├── README.md              # User documentation
├── DEVELOPMENT.md         # This file
├── seqsee/                # Main package
│   ├── __init__.py
│   ├── main.py            # seqsee command
│   ├── jsonmaker.py       # seqsee-jsonmaker command
│   ├── convert_all.py     # seqsee-convert-all command
│   └── ...
├── csv/                   # Example CSV files
├── json/                  # Generated JSON files
└── html/                  # Generated HTML files
```

### Package Management

This project uses:
- **uv** for dependency management (replaces Poetry)
- **Standard Python packaging** (PEP 621) in `pyproject.toml`
- **setuptools** as the build backend

### Key Dependencies

- **jinja2**: HTML template rendering
- **pandas**: CSV data processing
- **jsonschema**: JSON validation
- **pydantic**: Data validation and parsing
- **compact-json**: Compact JSON output

### Development Dependencies

- **ruff**: Fast linting and formatting
- **mypy**: Static type checking
- **types-jsonschema**: Type stubs for jsonschema

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run the code quality checks
5. Submit a pull request

### Nix Flake Details

The `flake.nix` provides:
- Isolated development environment
- Consistent Python version (3.11)
- All necessary development tools
- Automatic virtual environment setup
- Integration with direnv for seamless workflow

The flake automatically:
- Sets up uv with the correct Python interpreter
- Creates a `.venv` directory if it doesn't exist
- Activates the virtual environment
- Provides helpful shell hints