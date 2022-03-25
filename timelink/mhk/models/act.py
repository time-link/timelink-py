""" Implementation of Acts in POM model
(c) Joaquim Carvalho 2021.
MIT License, no warranties.
"""
from sqlalchemy import Column, String, ForeignKey

from timelink.mhk.models.entity import Entity


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
            f'the_type="{self.the_type}", '
            f'the_date="{self.the_date}", '
            f'local="{self.loc}", '
            f'ref="{self.ref}", '
            f'obs="{self.obs}"'
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
