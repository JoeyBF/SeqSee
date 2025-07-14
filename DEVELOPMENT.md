# Development Guide

This guide is for contributors and developers working on SeqSee.

## Development Environment

### Prerequisites

- **Python** 3.11+
- **uv** for fast dependency management
- **Nix** (optional, but recommended for reproducible environments)

### Setup Options

#### Option 1: Nix (Recommended)

This project includes a Nix flake for reproducible development environments:

0. **Install Nix:**

   ```bash
   curl -L https://nixos.org/nix/install | sh -s -- --daemon
   ```

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
   uv sync
   ```

#### Option 2: Manual setup

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
# Run the tools locally
uv run seqsee input.json output.html
uv run seqsee-jsonmaker input.csv output.json
uv run seqsee-convert-all

# Code quality
ruff check .                     # Linting
ruff format .                    # Formatting
basedpyright .                   # Type checking
# Note: ruff and basedpyright are included in the Nix flake. For manual setup, install them via your preferred package manager

# Build and publish
uv build                         # Build distribution packages
uv publish                       # Publish to PyPI
```

### Project Structure

```text
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
