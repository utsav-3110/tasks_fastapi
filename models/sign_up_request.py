from pydantic import BaseModel, EmailStr, field_validator
import re

class UserRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str

    @field_validator('password')
    @classmethod
    def validate_strong_password(cls, v):  # 👈 use cls, not self
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long.')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter.')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter.')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number.')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character.')
        return v
