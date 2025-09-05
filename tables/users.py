from sqlalchemy import Column, Integer , String , Boolean
from database import Base


class Users(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True , index=True, autoincrement=True)
    username = Column(String , nullable=False , unique=True)
    email = Column(String , nullable=False , unique=True)
    avatar_url = Column(String)
    full_name = Column(String)
    password = Column(String)
    is_deleted = Column(Boolean ,  default=False)
    login_attempt = Column(Integer , default=0)

