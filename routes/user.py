import datetime
from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, UploadFile, Form, File, HTTPException, status, Header, Body
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
from utils.api_response import api_response

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


async def create_access_token(email: EmailStr,  expires_update: timedelta):
    user = {"email": email}
    expires = datetime.datetime.now(datetime.timezone.utc) + expires_update
    user.update({'exp': expires})
    return jwt.encode(user, SECRET_KEY, algorithm=ALGO)


async def get_current_user(  db : db_dependency,Authorization: str = Header(...) ):
    try:
        payload = jwt.decode(Authorization, SECRET_KEY, algorithms=[ALGO])
        email = payload.get('email')

        if email is None:
            return api_response(False , 401 , 'invalid token')
        print(email)
        user = get_user_by_email(email , db)

        return {'email': email, 'user_id': user.id}
    except JWTError:
        return api_response(False, 401, 'jwt token')


user_dependency = Annotated[dict, Depends(get_current_user)]


async def verify_password(email: EmailStr, password: str, db):
    user = get_user_by_email(email , db)
    print("-============================================================================================================/n",user)
    if not user:
        return False

    if bcrypt_context.verify(password, user.password):
        return user

    return False


def get_user_by_email(email : EmailStr , db):
    return db.query(Users).filter(Users.email == email).first()

def get_user_by_id(id : str , db):
    return db.query(Users.id == id).first()

@router.post('/sign-up')
async def sign_up(
        db: db_dependency,
        username: str = Form(...),
        email: EmailStr = Form(...),
        password: str = Form(...),
        full_name: str = Form(...),
        file: UploadFile = File(...)
):
    try :
        UserRequest(username=username, email=email, password=password, full_name=full_name)

        url = await create_upload_file(file)

        user  = get_user_by_email(email, db)

        if user :
            return api_response(False, 409, {'error': 'Email already exists try to login '})

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

        return api_response(True, 200, {'user': user})

    except Exception as e:
        db.rollback()
        return api_response(False, 404, {'error': str(e.orig.args[1])})


@router.post('/login')
async def login(db: db_dependency, email: EmailStr = Form(...),
        password: str = Form(...)):

    print(email)
    print(password)

    user = await verify_password(email, password, db)

    if not user:
        return api_response(False , 401 , 'Not authrized ')

    if user.is_deleted:
        return api_response(False , 404 , 'account not found ')

    access_token = await create_access_token(user.username, timedelta(minutes=60))

    return api_response(True , 200 , {'access_token': access_token, 'token_type': 'bearer'})

from fastapi import UploadFile, File

@router.patch('/update')
async def update(
    db: db_dependency,
    user: user_dependency,
    file: UploadFile = File(None)  ,
        email: EmailStr = Form(None),
        full_name: str = Form(None),
        password: str = Form(None)
):
    if not user:
        return api_response(False, 404, 'account not found')

    user_db = get_user_by_id(user.get('user_id'), db)

    print('================================================================================')
    print('================================================================================')

    print('================================================================================')
    print(user)
    print('================================================================================')
    print('================================================================================')
    print('================================================================================')



    if not user_db:
        return api_response(False, 404, 'account not found')

    if user_db.is_deleted:
        return api_response(False, 404, 'account not found')

    # Update basic user info if provided
    if email is not None:
        user_db.email = email
    if full_name is not None:
        user_db.full_name = full_name
    if password is not None:
        user_db.password = bcrypt_context.hash(password)

    # Update avatar if file is provided
    if file:
        url = await create_upload_file(file)
        user_db.avatar_url = url

    db.commit()
    db.refresh(user_db)

    return user_db


@router.delete('/soft-delete')
async def soft_delete(db: db_dependency, user: user_dependency):
    if not user:
        return api_response(False, 404, 'account not found ')

    user_db = get_user_by_id(user.get('user_id'), db)

    if not user_db:
        return api_response(False , 404 , 'account not found ')

    if user_db.is_deleted:
        raise HTTPException(status_code=404, detail='Account not found')

    user_db.is_deleted = True

    db.commit()

    return {'mes': ' you account is deleted '}


@router.delete('/hard-delete')
async def hard_delete(db: db_dependency, user: user_dependency):
    if not user:
        raise HTTPException(status_code=404, detail='Account not found')

    user_db = get_user_by_id(user.get('user_id'), db)

    if not user_db:
        raise HTTPException(status_code=404, detail='Account not found')

    if user_db.is_deleted:
        raise HTTPException(status_code=404, detail='Account not found')

    db.delete(user_db)
    db.commit()


