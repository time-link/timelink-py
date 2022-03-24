from sqlalchemy import Column, String, ForeignKey

from timelink.mhk.models.entity import Entity


class Person(Entity):
    __tablename__ = "persons"

    id = Column(String, ForeignKey('entities.id'), primary_key=True)
    name = Column(String, index=True)
    id = Column(String, ForeignKey("entities.id"), primary_key=True)
    name = Column(String)
    sex = Column(String(1))
    obs = Column(String)

    __mapper_args__ = {
        'polymorphic_identity': 'person'
    }

    def __repr__(self):
        sr = super().__repr__()
        return (
            f"Person(id={sr}, "
            f'name="{self.name}", '
            f'sex="{self.sex}", '
            f"obs={self.obs}"
            f")"
        )

    def __str__(self):
        r = f"{self.groupname}${self.name}/{self.sex}/id={self.id}"
        if self.obs is not None:
            r = f"{r}/obs={self.obs}"
        return r
