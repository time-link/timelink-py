"""
(c) Joaquim Carvalho 2021.
MIT License, no warranties.
"""
from sqlalchemy import Column, String, ForeignKey

from timelink.mhk.models.base import Entity
from timelink.mhk.models.pom_som_mapper import PomSomMapper, PomClassAttributes


class Act(Entity):
    __tablename__ = 'acts'

    id = Column(String, ForeignKey('entities.id'), primary_key=True)
    the_type = Column(String(32))
    the_date = Column(String, index=True)
    loc = Column(String)
    ref = Column(String)
    obs = Column(String)

    __mapper_args__ = {
        'polymorphic_identity': 'act'
    }

    @classmethod
    def get_pom_som_data(cls):
        """
        from timelink.mhk.models.pom_som_mapper import PomSomMapper, \
             PomClassAttributes

        :return: List of PomSomMapper and PomClassAttributes
        """
        return [
            PomSomMapper(id="act", table_name="acts",
                         class_group="historical-act", super_class="entity"),
            PomClassAttributes(the_class="act", name="date",
                               colname="the_date", colclass="the_date",
                               coltype="varchar", colsize="24",
                               colprecision="0", pkey="0"),
            PomClassAttributes(the_class="act", name="id", colname="id",
                               colclass="id", coltype="varchar", colsize="64",
                               colprecision="0", pkey="1"),
            PomClassAttributes(the_class="act", name="loc", colname="loc",
                               colclass="loc", coltype="varchar", colsize="64",
                               colprecision="0", pkey="0"),
            PomClassAttributes(the_class="act", name="obs", colname="obs",
                               colclass="obs", coltype="varchar",
                               colsize="1024", colprecision="0", pkey="0"),
            PomClassAttributes(the_class="act", name="ref", colname="ref",
                               colclass="ref", coltype="varchar", colsize="64",
                               colprecision="0", pkey="0"),
            PomClassAttributes(the_class="act", name="type",
                               colname="the_type", colclass="the_type",
                               coltype="varchar", colsize="32",
                               colprecision="0", pkey="0"),

        ]

    def __repr__(self):
        sr = super().__repr__()
        return (
            f'Act(id={sr}, '
            f'the_type="{self.the_type}", '
            f'the_date="{self.the_date}", '
            f'local="{self.loc}", '
            f'ref="{self.ref}", '
            f'obs={self.obs}'
            f')'
        )

    def __str__(self):
        r = f'{self.groupname}${self.id}/{self.the_date}'
        r += f'/type={self.the_type}/ref={self.ref}/loc={self.loc}'
        if self.obs is not None:
            r = (f'{r}  /obs={self.obs}')
        return r
