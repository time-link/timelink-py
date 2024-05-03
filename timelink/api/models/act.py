""" Implementation of Acts in POM model

(c) Joaquim Carvalho 2023.
MIT License, no warranties.
"""

# for sqlalchemy 2.0 ORM
# see https://docs.sqlalchemy.org/en/20/orm/declarative_config.html
# and https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html#orm-declarative-table

from sqlalchemy import ForeignKey  # pylint: disable=import-error
from sqlalchemy import String  # pylint: disable=import-error
from sqlalchemy.orm import Mapped  # pylint: disable=import-error
from sqlalchemy.orm import mapped_column  # pylint: disable=import-error

from timelink.kleio.utilities import quote_long_text, kleio_escape

from .entity import Entity


class Act(Entity):
    """Represents an Act, i.e. a record of some event in a historical document.

    Examples of acts are: baptisms, marriages, purchase deeds, wills,
    court records.

    TODO: implement https://github.com/time-link/timelink-kleio/issues/1
    """

    __tablename__ = "acts"

    #: str:  a string uniquely identifying the act
    id: Mapped[str] = mapped_column(
        String, ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True
    )
    the_type: Mapped[str] = mapped_column(
        String(32), nullable=True, comment="type of act"
    )
    #: str: the date of the act in Kleio format AAAAMMDD
    the_date: Mapped[str] = mapped_column(
        String,
        index=True,
        nullable=True,
        comment="the date of the act in Kleio format AAAAMMDD",
    )
    #: str: location of the act, eg church, notary office
    loc: Mapped[str] = mapped_column(String, nullable=True)
    ref: Mapped[str] = mapped_column(String, nullable=True)  #: str: archival reference
    obs: Mapped[str] = mapped_column(
        String, nullable=True
    )  #: any observations or comments.

    __mapper_args__ = {"polymorphic_identity": "act"}

    def __repr__(self):
        """Expression that can be used to instantiate an Act"""
        sr = super().__repr__()
        return (
            f"Act(id={sr}, "
            f'the_type="{kleio_escape(self.the_type)}", '
            f'the_date="{self.the_date}", '
            f'local="{kleio_escape(self.loc)}", '
            f'ref="{kleio_escape(self.ref)}", '
            f'obs="{quote_long_text(self.obs)}"'
            f")"
        )

    def __str__(self):
        return self.to_kleio(show_contained=False)

    def to_kleio(self, ident="", ident_inc="  ", show_contained=True, width=80) -> str:
        r = (
            f"{self.groupname}${self.id}"
            f"/{self.the_date}"
            f"/type={kleio_escape(self.the_type)}"
            f"/ref={quote_long_text(self.ref)}"
            f"/loc={quote_long_text(self.loc)}"
        )
        if self.obs is not None and len(self.obs.strip()) > 0:
            r = f"{r}/obs={quote_long_text(self.obs.strip(),width=width)}"
        kleio = super().to_kleio(
            self_string=r,
            ident=ident,
            ident_inc=ident_inc,
            show_contained=show_contained,
            width=width,
        )
        return kleio
