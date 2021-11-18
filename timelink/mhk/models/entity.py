
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy import case
from sqlalchemy.orm import relationship

from timelink.mhk.models.base_class import Base

class Entity(Base):
    __tablename__ = 'entities'

    id = Column(String, primary_key=True)
    pom_class = Column('class', String,ForeignKey('classes.id'))
    inside = Column(String, ForeignKey('entities.id'))
    the_order = Column(Integer)
    the_level = Column(Integer)
    the_line = Column(Integer)
    groupname = Column(String)
    updated = Column(DateTime)
    indexed = Column(DateTime)

    rels_in = relationship("Relation", back_populates="dest")
    rels_out = relationship("Relation", back_populates="org")

    # see https://docs.sqlalchemy.org/en/14/orm/inheritance.html
    # To handle non mapped pom_class see https://github.com/sqlalchemy/sqlalchemy/issues/5445
    #
    #    __mapper_args__ = {
    #       "polymorphic_identity": "entity",
    #    "polymorphic_on": case(
    #        [(type.in_(["parent", "child"]), type)], else_="entity"
    #    ),
    #
    #  This defines what mappings do exist
    # [aclass.__mapper_args__['polymorphic_identity'] for aclass in Entity.__subclasses__()]

    __mapper_args__ = {
        'polymorphic_identity': 'entity',
        'polymorphic_on': pom_class,
    }


    # untested
    @classmethod  # untested
    def get_subclasses(cls):
        for subclass in cls.__subclasses__():
            yield from subclass.get_subclasses()
            yield subclass

    @classmethod
    def mapped_pom_classes(cls):
        return [aclass.__mapper_args__['polymorphic_identity']
                for aclass
                in Entity.__subclasses__()]

    @classmethod
    def table_to_orm(cls):
        """
        Return a dict with table name as key and ORM class as value
        """
        return {subclass.__mapper__.local_table.name: subclass for subclass in
                cls.get_subclasses()}

    @classmethod
    def pom_class_to_orm(cls):
        """
        Return a dict with pom_class id as key and ORM class as value
        """
        sc = list(cls.get_subclasses())
        if sc is not None:
            sc.append(cls)
        return {subclass.__mapper__.polymorphic_identity: subclass for subclass
                in sc}

    @classmethod
    def get_orm_for_table(cls, table: String):
        """
        Entity.get_orm_for_table("acts")

        will return the ORM class handling the "acts" table
        """
        return cls.table_to_orm().get(table, None)

    @classmethod
    def get_orm_for_pom_class(cls, pom_class: String):
        """
        Entity.get_orgm_for_pom_class("act")

        will return the ORM class corresponding to the pom_class "act"
        """
        return cls.pom_class_to_orm().get(pom_class, None)

    def __repr__(self):
        return (
            f'Entity(id="{self.id}", '
            f'pom_class="{self.pom_class}",'
            f'inside="{self.inside}", '
            f'the_order={self.the_order}, '
            f'the_level={self.the_level}, '
            f'the_line={self.the_line}, '
            f'groupname="{self.groupname}", '

            f'updated={self.updated}, '
            f'indexed={self.indexed},'
            f')'
        )

    def __str__(self):
        return (f'{self.groupname}${self.id}/type={self.pom_class}')
