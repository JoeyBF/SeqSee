# Development Guide

This guide is for contributors and developers working on SeqSee.

## Development Environment

### Prerequisites

This project uses the following tools for development:

- **Python** 3.11+
- **uv** for fast dependency management
- **ruff** for linting and formatting
- **basedpyright** for type checking
- **Nix** (optional, but recommended for reproducible environments)

The setup options below provide guidance on installing and configuring these tools.

### Setup Options

The development environment can be set up in a few ways. For convenience, we provide a Nix flake
that bundles an appropriate version of Python, together with uv, ruff and basedpyright. See the
[instructions](#option-1-nix-recommended).

It is also possible to install these tools manually. We assume that Python is already installed
system-wide. We provide instructions on how to install uv on Linux or MacOS; ruff and basedpyright
can be installed using your preferred package manager. See the
[instructions](#option-2-manual-setup).

Note that Nix does not support Windows. For development on Windows, we recommend working through
WSL2, the Windows Subsystem for Linux. Otherwise, it is possible to install Python and uv directly,
although this is untested.

#### Option 1: Nix (Recommended)

0. **Install Nix and enable flakes:**

   ```bash
   curl -L https://nixos.org/nix/install | sh -s -- --daemon
   mkdir -p ~/.config/nix
   echo "experimental-features = nix-command flakes" >> ~/.config/nix/nix.conf
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

   For convenience, we recommend installing direnv to automatically activate the development
   environment when entering the project directory. If installed, simply run:

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

We assume that an appropriate version of Python (3.11+) is already installed system-wide.

1. **Install uv** (if not already installed):

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Clone and setup:**

   ```bash
   git clone https://github.com/JoeyBF/SeqSee.git
   cd SeqSee
   uv sync
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
# Note: ruff and basedpyright are included in the Nix flake. For manual setup,
# install them via your preferred package manager

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
