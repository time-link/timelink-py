# following https://sqlmodel.tiangolo.com/tutorial/

from typing import List, Optional
from sqlmodel import Field, Relationship, Session, SQLModel, col, or_, create_engine, select

# currently starting at https://sqlmodel.tiangolo.com/tutorial/relationship-attributes/define-relationships-attributes/
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
    the_class: Optional[str] = Field(index=True, foreign_key="classes.id")
    description: Optional[str] = Field(index=True)
    inside: Optional[str] = Field(index=True)
    the_order: Optional[int] = None
    the_level: Optional[int] = None
    the_line: Optional[int] = None
    group_name: Optional[str] = None

    __tablename__ = "entities"


class MapperClass(SQLModel, table=True):
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
    # set the table name to "classes" to match the Timelink-MHK database
    id: Optional[str] = Field(default=None, primary_key=True, foreign_key="entities.id")
    table_name: Optional[str] = Field(index=True) 
    group_name: Optional[str] = Field(index=True)
    super_class: Optional[str] = Field(index=True)


    __tablename__ = "classes"
    __mapper_args__ = {
        "polymorphic_identity": "the_class",
        "inherit_condition": id == Entity.id,
    }


SQLITE_FILE_NAME = "../../tests/sqlite/sqlmodel.db"
sqlite_url = f"sqlite:///{SQLITE_FILE_NAME}"

engine = create_engine(sqlite_url, echo=True)


def create_db_and_tables():
    """Create the database and tables

    Returns: None
    """
    SQLModel.metadata.create_all(engine)


def create_basic_data():
    """ Create the basic entities 
    
    Returns: None
    """
    root = Entity(id="*ROOT*", the_class='entity', description="Root container for all entities")
    entity = Entity(id="entity", description="Entity", the_class='class', inside="*ROOT*")
    act = Entity(id="act", description="Act", the_class='class', inside="*ROOT*")
    attribute = Entity(id="attribute", description="Attribute", the_class='class', inside="*ROOT*")
    geoentity = Entity(id="geoentity", description="Geoentity", the_class='class',  inside="*ROOT*")
    good = Entity(id="good", description="Good", the_class='class',    inside="*ROOT*")
    object_ = Entity(id="object", description="Object", the_class='class',inside="*ROOT*")
    person = Entity(id="person", description="Person", the_class='class', inside="*ROOT*")
    relation = Entity(id="relation", description="Relation", the_class='class',inside="*ROOT*")
    rentity = Entity(id="rentity", description="Rentity", the_class='class', inside="*ROOT*")
    rgeoentity = Entity(id="rgeoentity", description="Rgeoentity", the_class='class', inside="*ROOT*")
    robject = Entity(id="robject", description="Robject", the_class='class', inside="*ROOT*")
    rperson = Entity(id="rperson", description="Rperson", the_class='class', inside="*ROOT*")
    source = Entity(id="source", description="Source", the_class='class', inside="*ROOT*")
    e0 = Entity(id="baptismos 1685", the_class="source", the_order=1, the_level=1, the_line=4,	groupname="fonte")
    e1 = Entity(id="b1685.1", the_class="act", inside="baptismos 1685", the_order=2, the_level=2, the_line=6, group_name="bap")
    e2 = Entity(id="b1685.1-per1", the_class="person", inside="b1685.1", the_order=3, the_level=3, the_line=8, group_name="n")
    e3 = Entity(id="b1685.1-rela1", the_class="relation", inside="b1685.1-per1", the_order=4, the_level=4, the_line=9, group_name="relation")
    e4 = Entity(id="b1685.1-per1-per2", the_class="person", inside="b1685.1-per1", the_order=4, the_level=5, the_line=10, group_name="pai")
    e5 = Entity(id="b1685.1-per1-rela2", the_class="relation", inside="b1685.1-per1-per2", the_order=5, the_level=6, the_line=11, group_name="relation")
    e6 = Entity(id="b1685.1-per1-per2-att1-38", the_class="attribute", inside="b1685.1-per1-per2", the_order=5, the_level=7, the_line=12, group_name="ls")
    e7 = Entity(id="b1685.1-per1-per2-att2-38", the_class="attribute", inside="b1685.1-per1-per2", the_order=5, the_level=7, the_line=13, group_name="ls")
    e8 = Entity(id="b1685.1-per1-per3", the_class="person", inside="b1685.1-per1", the_order=4, the_level=5, the_line=14, group_name="mae")
    e9 = Entity(id="b1685.1-per1-rela3", the_class="relation", inside="b1685.1-per1-per3", the_order=5, the_level=6, the_line=15, group_name="relation")
    e10 = Entity(id="b1685.1-per1-per3-att1-38", the_class="attribute", inside="b1685.1-per1-per3", the_order=5, the_level=7, the_line=16, group_name="ls")
    # insert classes act,attribute,class,entity,person,relation,source
    entity_class = MapperClass(id="entity", table_name='entities', group_name='entity',super_class=None)
    act_class = MapperClass(id="act", table_name='acts', group_name='act',super_class='entity')
    attribute_class = MapperClass(id="attribute", table_name='attributes', group_name='attr',super_class='entity')
    mapper_class = MapperClass(id="class", table_name='classes', group_name='class',super_class='entity')
    person_class = MapperClass(id="person", table_name='persons', group_name='person',super_class='entity')
    relation_class = MapperClass(id="relation", table_name='relations', group_name='rel',super_class='entity')
    source_class = MapperClass(id="source", table_name='sources', group_name='source',super_class='entity')
    with Session(engine) as session:
        session.add(root)
        session.add(entity)
        session.add(entity_class)
        session.add(act)
        session.add(attribute)
        session.add(geoentity)
        session.add(good)
        session.add(object_)
        session.add(person)
        session.add(relation)
        session.add(rentity)
        session.add(rgeoentity)
        session.add(robject)
        session.add(rperson)
        session.add(source)
        session.add(e0)
        session.add(e1)
        session.add(e2)
        session.add(e3)
        session.add(e4)
        session.add(e5)
        session.add(e6)
        session.add(e7)
        session.add(e8)
        session.add(e9)
        session.add(e10)
        session.add(act_class)
        session.add(attribute_class)
        session.add(mapper_class)
        session.add(person_class)
        session.add(relation_class)
        session.add(source_class)
        

        session.commit()
        print("After commit")
        print("Root:", root)
        print("Root description", root.description)
        print("Source:", source)
        print("Source description", source.description)

    print("Root description after session closes", root.description)


def select_entities():
    """
    Select entities from the database.
    
    Returns: None
    """
    with Session(engine) as session:
        # statement = select(Entity).where(Entity.the_class == 'attribute').where(col(Entity.the_line) > 12, col(Entity.the_level)  <= 8)
        statement = select(Entity).where(or_(col(Entity.the_class) == 'class',col(Entity.id) == '*ROOT*'))
        results = session.exec(statement)
        # note that first() closes the cursor
        results = session.exec(statement)
        print('=====================')
        for entity in results:
            print(entity)
        print('=====================')
        root = session.get(Entity, "*ROOT*")
        print("Root:", root)


def update_entities():
    """
    Update entities in the database.
    
    Returns: None
    """
    with Session(engine) as session:
        root = session.get(Entity, "*ROOT*")
        root.description = "Root. Value for 'inside' in entities not enclosed in others."
        session.add(root)
        session.commit()


def main():
    create_db_and_tables()
    create_basic_data()
    update_entities()
    select_entities()
    

if __name__ == "__main__":
    main()
