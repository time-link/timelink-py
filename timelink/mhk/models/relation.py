from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from timelink.mhk.models.base import Entity

class Relation(Entity):  # should extend Entity but gives error

    __tablename__ = 'relations'

    id = Column(String,ForeignKey('entities.id'), primary_key=True)
    #rel_entity = relationship("Entity",foreign_keys='id',back_populates='rel')
    origin = Column(String,ForeignKey('entities.id'))
    org = relationship(Entity,foreign_keys=[origin], back_populates='rels_out')

    destination = Column(String,ForeignKey('entities.id'))
    dest = relationship("Entity",foreign_keys=[destination], back_populates="rels_in")
    the_type = Column(String)
    the_value = Column(String)
    the_date = Column(String)
    obs = Column(String)

    __mapper_args__ = {
        'polymorphic_identity':'relation',
        'inherit_condition': id == Entity.id
    }

    def __repr__(self):
        sr = super().__repr__()
        return (
            f'Relation(id={sr}, '
            f'origin="{self.origin}", '
            f'destination="{self.destination}", '
            f'the_type="{self.the_type}", '
            f'the_value="{self.the_value}", '
            f'the_date="{self.the_date}"", '
            f'obs={self.obs}'
            f')'
        )

    def __str__(self):
        if self.dest is not None and self.dest.pom_class == 'person':
            r = f'rel${self.the_type}/{self.the_value}/{self.dest.name}/{self.destination}/{self.the_date}'
        else:
            r = f'rel${self.the_type}/{self.the_value}/{self.destination}/{self.the_date}'
        if self.obs is not None:
                r = (f'{r}  /obs={self.obs}')
        return r



Entity.rels_out = relationship("Relation",foreign_keys=[Relation.origin],back_populates="dest")


Entity.rels_in = relationship("Relation",foreign_keys=[Relation.destination],back_populates="org")