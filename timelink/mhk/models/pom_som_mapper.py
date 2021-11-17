from typing import Optional, Type

from sqlalchemy import Column, String, Integer, ForeignKey, Table, Float
from sqlalchemy.orm import relationship

from timelink.mhk.models.base_class import Base
from timelink.mhk.models.entity import Entity


class PomSomMapper(Entity):
    """
    Represents a mapping between a Kleio Group in the
    Source Oriented Model (Som) and a relational database entity
    in the Person Oriented Model (Pom).


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

    def ensure_mapping(self, session):
        """
        Ensure that a table exists to support
        this SOM Mapping

        Checks if there is a table definition
        to support this mapping. If not a new table
        definition is created.
        NOT TESTED
        """
        metadata_obj = type(self).metadata
        pytables = metadata_obj.tables
        if self.table_name in pytables.keys():
            return pytables[self.table_name]
        else:
            NewTable: Table = Table(self.table_name, metadata_obj,
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

                print("Getting super class " + self.super_class)
                PomSuperClass: PomSomMapper = PomSomMapper.get_pom_class(
                    session, self.super_class)
                if PomSuperClass is not None:
                    super_class_table_id = PomSuperClass.table_name + '.id'
                else:
                    print("ERROR could not find superclass: ",
                          self.super_class)
                    super_class_table_id = 'entities.id'
                if cattr.pkey != 0:
                    NewTable.append_column(Column(cattr.colname, PyType,
                                                  ForeignKey(
                                                      super_class_table_id),
                                                  primary_key=True),
                                           replace_existing=True)
                else:
                    NewTable.append_column(
                        Column(cattr.colname, PyType, primary_key=False),
                        replace_existing=True)

            # check if we have a mapping
            MyORM = entity.get_orm_for_pom_class(self.id)
            if MyORM is None:
                super_orm = entity.get_orm_for_pom_class(self.super_class)
                props = {
                    '__table__': NewTable,
                    '__mapper_args__': {'polymorphic_identity': self.id}
                }

                newORM = type(self.id.capitalize(), (super_orm,), props)
            # print("----")
            # print(repr(NewTable))
            # self.__table__= NewTable

    @classmethod
    def get_pom_class(cls, session, pom_class_name: String):
        """
        Return the pom_class object for a given pom_class_name.

        See also Entity.get_orm_for_pom_class

        """
        pom_class: Optional["PomSomMapper"] = session.query(entity).get(
            pom_class_name)
        return pom_class

    def __repr__(self):
        return (
            f'PomSomMapper(id={self.id}, '
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


PomClassAttributes.class_attributes = relationship("PomClassAttributes",
                                               back_populates="pom_class")
