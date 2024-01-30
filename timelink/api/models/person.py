from typing import Optional

# pylint: disable=import-error
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import mapped_column, Mapped

from timelink.api.models.entity import Entity
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
        r = f"{self.groupname}${quote_long_text(self.name)}/{quote_long_text(self.sex)}/id={quote_long_text(self.id)}"
        if self.obs is not None:
            r = f"{r}/obs={quote_long_text(self.obs)}"
        return r
