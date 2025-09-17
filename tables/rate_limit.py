from sqlalchemy import Column, Integer, String, Boolean, Date
from database import Base


class RateLimit(Base):
    __tablename__ = 'rate_limit'
    id = Column(Integer, primary_key=True , index=True, autoincrement=True)
    email = Column(String(50) , nullable=False , unique=True)
    last_attempt = Column(Date)
    attempt = Column(Integer)


