"""
(c) Joaquim Carvalho 2023.
MIT License, no warranties.
"""

from typing import Optional

from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped  # pylint: disable=import-error
from sqlalchemy.orm import mapped_column  # pylint: disable=import-error

from .entity import Entity
from timelink.kleio.utilities import kleio_escape, quote_long_text


class Source(Entity):
    """Represent an historical source"""

    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(
        String, ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True
    )
    the_type: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        comment="type of the source (parish register, tax roll, etc.)",
    )
    the_date: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    loc: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, comment="location of the source"
    )
    ref: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, comment="call number of the source"
    )
    kleiofile: Mapped[Optional[str]] = mapped_column(
        String, index=True, comment="path of the kleio file"
    )
    replaces: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, comment="id of the source this one replaces"
    )
    obs: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, comment="observations"
    )

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
        return self.to_kleio()

    def to_kleio(self, ident="", ident_inc="  ", show_contained=True, width=80) -> str:
        r = (
            f"{self.groupname}${self.id}/{self.the_date}"
            f"/type={kleio_escape(self.the_type)}"
            f"/ref={kleio_escape(self.ref)}"
            f"/loc={kleio_escape(self.loc)}"
            f'/kleiofile={kleio_escape(self.kleiofile)}"'
            f"/replaces={self.replaces}"
        )
        if self.obs is not None and len(self.obs.strip()) > 0:
            r = f"{r}/obs={quote_long_text(self.obs.strip(), width=width)}"
        r = super().to_kleio(
            self_string=r,
            ident=ident,
            ident_inc=ident_inc,
            show_contained=show_contained,
            width=width,
        )
        return r
