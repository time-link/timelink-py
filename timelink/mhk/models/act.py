"""
(c) Joaquim Carvalho 2021.
MIT License, no warranties.
"""
from sqlalchemy import Column, String, ForeignKey

from timelink.mhk.models.base import Entity


class Act(Entity):
    __tablename__ = "acts"

    id = Column(String, ForeignKey("entities.id"), primary_key=True)
    the_type = Column(String(32))
    the_date = Column(String)
    loc = Column(String)
    ref = Column(String)
    obs = Column(String)

    __mapper_args__ = {"polymorphic_identity": "act"}

    def __repr__(self):
        sr = super().__repr__()
        return (
            f"Act(id={sr}, "
            f'the_type="{self.the_type}", '
            f'the_date="{self.the_date}", '
            f'local="{self.loc}", '
            f'ref="{self.ref}", '
            f"obs={self.obs}"
            f")"
        )

    def __str__(self):
        r = (
            f"{self.groupname}${self.id}"
            f"/{self.the_date}"
            f"/type={self.the_type}"
            f"/ref={self.ref}"
            f"/loc={self.loc}"
        )
        if self.obs is not None:
            r = f"{r}/obs={self.obs}"
        return r
