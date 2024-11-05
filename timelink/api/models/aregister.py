"""
mapping 'authority-register' to class aregister.
class aregister super entity table aregisters
      with attributes
           id column id baseclass id coltype varchar colsize 64 colprecision 0 pkey 1
        and
           date column the_date baseclass date coltype varchar colsize 24 colprecision 0 pkey 0
        and
           user column user baseclass user coltype varchar colsize 32 colprecision 0 pkey 0
        and
           name column name baseclass name coltype varchar colsize 254 colprecision 0 pkey 0
        and
           dbase column dbase baseclass dbase coltype varchar colsize 32 colprecision 0 pkey 0
      and
         mode column replace_mode baseclass mode coltype varchar colsize 64 colprecision 0 pkey 0
        and
           obs column obs baseclass obs coltype varchar colsize 16654 colprecision 0 pkey 0 .

(c) Joaquim Carvalho 2024
MIT License, no warranties.
"""

from typing import Optional

from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped  # pylint: disable=import-error
from sqlalchemy.orm import mapped_column  # pylint: disable=import-error

from .entity import Entity
from timelink.kleio.utilities import kleio_escape, quote_long_text


class ARegister(Entity):
    """Represent an Authorithy Register"""

    __tablename__ = "aregisters"

    id: Mapped[str] = mapped_column(
        String, ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True
    )
    the_type: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        comment="type of the register (identifcation, user-comments, vocabulary, etc.)",
    )
    the_date: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    dbase: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, comment="name of the exporting database"
    )
    replace_mode: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
        comment="backup mode means the file is ignored by default on import",
    )
    kleiofile: Mapped[Optional[str]] = mapped_column(
        String, index=True, comment="path of the kleio file"
    )
    obs: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, comment="observations"
    )

    __mapper_args__ = {"polymorphic_identity": "aregister"}

    def __repr__(self):
        sr = super().__repr__()
        return str(
            f"ARegister(id={sr}, "
            f'the_type="{self.the_type}", '
            f'the_date="{self.the_date}", '
            f'dbase="{self.dbase}"',
            f'kleiofile="{self.kleiofile}", '
            f'replace_mode="{self.replace_mode}", '
            f'obs="{self.obs}"'
            f")"
        )

    def __str__(self):
        return self.to_kleio()

    def to_kleio(self, show_contained=True, self_string=None, ident="", ident_inc="  ", width=80, **kwargs) -> str:
        if self_string is None:
            r = (
                f"{self.groupname}${self.id}/{self.the_date}"
                f"/type={kleio_escape(self.the_type)}"
                f"/replace_mode={kleio_escape(self.replace_mode)}"
                f"/the_date={kleio_escape(self.the_date)}"
                f'/kleiofile={kleio_escape(self.kleiofile)}"'
            )
            if self.obs is not None and len(self.obs.strip()) > 0:
                r = f"{r}/obs={quote_long_text(self.obs.strip(), width=width)}"
        else:
            r = self_string
        r = super().to_kleio(
            self_string=r,
            ident=ident,
            ident_inc=ident_inc,
            show_contained=show_contained,
            width=width,
        )
        return r
