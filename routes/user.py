import datetime
from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, UploadFile, Form, File, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi_limiter.depends import RateLimiter
from pydantic import EmailStr
from sqlalchemy.orm import Session

from models.PatchUser import PatchUserModel
from models.sign_up_request import UserRequest
from models.token import Token
from tables.users import Users
from utils.cloudinary_upload import create_upload_file
from passlib.context import CryptContext
from database import get_db
from jose import jwt, JWTError
from dotenv import load_dotenv
import os

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGO = os.getenv("ALGO")
oauthbearer = OAuth2PasswordBearer(tokenUrl='/api/v1/user/login')

router = APIRouter(
    prefix='/user',
    tags=['User']
)

bcrypt_context = CryptContext(schemes=['bcrypt'])
db_dependency = Annotated[Session, Depends(get_db)]


async def create_access_token(username: str, id: int, expires_update: timedelta):
    user = {"username": username, "user_id": id}
    expires = datetime.datetime.now(datetime.timezone.utc) + expires_update
    user.update({'exp': expires})
    return jwt.encode(user, SECRET_KEY, algorithm=ALGO)


async def get_current_user(token: Annotated[str, Depends(oauthbearer)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGO])
        username = payload.get('username')
        user_id = payload.get('user_id')

        if user_id is None or username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='INVALID TOKEN')

        return {'username': username, 'user_id': user_id}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='INVALID TOKEN')


user_dependency = Annotated[dict, Depends(get_current_user)]


async def verify_password(username: str, password: str, db):
    user = db.query(Users).filter(Users.username == username).first()

    if not user:
        return False

    if bcrypt_context.verify(password, user.password):
        return user

    return False


@router.post('/sign-up')
async def sing_up(
        db: db_dependency,
        username: str = Form(...),
        email: EmailStr = Form(...),
        password: str = Form(...),
        full_name: str = Form(...),
        file: UploadFile = File(...)
):
    UserRequest(username=username, email=email, password=password, full_name=full_name)

    url = await create_upload_file(file)

    user = Users(
        username=username,
        email=email,
        password=bcrypt_context.hash(password),
        full_name=full_name,
        avatar_url=url
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.post('/login', response_model=Token , dependencies=[Depends(RateLimiter(times=5, seconds=60))])
async def login(db: db_dependency, form_data: OAuth2PasswordRequestForm = Depends()):
    username = form_data.username
    password = form_data.password

    user = await verify_password(username, password, db)

    if not user:
        raise HTTPException(status_code=401, detail='Not authorization')

    if user.is_deleted:
        raise HTTPException(status_code=404, detail='Account not found')

    access_token = await create_access_token(user.username, user.id, timedelta(minutes=60))

    return {'access_token': access_token, 'token_type': 'bearer'}


@router.patch('/update')
async def update(data: PatchUserModel, db: db_dependency, user: user_dependency):
    if not user:
        raise HTTPException(status_code=401, detail='Not authorized')

    user_db = db.query(Users).filter(Users.id == user.get('user_id')).first()

    if not user_db:
        raise HTTPException(status_code=404, detail='User not found')

    if user_db.is_deleted:
        raise HTTPException(status_code=404, detail='Account not found')

    if data.email is not None:
        user_db.email = data.email
    if data.full_name is not None:
        user_db.full_name = data.full_name
    if data.password is not None:
        user_db.password = bcrypt_context.hash(data.password)

    db.commit()

    db.refresh(user_db)

    return user_db


@router.post('/change-avatar')
async def update_avatar(db: db_dependency, user: user_dependency, file: UploadFile = File(...)):
    if not user:
        raise HTTPException(status_code=401, detail='Not authorized')

    user_db = db.query(Users).filter(Users.id == user.get('user_id')).first()

    if not user_db:
        raise HTTPException(status_code=404, detail='User not found')

    if user_db.is_deleted:
        raise HTTPException(status_code=404, detail='Account not found')

    url = await create_upload_file(file)

    user_db.avatar_url = url

    db.commit()

    db.refresh(user_db)

    return user_db


@router.delete('/soft-delete')
async def soft_delete(db: db_dependency, user: user_dependency):
    if not user:
        raise HTTPException(status_code=401, detail='Not authorized')

    user_db = db.query(Users).filter(Users.id == user.get('user_id')).first()

    if not user_db:
        raise HTTPException(status_code=404, detail='User not found')

    if user_db.is_deleted:
        raise HTTPException(status_code=404, detail='Account not found')

    user_db.is_deleted = True

    db.commit()

    return {'mes': ' you account is deleted '}


@router.delete('/hard-delete')
async def hard_delete(db: db_dependency, user: user_dependency):
    if not user:
        raise HTTPException(status_code=401, detail='Not authorized')

    user_db = db.query(Users).filter(Users.id == user.get('user_id')).first()

    if not user_db:
        raise HTTPException(status_code=404, detail='User not found')

    if user_db.is_deleted:
        raise HTTPException(status_code=404, detail='Account not found')

    db.delete(user_db)
    db.commit()


