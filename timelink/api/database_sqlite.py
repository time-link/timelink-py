"""
This module provides utility functions for working with SQLite databases.

Functions:
    get_sqlite_databases(directory_path: str, relative_path=True) -> list[str]:
        Get the SQLite databases in a specified directory.

    get_sqlite_url(db_path: str) -> str:
        Get the SQLite URL for a given database path.
"""
import os


def get_sqlite_databases(directory_path: str, relative_path=True) -> list[str]:
    """Get the sqlite databases in a directory
    Args:
        directory_path (str): directory path
    Returns:
        list[str]: list of sqlite databases
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
    """Get the sqlite url for a database path
    Args:
        db_path (str): database path
    Returns:
        str: sqlite url
    """
    if db_path == ":memory:":
        return "sqlite:///:memory:"
    return f"sqlite:///{db_path}"
