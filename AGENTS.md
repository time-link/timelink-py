# Timelink Python Package - Agent Guide

This file provides essential information for AI coding agents working with the Timelink Python package codebase.

## Project Overview

**Timelink** is a Python package (version 1.1.30) for managing person-related information collected from historical sources. Formerly known as MHK (Micro History with Kleio), it provides a comprehensive information system for prosopography research with database management, API services, data processing, and web application capabilities.

- **Repository**: <https://github.com/time-link/timelink-py>
- **Documentation**: <https://timelink-py.readthedocs.io/>
- **PyPI**: <https://pypi.org/project/timelink/>
- **License**: MIT

## Technology Stack

- **Python**: 3.10+ (supports 3.10, 3.11, 3.12, 3.13)
- **Web Framework**: FastAPI with Pydantic for validation
- **Database ORM**: SQLAlchemy 2.0+
- **Database Support**: PostgreSQL (primary), SQLite, MySQL
- **Migrations**: Alembic
- **CLI**: Typer
- **Authentication**: JWT tokens (python-jose)
- **External Services**: Kleio Server integration (Prolog-based, via Docker)

## Project Structure

```bash
timelink/
├── api/                    # Database API and ORM models
│   ├── models/            # SQLAlchemy database models
│   │   ├── base_class.py  # SQLAlchemy Base class
│   │   ├── entity.py      # Entity model
│   │   ├── attribute.py   # Attribute model
│   │   ├── relation.py    # Relation model
│   │   ├── person.py      # Person entity
│   │   ├── object.py      # Object entity
│   │   ├── act.py         # Historical acts
│   │   ├── source.py      # Source tracking
│   │   └── ...
│   ├── database.py        # Main TimelinkDatabase class
│   ├── database_*.py      # Database mixins (postgres, sqlite, kleio, etc.)
│   ├── crud.py           # CRUD operations
│   ├── schemas.py        # Pydantic schemas for API
│   └── views.py          # Database views
├── app/                   # Web application (FastAPI)
│   ├── main.py           # Main FastAPI application with routes
│   ├── dependencies.py   # FastAPI dependencies (auth, db)
│   ├── backend/          # Backend services
│   ├── models/           # User, Project models
│   ├── schemas/          # Request/response schemas
│   ├── services/         # Auth, logging services
│   ├── web/              # Web page handlers
│   └── templates/        # Jinja2 templates
├── kleio/                # Kleio data format integration
│   ├── kleio_server.py   # Kleio Server API client
│   ├── importer.py       # Data import from XML
│   ├── groups/           # Kleio group classes
│   └── schemas.py        # Kleio-related schemas
├── mhk/                  # Legacy MHK compatibility layer
│   ├── models/           # Legacy ORM models
│   └── utilities.py      # MHK utilities
├── migrations/           # Alembic migration scripts
│   └── versions/         # Migration files
├── networks/             # Network/graph utilities
│   ├── network_generation.py
│   └── network_draw.py
├── pandas/               # Pandas integration
│   ├── attribute_values.py
│   ├── entities_with_attribute.py
│   └── group_attributes.py
├── notebooks/            # Jupyter notebook utilities
├── cli.py               # Typer-based CLI entry point
└── timelink.py          # Main module

tests/                   # Test suite
├── conftest.py         # pytest fixtures
├── test_010_*.py       # API model database tests
├── test_040_*.py       # Pandas integration tests
├── test_100_*.py       # Kleio server integration tests
├── test_800_*.py       # Legacy MHK tests
├── test_999_*.py       # PostgreSQL specific tests
└── timelink-home/      # Test fixtures and sample data

docs/                   # Sphinx documentation
├── *.rst              # Documentation source files
└── _build/            # Generated HTML docs
```

## Build and Development Commands

### Installation

```bash
# Install package in development mode
pip install -e .

# Install with dev dependencies
pip install -e ".[dev]"
```

### Testing

```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_010_api_models_db.py

# Run tests on all Python versions
tox

# Test notebooks
make test-nb

# Run tests with coverage
make coverage

# Profile tests
make profile
```

### Code Quality

```bash
# Format code with Black
black timelink

# Lint with flake8
make lint
# or: flake8 timelink tests

# Clean build artifacts
make clean
```

### Documentation

```bash
# Generate Sphinx documentation
make docs

# Serve docs with auto-rebuild
make servedocs
```

### Building and Release

```bash
# Build distribution packages
make dist

# Create release (manual, CI handles PyPI deployment)
make release
```

### Running the Application

```bash
# Start web application
make install
timelink start

# Or directly with uvicorn
uvicorn timelink.app.main:app --reload --port 8008

# CLI commands
timelink --help
timelink db list          # List databases
timelink db upgrade <url> # Run migrations
timelink mhk version      # Show MHK info
```

## Code Style Guidelines

### Formatting

- **Black**: Line length 120 characters (configured in `pyproject.toml`)
- **Exclude**: `__init__.py` files from Black (to avoid breaking bump2version)

### Linting

