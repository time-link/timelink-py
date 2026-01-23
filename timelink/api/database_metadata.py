"""Database Metadata Mixin for Timelink.

This module provides the DatabaseMetadataMixin class, which contains methods for
inspecting database structure, metadata, and SQLAlchemy ORM models. It includes
utilities for listing tables, views, and columns, as well as mapping between
database tables and ORM classes.
"""
from collections import namedtuple
from typing import List

from sqlalchemy import (
    Table,
    func,
    inspect,
    select,
    text,
)
from sqlalchemy.orm import aliased
from sqlalchemy.sql.selectable import TableClause

from timelink.api.models import (
    Entity,
    pom_som_base_mappings,
)
from timelink.api.models.base_class import Base, get_all_base_subclasses


class DatabaseMetadataMixin:
    """Methods for database inspection and metadata management.

    This mixin provides utility methods to introspect the database schema,
    retrieve ORM model information, and describe the structure of tables and views.
    """

    def get_database_version(self):
        """Retrieve the current Alembic migration version of the database.

        Returns:
            str: The version number string from the 'alembic_version' table.
        """
        with self.engine.connect() as connection:
            result = connection.execute(
                select(text("version_num")).select_from(text("alembic_version"))
            )
            version = result.scalar()
        return version

    def db_table_names(self):
        """Return the names of all tables currently present in the database.

        Returns:
            list[str]: A list of table names.
        """
        insp = inspect(self.engine)
        db_tables = insp.get_table_names()  # tables in the database
        return db_tables

    def db_orm_tables(self):
        """Orm tables in the database

        These are the tables managed by SQLAlchemy ORM.
        These tables should be present in the database.

        These include:

            * All the tables of the timelink data model (Entity and its subclasses)
            * Other auxiliary tables managed with SQLAlchemy ORM like class_attributes
              and Kleio imported files, syspar, syslog, etc.
            * Dynamically created tables during import (see db_dynamic_tables)

        Returns:
            list: list of table objects
        """
        all_subclasses = get_all_base_subclasses()
        return [ormclass.__mapper__.local_table for ormclass in all_subclasses]

    def db_base_table_names(self):
        """Return the names of the core Timelink base tables.

        These are the tables defined in the base mappings and the 'classes' table.
        They represent the static part of the Timelink schema.

        Returns:
            list[str]: A list of base table names.
        """
        r = [
            pom_som_base_mappings[k][0].table_name for k in pom_som_base_mappings.keys()
        ]
        return list(set(r + ["classes"]))

    def db_base_tables(self):
        """Base tables in the database

        These are the tables included in the base mappings,
        i.e., the tables that are not dynamically created
        """
        return [
            self.metadata.tables[table_name]
            for table_name in self.db_base_table_names()
        ]

    def db_dynamic_tables(self):
        """Return tables that were created dynamically during data imports.

        Dynamic tables are created on-the-fly during imports when new entity types
        are encountered. They correspond to ORM classes dynamically created by
        the PomSomMapper mechanism.

        Returns:
            list[Table]: A list of SQLAlchemy Table objects for dynamic tables.
        """
        entity_based_tables = [
            ormclass.__mapper__.local_table
            for ormclass in Entity.get_subclasses()
            if ormclass.is_dynamic()
        ]
        return list(set(entity_based_tables) - set(self.db_base_tables()))

    def orm_table_names(self):
        """Current tables associated with ORM models"""
        return Entity.get_orm_table_names()

    def view_names(self):
        """Get the list of views in the database"""
        inspector = inspect(self.engine)
        return inspector.get_view_names()

    def get_view(self, view_name: str):
        """Get a view by name"""
        return self.views[view_name]

    def get_view_columns(self, view_name: str):
        """Get the columns of a view"""
        view = self.get_view(view_name)
        return list(view.columns)

    def table_row_count(self) -> List[tuple[str, int]]:
        """Count the number of rows in each table in the database.

        Returns:
            List[tuple[str, int]]: A list of tuples containing (table_name, row_count).
        """

        tables_names = self.db_table_names()

        row_count = []
        with self.session() as session:
            for table in tables_names:
                length = session.scalar(
                    select(func.count()).select_from(  # pylint: disable=not-callable
                        text(table)
                    )  # pylint: disable=not-callable
                )  # pylint: disable=not-callable
                row_count.append((table, length))
        return row_count

    def get_models_ids(self):
        """Get the ORM model classes as a list of ids

        Returns:
            list: list of ORM classes as string ids
        """
        return Entity.get_som_mapper_ids()

    def get_model(self, class_id: str | list[str], make_alias=None):
        """Get the ORM class for a entity type

        Args:
            class_id (str | List[str]): class id or list of class ids
            make_alias (bool, optional): if True, return an aliased ORM class;
                                         defaults to True in lists; False if single class_id.
        Returns:
            ORM class or list of ORM classes
        """
        if isinstance(class_id, list):
            # Default: alias models when a list of class_ids is provided,
            # unless the caller explicitly sets make_alias.
            if make_alias is None:
                make_alias = True
            return [
                self.get_model_by_name(c, make_alias=make_alias) for c in class_id
            ]
        else:
            # Default: do not alias for a single class_id, unless explicitly requested.
            if make_alias is None:
                make_alias = False
            return self.get_model_by_name(class_id, make_alias=make_alias)

    def get_model_by_name(self, class_or_groupname: str, make_alias=False):
        """Get the ORM class for a entity type by name
        or for a group name. If the name is not found, return None

        Args:
            class_or_groupname (str): class or group name

        Returns:
            ORM class aliased to avoid  # https://docs.sqlalchemy.org/en/20/errors.html#error-xaj2

        """

        orm_model = Entity.get_orm_for_pom_class(class_or_groupname)
        if orm_model is not None:
            if make_alias:
                return aliased(orm_model, flat=True)
            else:
                return orm_model
        else:
            orm_model = Entity.get_orm_for_group(class_or_groupname)
            if orm_model is None:
                return None
            if make_alias:
                return aliased(orm_model, flat=True)
            else:
                return orm_model

    def table_exists(self, table_name: str) -> bool:
        inspector = inspect(self.engine)
        return inspector.has_table(table_name)

    def get_table(self, table_or_class: str | Entity) -> Table:
        """Get a table object from the database

        Args:
            table_or_class (str | Entity): table name, model name of ORM model

        Returns:
            sqlAlchemy Table: table object


        """
        if type(table_or_class) is str:
            if table_or_class in self.orm_table_names():
                model = Entity.get_tables_to_orm_as_dict()[table_or_class]
                if model is not None:
                    return model.__table__
            elif table_or_class in self.db_table_names():
                table = self.metadata.tables.get(table_or_class, None)
                if table is not None:
                    return table
                else:
                    table = Table(
                        table_or_class, self.metadata, autoload_with=self.engine
                    )
                    return table
            elif table_or_class in self.get_models_ids():
                model = self.get_model_by_name(table_or_class)
                if model is not None:
                    return model.__table__
        elif isinstance(table_or_class, type) and issubclass(table_or_class, Entity):
            return table_or_class.__table__
        return None

    def get_columns(self, class_or_table: str):
        """Get the columns for a entity type

        Returns:
            list: list of columns
        """

        Model = self.get_model_by_name(class_or_table, make_alias=False)
        if Model is None:
            if class_or_table in Entity.get_orm_table_names():
                return list(self.get_table(class_or_table).columns)
            elif class_or_table in self.view_names():
                return self.get_view_columns(class_or_table)
            else:
                raise ValueError(f"{class_or_table} not found")

        insp = inspect(Model)
        return list(insp.columns)

    def describe(self, argument, show=None, **kwargs):
        """Describe a table, view or a model
          if argument is a string, it is assumed to be a table or view
          if argument is a model, it is assumed to be a ORM model
          otherwise it is checked if it is a table object
          the method prints the columns of the table or model

        Args:
            argument: table name or model
            kwargs: additional arguments to pass to the describe method
            show: print the columns

        Returns:
            list: list of columns
        """
        columns = []
        argument_type = None
        if argument is None:
            GroupModel = namedtuple("GroupModel", ["group", "table", "model"])
            return [
                GroupModel(group, orm.__tablename__, orm.__name__)
                for (group, orm) in Entity.group_models.items()
            ]
        if isinstance(argument, str):
            if argument in self.get_models_ids():
                argument_type = "model"
                columns = self.get_columns(argument)
            elif self.get_model_by_name(argument) is not None:
                argument_type = "model"
                columns = self.get_columns(argument)
            elif argument in self.orm_table_names():
                argument_type = "model_table"
                Model = Entity.get_tables_to_orm_as_dict()[argument]
                insp = inspect(Model)
                columns = list(insp.columns)
            elif argument in self.db_table_names():
                argument_type = "non_model_table"
                table = Table(argument, Base.metadata, autoload_with=self.engine)
                columns = list(table.columns)
        elif isinstance(argument, type) and issubclass(argument, Base):
            argument_type = "model"
            Model = argument
            insp = inspect(Model)
            columns = list(insp.columns)
        elif issubclass(type(argument), TableClause):
            argument_type = "table_like"
            columns = list(argument.columns)

        if len(columns) > 0 and show is not None:
            print(f"{str(argument)} ({argument_type})")
            for col in columns:
                fkey = str(col.foreign_keys) if col.foreign_keys else ""
                print(f"{col.name:<20} {str(col.table):<20} {str(col.type):<10} {fkey}")
        return columns
