from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class PatchTaskModel(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    deadline: Optional[datetime] = None
