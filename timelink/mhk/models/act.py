""" Implementation of Acts in POM model
(c) Joaquim Carvalho 2021.
MIT License, no warranties.
"""
from sqlalchemy import Column, String, ForeignKey
from timelink.mhk.models.entity import Entity


class Act(Entity):
    """Represents an Act, i.e. a record of some event in a historical document.

    Examples of acts are: baptisms, marriages, purchase deeds, wills, court records.

    Attributes:
        id (str): a string uniquely identifying the act.
        the_type (str): the type of the act, e.g.the name of the kleio group that recorded the act.
        the_date (str): the date of the act in Kleio format AAAAMMDD.
        loc (str): location where the act took place (church, notary office,...).
        ref (str): archival reference of the act (page number in the source or equivalent).
        obs (str): any observations or comments on the act.

    """

    __tablename__ = "acts"

    id = Column(String, ForeignKey("entities.id"), primary_key=True)
    the_type = Column(String(32))
    the_date = Column(String)
    loc = Column(String)
    ref = Column(String)
    obs = Column(String)

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
