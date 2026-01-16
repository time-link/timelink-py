# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Timelink is a Python package (version 1.1.26) for managing person-related information collected from historical sources. Formerly known as MHK (Micro History with Kleio), it provides a comprehensive information system with database management, API services, and data processing capabilities.

## Development Environment

### Git Worktree Workflow
This repository uses Git Worktree for managing multiple branches simultaneously:

```bash
# List active worktrees
git worktree list

# Create new feature branch
git worktree add feature-new-ui -b feature/new-ui

# Work on existing branch
git worktree add hotfix-123 hotfix/issue-123

# Remove finished worktree
git worktree remove feature-new-ui
```

### Python Requirements
- **Python Version**: 3.10+, explicitly requires Python >=3.10
- **Current Environment**: Python 3.13.1 (from pyenv)

### Common Development Commands

#### Testing
```bash
# Run all tests
make test

# Run tests on all Python versions
tox

# Run specific test file
pytest tests/test_mhk_utilities.py

# Test notebooks
make test-nb

# Run tests with coverage
make coverage

# Profile tests
make profile
```

#### Code Quality
```bash
# Format code with Black
black timelink

# Lint with flake8
make lint

# Clean artifacts
make clean
```

**Linter and Formatter Configuration:**

- **flake8** (Primary Linter)
  - Configuration: `setup.cfg`
  - Max line length: 120 characters
  - Selected checks: C, E, F, W, B, B950
  - Ignores: E203, E501
  - Command: `make lint` or `flake8 timelink tests`
  
- **Black** (Code Formatter)
  - Configuration: `pyproject.toml`
  - Line length: 120 characters
  - Excludes `__init__.py` (prevents breaking bump2version)
  - Command: `black timelink`
  
- **Tox** includes flake8 in test suite (`tox.ini`)

#### Building and Documentation
```bash
# Generate documentation
make docs

# Build distribution packages
make dist

# Create release (deploys to PyPI via GitHub Actions)
make release
```

#### Application Commands
```bash
# Start web application
make install
timelink start

# Start directly with uvicorn
uvicorn timelink.app.main:app --reload --port 8008
```

## Architecture Overview

### Package Structure

```
timelink/
├── api/                 # Database API and ORM models
│   ├── models.py       # SQLAlchemy database models
│   ├── schemas.py      # Pydantic schemas for API
│   ├── crud.py         # CRUD operations
│   └── database.py     # Database connection logic
├── app/                # Web application (FastAPI)
│   ├── main.py         # Main FastAPI application
│   └── dependencies.py # FastAPI dependencies
├── kleio/              # Kleio data format integration
│   ├── kleio_server.py # Kleio Server API integration
│   └── importer.py     # Data import functionality
├── mhk/                # Legacy MHK compatibility
├── migrations/         # Alembic migration scripts
├── networks/           # Network/graph utilities
└── pandas/             # Pandas integration
```

### Key Technologies

- **Web Framework**: FastAPI with Pydantic for validation
- **Database**: SQLAlchemy 2.0+ multi-database support (PostgreSQL, SQLite, MySQL)
- **ORM**: SQLAlchemy models in `timelink/api/models.py`
- **API Layer**: FastAPI routes with dependency injection
- **CLI**: Typer-based command-line interface
- **Authentication**: JWT tokens (python-jose)
- **External Services**: Kleio Server integration (Prolog-based)

### Testing Strategy

**Test Organization:**
- `test_010_*.py` - API model database tests
- `test_040_*.py` - Pandas integration tests
- `test_100_*.py` - Kleio server integration tests
- `test_800_*.py` - Legacy MHK tests
- `test_999_*.py` - PostgreSQL specific tests

**Multi-Database Testing:**
- Tests run against PostgreSQL and SQLite
- PostgreSQL preferred for development
- SQLite for lightweight testing

**Kleio Server Testing Modes:**
1. **Docker Mode**: Spin up Kleio server in Docker
2. **Local Mode**: Use installed Kleio server

### Database Models

Core models in `timelink/api/models.py`:
- **Entity**: Core data entities (person, object, etc.)
- **Attribute**: Entity attributes
- **Relation**: Relationships between entities
- **Act**: Historical acts/actions
- **File**: Source file tracking

### API Patterns

**FastAPI Structure:**
- **Routes**: Defined in `timelink/app/main.py`
- **Schemas**: Pydantic models in `timelink/api/schemas.py`
- **CRUD**: Generic CRUD operations in `timelink/api/crud.py`
- **Dependencies**: Global dependencies in `timelink/app/dependencies.py`

**Common Patterns:**
- Session-scoped database fixtures
- Dependency injection for database sessions
- Pydantic models for request/response validation
- SQLAlchemy for ORM operations

### Development Notes

**Branch Management:**
- Use `feature/`, `bugfix/`, `hotfix/`, `release/`, `chore/` prefixes
- Rebase feature branches regularly against `main`
- Delete merged branches
- Never push directly to `main`

**Code Style:**
- Google-style docstrings
- Black formatting (120 char line length)
- flake8 with bugbear extension (120 char line length)
- Type hints encouraged

**Database Migrations:**
- Alembic migrations in `timelink/migrations/versions/`
- Run `alembic upgrade head` to migrate
- Test migrations on non-production data first

**Release Process:**
1. Update `HISTORY.rst` with changes
2. Run full test suite: `make test-all`
3. Update version with `bump2version`
4. Push with tags: `git push && git push --tags`
5. GitHub Actions handles PyPI deployment

## Git Integration Notes

- Repository uses **Git Worktree Workflow**
- Main development branch: `main`
- Current branch: `main` (clean working directory)
- Recent commits show branch management improvements
- No Credentials: Never include API keys or tokens in code

## Resources

- **Documentation**: https://timelink-py.readthedocs.io/
- **Repository**: https://github.com/time-link/timelink-py
- **PyPI**: Distributed via PyPI (GitHub Actions deployment)
- **Issue Tracker**: GitHub Issues
- **CI/CD**: GitHub Actions (configured in `.github/workflows/ci.yml`)