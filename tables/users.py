from sqlalchemy import Column, Integer , String , Boolean
from database import Base


class Users(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True , index=True, autoincrement=True)
    username = Column(String(20) , nullable=False )
    email = Column(String(50) , nullable=False , unique=True)
    avatar_url = Column(String(250))
    full_name = Column(String(50))
    password = Column(String(100))
    is_deleted = Column(Boolean ,  default=False)
    is_admin = Column(Boolean , default=False)

