# following https://sqlmodel.tiangolo.com/tutorial/
from typing import Optional
from sqlmodel import Field, Session, SQLModel, create_engine


class Entity(SQLModel, table=True):
    id: Optional[str] = Field(default=None, primary_key=True)
    the_class: Optional[str] = None
    description: Optional[str] = None
    inside: Optional[str] = None
    the_order: Optional[int] = None
    the_level: Optional[int] = None
    the_line: Optional[int] = None
    group_name: Optional[str] = None


sqlite_file_name = "../../tests/sqlite/sqlmodel.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, echo=True)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def create_root_entity():
    root = Entity(id="*ROOT*")

    session = Session(engine)
    session.add(root)

    session.commit()


def main():
    create_db_and_tables()
    create_root_entity()


if __name__ == "__main__":
    main()
