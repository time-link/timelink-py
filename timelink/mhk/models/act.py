""" Implementation of Acts in POM model
(c) Joaquim Carvalho 2021.
MIT License, no warranties.
"""

# pylint: disable=import-error
from sqlalchemy import Column, String, ForeignKey

from timelink.mhk.models.entity import Entity
from timelink.kleio.utilities import quote_long_text, kleio_escape


class Act(Entity):
    """Represents an Act, i.e. a record of some event in a historical document.

    Examples of acts are: baptisms, marriages, purchase deeds, wills,
    court records.
    """

    __tablename__ = "acts"

    #: str:  a string uniquely identifying the act
    id = Column(String, ForeignKey("entities.id"), primary_key=True)
    #: str: the type of the act
    the_type = Column(String(32))
    #: str: the date of the act in Kleio format AAAAMMDD
    the_date = Column(String, index=True)
    #: str: location of the act, eg church, notary office
    loc = Column(String)
    ref = Column(String)  #: str: archival reference
    obs = Column(String)  #: any observations or comments.

    __mapper_args__ = {"polymorphic_identity": "act"}

    def __repr__(self):
        """String can be used to instantiate an Act"""
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
        r = (
            f"{self.groupname}${self.id}"
            f"/{self.the_date}"
            f"/type={kleio_escape(self.the_type)}"
            f"/ref={quote_long_text(self.ref)}"
            f"/loc={quote_long_text(self.loc)}"
        )
        if self.obs is not None and len(self.obs.strip()) > 0:
            r = f"{r}/obs={quote_long_text(self.obs)}"
        return r