- **flake8** with bugbear extension
- Max line length: 120 characters
- Selected checks: C, E, F, W, B, B950
- Ignored: E203, E501, W503, W504

### Docstrings

- Use Google-style docstrings
- Include type hints where applicable

### Import Style

```python
# Standard library imports
import os
from typing import Annotated, List

# Third-party imports
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

# Local application imports
from timelink.api import models
from timelink.app.dependencies import get_db
```

## Testing Instructions

### Test Organization

Tests are prefixed with numbers to indicate test order and category:

- `test_010_*.py` - API model database tests
- `test_015_*.py` - API model tests (no database)
- `test_040_*.py` - Pandas integration tests
- `test_100_*.py` - Kleio server integration tests
- `test_800_*.py` - Legacy MHK compatibility tests
- `test_999_*.py` - PostgreSQL-specific tests

### Test Configuration

Key settings in `tests/__init__.py`:

```python
# Kleio server test mode
kleio_server_mode = KleioServerTestMode.DOCKER  # or LOCAL

# Docker image for Kleio server
use_kleio_image = "timelinkserver/kleio-server"
use_kleio_version = "latest"
```

### Database Testing

- Tests run against both PostgreSQL and SQLite
- PostgreSQL preferred for development testing
- SQLite for lightweight testing
- Connection strings configured in `tests/__init__.py`

### Skipping Tests

```python
# Skip on CI environments
from tests import skip_on_ci, skip_on_github_actions

@pytest.mark.skipif(not has_internet(), reason="No internet connection")
def test_network_feature():
    pass
```

## Database Migrations

Using Alembic for database migrations:

```bash
# Show current revision
timelink db current <db_url>

# Upgrade to latest
timelink db upgrade <db_url> heads

# Create new migration
timelink db revision <db_url> "description"

# Auto-generate from model changes
timelink db autogenerate <db_url> "description"

# Show migration history
timelink db history
```

Migration files are stored in `timelink/migrations/versions/`.

## Version Management

Using bump2version for version management:

```bash
# Bump patch version (1.1.30 -> 1.1.31)
bump2version patch

# Bump minor version (1.1.30 -> 1.2.0)
bump2version minor

# Bump major version (1.1.30 -> 2.0.0)
bump2version major
```

Version is stored in:

- `pyproject.toml` (primary)
- `timelink/__init__.py`
- `setup.cfg` (for bump2version config)

## CI/CD Pipeline

GitHub Actions workflow (`.github/workflows/ci.yml`):

1. **Lint Job**: Runs flake8 on Python 3.11
2. **Test Job**: Runs pytest on Python 3.10, 3.11, 3.12, 3.13 with PostgreSQL
3. **Deploy Job**: Publishes to PyPI on version tags (starts with 'v')

Environment variables for CI compatibility:

- `TRAVIS=true`
- `GITHUB_ACTIONS=true`

## Security Considerations

- **No credentials in code**: Never commit API keys, tokens, or passwords
- **JWT tokens**: Used for authentication, configured in `timelink/app/services/auth.py`
- **Database passwords**: Auto-generated or configured via environment variables
- **Admin password**: Set via `TIMELINK_ADMIN_PWD` environment variable

## Key Architectural Patterns

### Database Access Pattern

```python
from timelink.api.database import TimelinkDatabase

# Create database instance
db = TimelinkDatabase(db_url="postgresql://...")

# Use session context manager
with db.session() as session:
    result = session.query(Entity).first()
```

### FastAPI Dependency Injection

```python
from fastapi import Depends
from timelink.app.dependencies import get_db, get_current_user

@app.get("/items")
def get_items(db=Depends(get_db), user=Depends(get_current_user)):
    return db.query(Item).all()
```

### Model-Schema Separation

- **Models**: SQLAlchemy ORM classes in `timelink/api/models/`
- **Schemas**: Pydantic models in `timelink/api/schemas.py` for API validation

## External Dependencies

### Kleio Server

- Docker image: `timelinkserver/kleio-server:latest`
- Provides Prolog-based translation of historical data
- API exposed on port 8088 (default)

### PostgreSQL

- Primary database for production
- Docker support built-in for development

## Common Development Tasks

### Adding a New Model

1. Create model class in `timelink/api/models/`
2. Import in `timelink/api/models/__init__.py`
3. Create Pydantic schema in `timelink/api/schemas.py`
4. Create Alembic migration: `timelink db autogenerate <url> "add new model"`
5. Add tests in appropriate `test_*.py` file

### Adding a New API Endpoint

1. Add route in `timelink/app/main.py`
2. Use appropriate dependencies (`get_db`, `get_current_user`)
3. Define request/response schemas if needed
4. Add tests

### Running Kleio Server Locally for Debugging

```python
# In tests/__init__.py
kleio_server_mode = KleioServerTestMode.LOCAL
```

Then run the Prolog server with specific token and port for debugging.

## Resources

- **Documentation**: <https://timelink-py.readthedocs.io/>
- **Issue Tracker**: <https://github.com/time-link/timelink-py/issues>
- **Cookiecutter Template**: Based on `audreyr/cookiecutter-pypackage`
