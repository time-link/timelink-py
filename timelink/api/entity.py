# following https://sqlmodel.tiangolo.com/tutorial/
from typing import Optional
from sqlmodel import Field, Session, SQLModel, create_engine


class Entity(SQLModel, table=True):
    """An Entity in the Timelink data model.

    Args:
        SQLModel (sql.SQLModel): Required by the framework.
        table (bool, optional): Is the class to be stored in a database table. Defaults to True.

    Attributes:
        id （Optional[str]）: Unique identifier, if missing an automatic one will be generated
        the_class (Optional[str]): class of the entity (relation to Class table)
        description (Optional[str]): a descriptive name for the entity (e.g. a person's name)
        inside (Optional[str]): id of the entity inside this occurred in the original source (will be self referencing relation)
        the_order  (Optional[int]): order in the original source
        the_level  (Optional[int]): the nesting level in the original source
        the_line (Optional[int]): line number in the original source
        group_name (Optional[str]): kleio group name in the original source
    """
    id: Optional[str] = Field(default=None, primary_key=True)
    the_class: Optional[str] = None
    description: Optional[str] = None
    inside: Optional[str] = None
    the_order: Optional[int] = None
    the_level: Optional[int] = None
    the_line: Optional[int] = None
    group_name: Optional[str] = None


SQLITE_FILE_NAME = "../../tests/sqlite/sqlmodel.db"
sqlite_url = f"sqlite:///{SQLITE_FILE_NAME}"

engine = create_engine(sqlite_url, echo=True)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def create_root_entity():
    root = Entity(id="*ROOT*", description="Root container for all entities")

    with Session(engine) as session:
        session.add(root)

        session.commit()
        print("After commit")
        print("Root:", root)

        print("Root description", root.description)
    
    print("Root description after session closes", root.description)


def main():
    create_db_and_tables()
    create_root_entity()
    

if __name__ == "__main__":
    main()
