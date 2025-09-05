from typing import Annotated

from fastapi import APIRouter, Depends
from  fastapi.security import OAuth2PasswordBearer

from routes.user import oauthbearer, get_current_user

user_dependency = Annotated[dict, Depends(get_current_user)]






router = APIRouter(
    prefix='/task',
    tags=['Task']
)

@router.get('/create')
async def task(user : user_dependency):
    return user


