from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class PatchUserModel(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
