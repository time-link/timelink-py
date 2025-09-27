from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import declarative_base
from datetime import datetime

ActivityBase = declarative_base()


class Activity(ActivityBase):
    __tablename__ = 'activity'

    id = Column(Integer, primary_key=True)
    entity_id = Column(String(64), nullable=False)
    entity_type = Column(String(32), nullable=False)
    activity_type = Column(String(32), nullable=False)
    desc = Column(Text(), nullable=True)
    when = Column(DateTime, default=datetime.now, nullable=False)
