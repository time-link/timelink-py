from sqlalchemy import Column, String, ForeignKey, Integer
from sqlalchemy.orm import relationship

from timelink.mhk.models.base_class import Base
from timelink.mhk.models.base import PomSomMapper # noqa


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
