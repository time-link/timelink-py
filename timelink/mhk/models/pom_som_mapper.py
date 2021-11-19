from typing import Optional, Type, List

from sqlalchemy import Column, String, Integer, ForeignKey, Table, Float, \
    select
from sqlalchemy import inspect
from sqlalchemy.orm import relationship

from timelink.mhk.models.base_class import Base
from timelink.mhk.models.entity import Entity


class PomSomMapper(Entity):
    """
    Represents a mapping between a Kleio Group in the
    Source Oriented Model (Som) and a relational database entity
    in the Person Oriented Model (Pom). This class in an ORM
    mapping for the table "classes" in a Timelink-MHK database,
    and the associated "class_attributes" table. Together the
    two tables describe a Som-Pom mapping, and allow for dynamic
    mappings to be added to a given project.

    Fields:
        * id - name of this PomSomMapper, singular form
        * table_name - name of the table in Pom, plural form
        * class_group - name of Som group that maps to this table
        * super_class - name of PomSom class extended by this one

    For a mapping between a Som Group and a Pom table
    to be fully operational it is necessary that:

    1. The tables "classes" and "class_attributes" contain the mapping
    information, normally populated during the initialization process of
    the database (DBSystem.db_init) and updated during import,
    as new sources define new mappings dynamically.

    2. A table for storing the elements of the Som Group. This is either
    mapped to a basic core table (persons,objects,acts,sources,...) or
    to an additional table for extra information. The name of the table for
    a given group and the correspondence between group elements and table
    columns is given in the "classes" and "class_attributes" tables. If the
    group adds extra information creating a new table that "extends"
     an existing table, through what is called a joined inheritance hierarchy
    (see https://docs.sqlalchemy.org/en/14/orm/inheritance.html)

    3. An ORM sqlalchemy model that represents the Pom model and joins
    the information of the inheritance hierarchy, by mapping to the necessary
    tables.


    To ensure that all the three dimensions exist in a given context it
    is necessary that:

    1. When creating a new database, the core Pom tables can be created
    using sqlalchemy `metadata.create_all(bind=engine)`. Then the
    tables "classes" and "class_attributes" must be populated with the mapping
    of the core Som and Pom core entities. See timelink.models.base_mappings.py
    for the core data for the bootstrapping of the mapping information. Both steps
    are ensured by DBSystem.init_db

    2. When importing new sources, if a new mapping was generated at the
   translation step, it is necessary first to populate "classes" and
   "class_attributes" with the mapping information, included the translation
   source, then generate the table for the group information (if it
   does not exist) and the ORM mapping. This step is done by the method
   PomSomMapper.ensure_mapping(session).

   3. When connecting to a database created by a legacy version of MHK, it is
   necessary to ensure that the ORM mappings exist, by examining all the
   information in the "classes" table and checking if the ORM mapping and
   table representations exist.
   This is also done by the PomSomMapper.ensure_mapping(session) method.








    """
    __tablename__ = 'classes'

    id = Column(String, ForeignKey('entities.id'), primary_key=True)
    table_name = Column(String)
    class_group = Column("group_name", String(32))
    super_class = Column("super", String)
    __mapper_args__ = {
        'polymorphic_identity': 'class',
        'inherit_condition': id == Entity.id
    }
    # stores the ORM mapper for this mapping
    orm_class: Entity

    def ensure_mapping(self, session=None):
        """
        Ensure that a table exists to support
        this SOM Mapping

        Checks if there is a table definition
        to support this mapping. If not a new table
        definition is created.
        NOT TESTED
        """
        if not hasattr(self, 'orm_class'):
            self.orm_class = None

        my_orm = self.orm_class

        if my_orm is not None:
            return self.orm_class
        my_orm = Entity.get_orm_for_pom_class(self.id)
        if my_orm is not None:
            self.orm_class = my_orm
            return self.orm_class
        session = inspect(self).session
        if session is None:
            # cannot ensure mapping if no connection to db
            return None
        metadata_obj = type(self).metadata
        pytables = metadata_obj.tables
        my_table: Table
        if self.table_name in pytables.keys():
            my_table = pytables[self.table_name]
        else:
            my_table = Table(self.table_name, metadata_obj,
                             extend_existing=True)
            cattr: Type["PomClassAttributes"]
            for cattr in self.class_attributes:
                PyType = None
                pom_type = cattr.coltype.lower()
                if pom_type == 'varchar':
                    PyType = String(cattr.colsize)
                elif pom_type == 'numeric' and cattr.colprecision == 0:
                    PyType = Integer
                elif pom_type == 'numeric' and cattr.colprecision > 0:
                    PyType = Float
                else:
                    PyType = String
                print(f"Inferred python type for {cattr.colname}: ", PyType)


                if cattr.pkey != 0:
                    if self.super_class not in ['root','base']:
                        print("Getting super class " + self.super_class)
                        pom_super_class: PomSomMapper = PomSomMapper.get_pom_class(
                            session, self.super_class)
                        if pom_super_class is not None:
                            super_class_table_id = pom_super_class.table_name + '.id'
                        else:
                            print("ERROR could not find superclass: ",
                                  self.super_class)
                            super_class_table_id = 'entities.id'
                        my_table.append_column(Column(cattr.colname, PyType,
                                                      ForeignKey(
                                                          super_class_table_id),
                                                      primary_key=True),
                                               replace_existing=True)
                    else:
                        my_table.append_column(Column(cattr.colname, PyType,
                                                      primary_key=True),
                                               replace_existing=True)
                else:
                    my_table.append_column(
                        Column(cattr.colname, PyType, primary_key=False),
                        replace_existing=True)

            super_orm = Entity.get_orm_for_pom_class(self.super_class)
            props = {
                '__table__': my_table,
                '__mapper_args__': {'polymorphic_identity': self.id}
            }

            try:
                my_orm = type(self.id.capitalize(), (super_orm,), props)
            except:
                pass
            self.orm_class = my_orm
            return self.orm_class
            # print("----")
            # print(repr(NewTable))
            # self.__table__= NewTable

    @classmethod
    def get_pom_classes(cls, session=None):
        if session is None:
            session = inspect(cls).session
            if session is None:
                # cannot ensure mapping if no connection to db
                return
        stmt = select(cls)
        pom_classes: Optional["PomSomMapper"] = session.execute(
            stmt).scalars().all()
        return pom_classes

    @classmethod
    def get_pom_class_ids(cls, session=None):
        if session is None:
            session = inspect(cls).session
            if session is None:
                # cannot ensure mapping if no connection to db
                return

        stmt = select(cls.id)
        pom_class_ids: Optional[List[str]] = session.execute(
            stmt).scalars().all()
        return pom_class_ids

    @classmethod
    def get_pom_class(cls, session, pom_class_name: String):
        """
        Return the pom_class object for a given pom_class_name.

        See also Entity.get_orm_for_pom_class

        """
        pom_class: Optional["PomSomMapper"] = session.query(Entity).get(
            pom_class_name)
        return pom_class

    def __repr__(self):
        return (
            f'PomSomMapper(id="{self.id}", '
            f'table_name="{self.table_name}", '
            f'class_group="{self.class_group}", '
            f'super_class="{self.super_class}" '
            f')'
        )

    def __str__(self):
        r = f'{self.id} table {self.table_name} super {self.super_class}\n'
        for cattr in self.class_attributes:
            r = r + f'{cattr.the_class}.{cattr.name} \tclass {cattr.colclass} \tcol {cattr.colname} \ttype {cattr.coltype} size {cattr.colsize} precision {cattr.colprecision} primary key {cattr.pkey} \n'
        return r


class PomClassAttributes(Base):
    __tablename__ = 'class_attributes'

    the_class = Column(String, ForeignKey('classes.id'), primary_key=True)

    pom_class = relationship("PomSomMapper", foreign_keys=[the_class],
                             back_populates='class_attributes')
    name = Column(String(32), primary_key=True)
    colname = Column(String(32))
    colclass = Column(String(32))
    coltype = Column(String)
    colsize = Column(Integer)
    colprecision = Column(Integer)
    pkey = Column(Integer)

    def __repr__(self):
        return (
            f'PomClassAttributes(the_class="{self.the_class}", '
            f'name="{self.name}", '
            f'colname="{self.colname}", '
            f'colclass="{self.colclass}", '
            f'coltype="{self.coltype}", '
            f'colsize="{self.colsize}", '
            f'colprecision="{self.colprecision}", '
            f'pkey="{self.pkey}" '
            f')'
        )


PomSomMapper.class_attributes = relationship("PomClassAttributes",
                                             back_populates="pom_class")
