"""SQLAlchemy View Support for Timelink.

This module provides utilities for defining and managing SQL views in SQLAlchemy,
enabling views to be treated as tables for querying purposes. It includes
DDL elements for creating and dropping views across different database dialects
(PostgreSQL and SQLite) and event listeners to automate view lifecycle management.

Based on: https://github.com/sqlalchemy/sqlalchemy/wiki/Views
"""

import sqlalchemy as sa
from sqlalchemy.ext import compiler
from sqlalchemy.schema import DDLElement


class CreateView(DDLElement):
    """DDL element for creating a database view.

    Args:
        name (str): The name of the view to create.
        selectable (Select): The SQLAlchemy select statement that defines the view.
    """
    def __init__(self, name, selectable):
        self.name = name
        self.selectable = selectable


class DropView(DDLElement):
    """DDL element for dropping a database view.

    Args:
        name (str): The name of the view to drop.
    """
    def __init__(self, name):
        self.name = name


@compiler.compiles(CreateView)
def _create_view(element, compiler, **kw):
    """Compile the CREATE VIEW statement."""
    return "CREATE VIEW %s AS %s" % (
        element.name,
        compiler.sql_compiler.process(element.selectable, literal_binds=True),
    )


@compiler.compiles(DropView)
def _drop_view(element, compiler, **kw):
    """Compile the DROP VIEW statement with dialect-specific logic."""
    if compiler.dialect.name == "sqlite":
        return "DROP VIEW %s" % (element.name)
    elif compiler.dialect.name == "postgresql":
        return "DROP VIEW IF EXISTS %s CASCADE" % (element.name)


def view_exists(ddl, target, connection, **kw):
    """Check if a view exists in the database.

    Used as a condition for conditional DDL execution.
    """
    return ddl.name in sa.inspect(connection).get_view_names()


def view_doesnt_exist(ddl, target, connection, **kw):
    """Check if a view does not exist in the database."""
    return not view_exists(ddl, target, connection, **kw)


def view(name, metadata, selectable):
    """Define a view and register its creation/drop events with MetaData.

    This function creates a Table object that represents the view, allowing
    it to be used in SQLAlchemy queries just like a regular table. It also
    registers listeners to automatically create the view after tables are created
    and drop it before tables are dropped.

    Args:
        name (str): The name of the view.
        metadata (MetaData): The SQLAlchemy MetaData object to register events with.
        selectable (Select): The select statement defining the view's content.

    Returns:
        Table: A SQLAlchemy Table object representing the view.
    """

    t = sa.table(
        name,
        *(
            sa.Column(c.name, c.type, primary_key=c.primary_key)
            for c in selectable.selected_columns
        ),
    )
    t.primary_key.update(c for c in t.c if c.primary_key)

    sa.event.listen(
        metadata,
        "after_create",
        CreateView(name, selectable).execute_if(callable_=view_doesnt_exist),
    )
    sa.event.listen(
        metadata,
        "before_drop",
        DropView(name).execute_if(callable_=view_exists),
    )
    return t
