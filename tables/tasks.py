from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from database import Base


class Tasks(Base):
    __tablename__ = 'tasks'
    id = Column(Integer,primary_key=True ,    index=True, autoincrement=True)
    title = Column(String)
    description = Column(String)
    deadline = Column(DateTime )
    owner_id = Column(Integer, ForeignKey("users.id"))

