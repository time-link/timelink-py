"""SQLite database utilities for Timelink.

This module provides utility functions for working with SQLite databases,
including methods to search for SQLite files in a directory and construct
SQLAlchemy connection URLs for SQLite files.

Functions:
    get_sqlite_databases(directory_path: str, relative_path: bool = True) -> list[str]:
        Search for and list SQLite databases in a specified directory.

    get_sqlite_url(db_path: str) -> str:
        Construct an SQLAlchemy SQLite connection URL for a given file path.
"""
import os


def get_sqlite_databases(directory_path: str, relative_path=True) -> list[str]:
    """Search for and list SQLite database files in a directory.

    Walks through the directory tree starting from the specified path and
    identifies files with .sqlite or .db extensions.

    Args:
        directory_path (str): Directory path to search for SQLite databases.
        relative_path (bool, optional): If True, returns paths relative to the
            current working directory. If False, returns absolute paths.
            Defaults to True.

    Returns:
        list[str]: List of SQLite database file paths.
    """
    cd = os.getcwd()
    sqlite_databases = []
    for root, _dirs, files in os.walk(directory_path):
        for file_name in files:
            if file_name.endswith(".sqlite") or file_name.endswith(".db"):
                db_path = os.path.join(root, file_name)
                # path relative to cd
                if relative_path:
                    db_path = os.path.relpath(db_path, cd)
                sqlite_databases.append(db_path)
    return sqlite_databases


def get_sqlite_url(db_path: str) -> str:
    """Construct an SQLAlchemy SQLite connection URL for a given file path.

    Args:
        db_path (str): Database file path. Use ":memory:" for in-memory database.

    Returns:
        str: SQLite connection URL in SQLAlchemy format.
            - For in-memory: "sqlite:///:memory:"
            - For file: "sqlite:///path/to/file.db"
    """
    if db_path == ":memory:":
        return "sqlite:///:memory:"
    return f"sqlite:///{db_path}"
