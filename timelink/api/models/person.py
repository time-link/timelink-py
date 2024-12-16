from typing import Optional

# pylint: disable=import-error
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import mapped_column, Mapped

from timelink.kleio.utilities import quote_long_text
from .entity import Entity


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

    def to_kleio(self, self_string='', ident="", ident_inc="  ", show_contained=True, width=80, **kwargs) -> str:
        if self.groupname is None:
            myname = "person"
        else:
            myname = self.groupname
        r = (
            f"{myname}${self.for_kleio('name')}/"
            f"{self.for_kleio('sex')}{self.render_id()}"
        )
        obss = self.for_kleio('obs')
        if len(obss) > 0:
            r = f"{r}/obs={quote_long_text(obss,width=width)}"
        kleio = super().to_kleio(
            self_string=r,
            show_contained=show_contained,
            ident=ident,
            ident_inc=ident_inc,
            width=width,
        )
        return kleio


def get_person(id: str = None, db=None, session=None, sql_echo: bool = False) -> Person:
    """
    Fetch a person from the database
    """
    if id is None:
        raise ValueError("Error, id needed")

    if session is None and db is None:
        raise ValueError("Error, session or database object needed")

    if db is not None:
        session = db.session()

    p: Person = session.get(Person, id)

    return p


def pperson(id: str, session=None):
    """Prints a person in kleio notation"""
    print(get_person(id=id, session=session).to_kleio())
