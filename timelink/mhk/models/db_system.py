from sqlalchemy import MetaData, create_engine, select
from sqlalchemy.orm import Session

from timelink.mhk.models import base  # noqa
from timelink.mhk.models.base_class import Base
from timelink.mhk.models.pom_som_mapper import PomSomMapper
from timelink.mhk.models.base_mappings import pom_som_base_mappings

class DBSystem:
    engine = None
    conn_string = None
    metadata: MetaData = None

    def init_db(self, conn_string):
        self.engine = create_engine(conn_string or self.conn_string)
        self.metadata = Base.metadata
        self.metadata.create_all(bind=self.engine)  # only creates if missing
        self.load_base_mappings()

    def load_base_mappings(self):
        with Session(self.engine) as session:
            stmt = select(PomSomMapper.id)
            available_mappings = session.execute(stmt).scalars().all()
            for k in pom_som_base_mappings.keys():
                if k not in available_mappings:
                    data = pom_som_base_mappings[k]
                    session.bulk_save_objects(data)
                    session.commit()



    def db_drop(self):
        self.metadata.drop_all(bind=self.engine)

