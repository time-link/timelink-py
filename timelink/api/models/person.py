from typing import Optional

# pylint: disable=import-error
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import mapped_column, Mapped

from .entity import Entity
from timelink.kleio.utilities import quote_long_text


class Person(Entity):
    """Represents a person in a historical source"""

    __tablename__ = "persons"

    id: Mapped[str] = mapped_column(
        String, ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True
    )
    name: Mapped[Optional[str]] = mapped_column(String, index=True)
    sex: Mapped[Optional[str]] = mapped_column(String(1))
    obs: Mapped[Optional[str]] = mapped_column(String)

    __mapper_args__ = {"polymorphic_identity": "person"}

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
        return self.to_kleio()

    def to_kleio(self, ident="", ident_inc="  ", show_contained=True, width=80) -> str:
        r = (
            f"{self.groupname}${quote_long_text(self.name)}/"
            f"{quote_long_text(self.sex)}/id={quote_long_text(self.id)}"
        )
        if self.obs is not None and len(self.obs.strip()) > 0:
            r = f"{r}/obs={quote_long_text(self.obs,width=width)}"
        kleio = super().to_kleio(
            self_string=r,
            show_contained=show_contained,
            ident=ident,
            ident_inc=ident_inc,
            width=width,
        )
        return kleio


def get_person(id: str = None, db=None, sql_echo: bool = False) -> Person:
    """
    Fetch a person from the database
    """
    if id is None:
        raise (Exception("Error, id needed"))
    with db.session() as session:
        p: Person = session.get(Person, id)
    return p


def pperson(id: str):
    """Prints a person in kleio notation"""
    print(get_person(id=id).to_kleio())
