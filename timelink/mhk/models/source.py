"""
(c) Joaquim Carvalho 2021.
MIT License, no warranties.
"""

# pylint: disable=import-error

from sqlalchemy import Column, String, ForeignKey

from timelink.mhk.models.entity import Entity
from timelink.kleio.utilities import kleio_escape, quote_long_text


class Source(Entity):
    __tablename__ = "sources"

    id = Column(String, ForeignKey("entities.id"), primary_key=True)
    the_type = Column(String(32))
    the_date = Column(String, index=True)
    loc = Column(String)
    ref = Column(String)
    kleiofile = Column(String, index=True)
    replaces = Column(String)
    obs = Column(String)

    __mapper_args__ = {"polymorphic_identity": "source"}

    def __repr__(self):
        sr = super().__repr__()
        return (
            f"Source(id={sr}, "
            f'the_type="{self.the_type}", '
            f'the_date="{self.the_date}", '
            f'local="{self.loc}", '
            f'ref="{self.ref}", '
            f'kleiofile="{self.kleiofile}", '
            f'replaces="{self.replaces}", '
            f'obs="{self.obs}"'
            f")"
        )

    def __str__(self):
        r = (
            f"{self.groupname}${self.id}/{self.the_date}"
            f"/type={kleio_escape(self.the_type)}"
            f"/ref={kleio_escape(self.ref)}"
            f"/loc={kleio_escape(self.loc)}"
            f'/kleiofile={kleio_escape(self.kleiofile)}"'
            f"/replaces={self.replaces}"
        )
        if self.obs is not None and len(self.obs.strip()) > 0:
            r = f"{r}/obs={quote_long_text(self.obs)}"
        return r
