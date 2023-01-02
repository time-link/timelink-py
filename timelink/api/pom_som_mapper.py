from typing import Optional
from sqlmodel import Field, Session, SQLModel, create_engine

# set the table name to "classes" to match the Timelink-MHK database
class PomSomMapper(SQLModel, table=True):
    """

    Represents a mapping between a Kleio Group in the
    Source Oriented Model (Som) and a relational database entity
    in the Person Oriented Model (Pom). This class corresponds
    to the table "classes" in a Timelink-MHK database,
    and the associated "class_attributes" table. Together the
    two tables describe a Som-Pom mapping, that define how
    Kleio groups are stored in the relational database.

    This class can generate tables and ORM objects that can
    store a Kleio Group in the database.
"""
    __tablename__ = "classes"