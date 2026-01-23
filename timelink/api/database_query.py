"""Database Query Mixin for Timelink.

This module provides the DatabaseQueryMixin class, which contains high-level
methods for data access, selection, and querying. It includes support for
executing SQL statements, retrieving entities by ID, and exporting data in
Kleio format.
"""
import logging
from typing import List

import pandas as pd
from pydantic import BaseModel
from sqlalchemy import (
    select,
    text,
)
from sqlalchemy.sql.selectable import Select

import timelink
from timelink.api.models import Entity


class TimelinkDatabaseSchema(BaseModel):
    """Pydantic schema for TimelinkDatabase representation."""

    db_name: str
    db_type: str


class DatabaseQueryMixin:
    """Methods for high-level data access and querying.

    This mixin provides a simplified interface for common database operations,
    integrating with SQLAlchemy for queries and Pandas for data manipulation.
    """

    def select(self, sql, session=None, as_dataframe=False):
        """Execute a SELECT statement on the database.

        Args:
            sql (str | Select): A SQL string or SQLAlchemy Select statement.
            session (Session, optional): An active database session. If None,
                creates a new session. Defaults to None.
            as_dataframe (bool, optional): If True, returns results as a pandas DataFrame.
                Defaults to False.

        Returns:
            Result | List[Row] | pd.DataFrame: When session is provided and as_dataframe
                is False, returns a SQLAlchemy Result object. When session is None and
                as_dataframe is False, returns a list of Row objects (fetched immediately).
                When as_dataframe is True, returns a pandas DataFrame.

        Raises:
            ValueError: If sql is not a string or select statement.

        Note:
            When session is None, all data is fetched immediately within the session
            context to avoid connection issues. When a session is provided, the caller
            is responsible for managing the session lifecycle.
        """
        # if sql is a string build a select statement
        if isinstance(sql, str):
            sql = select(text(sql))
        # if sql is a select statement
        elif not isinstance(sql, Select):
            raise ValueError(
                "sql must be a Select statement or a string with a valid select statement"
            )

        if session is None:
            with self.session() as session:
                try:
                    result = session.execute(sql)
                    # When session is None, materialize results inside the session context
                    # to avoid issues with closed connections
                    if as_dataframe:
                        return pd.DataFrame(result.fetchall(), columns=result.keys())
                    else:
                        # Fetch all rows while the session is still active
                        return result.fetchall()
                except Exception as e:
                    session.rollback()
                    logging.error(f"Error executing select: {e}")
                    raise
        else:
            try:
                result = session.execute(sql)
                if as_dataframe:
                    return pd.DataFrame(result.fetchall(), columns=result.keys())
                else:
                    return result
            except Exception as e:
                # Only rollback if the session is still active
                if session.is_active:
                    session.rollback()
                logging.error(f"Error executing select: {e}")
                raise

    def query(self, query_spec):
        """Execute a query on the database.

        Args:
            query_spec: A SQLAlchemy query specification.

        Returns:
            Result: SQLAlchemy Result object containing query results.

        Raises:
            Exception: If an error occurs during query execution.
        """

        with self.session() as session:
            try:
                result = session.execute(query_spec)
            except Exception as e:
                session.rollback()
                logging.error(f"Error executing query: {e}")
                raise
        return result

    def get_person(self, *args, **kwargs):
        """Fetch a person by id

        See :func:`timelink.api.models.person.get_person`

        """
        if kwargs.get("session", None) is None and kwargs.get("db", None) is None:
            kwargs["db"] = self
        return timelink.api.models.person.get_person(*args, **kwargs)

    def get_entity(self, id: str, session=None) -> Entity:
        """Fetch an entity by id.

        See: :func:`timelink.api.models.entity.Entity.get_entity`

        """
        if session is None:
            with self.session() as session:
                try:
                    return Entity.get_entity(id, session)
                except Exception as e:
                    session.rollback()
                    logging.error(f"Error fetching entity: {e}")
                    raise
        else:
            return Entity.get_entity(id, session)

    def export_as_kleio(
        self,
        ids: List,
        filename,
        kleio_group: str = None,
        source_group: str = None,
        act_group: str = None,
    ):
        """Export entities to a kleio file

        Renders each of the entities in the list in kleio format
        using Entity.to_kleio() and writes them to a file.

        If provided, kleio_group, source_group and act_group are written
        before the entities.


        Args:
            ids (List): list of ids
            filename ([type]): destination file path
            kleio_group ([type]): initial kleio group
            source_group ([type]): source group
            act_group ([type]): act group
        """

        with open(filename, "w", encoding="utf-8") as f:
            if kleio_group is not None:
                f.write(f"{kleio_group}\n")
            if source_group is not None:
                f.write(f"{source_group}\n")
            if act_group is not None:
                f.write(f"{act_group}\n")
            for id in ids:
                with self.session() as session:
                    try:
                        ent = Entity.get_entity(id, session)
                        f.write(str(ent.to_kleio()) + "\n\n")
                    except Exception as e:
                        session.rollback()
                        logging.error(f"Error exporting entity {id}: {e}")

    def pperson(self, id: str, session=None):
        """Prints a person in kleio notation"""
        if session is None:
            session = self.session()
            p = self.get_person(id=id, session=session)
            # get session from object p
            kleio = p.to_kleio()
        else:
            p = self.get_person(id=id, session=session)
            kleio = p.to_kleio()
        print(kleio)

    def as_schema(self) -> TimelinkDatabaseSchema:
        """Return a Pydantic schema for this database"""
        return TimelinkDatabaseSchema(db_name=self.db_name, db_type=self.db_type)
