import datetime
from datetime import timedelta
from time import timezone
from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile, Form, File, HTTPException , status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import EmailStr
from sqlalchemy.orm import Session
from models.sign_up_request import UserRequest
from models.token import Token
from tables.users import Users
from utils.cloudinary_upload import create_upload_file
from passlib.context import CryptContext
from database import get_db
from jose import jwt ,JWTError



SECRET_KEY = "VERY SECRET VERY"
ALGO = 'HS256'
oauthbearer = OAuth2PasswordBearer(tokenUrl='/api/v1/user/login')

router = APIRouter(
    prefix='/user',
    tags=['User']
)

bcrypt_context =CryptContext(schemes=['bcrypt'])
db_dependency = Annotated[Session, Depends(get_db)]


async def create_access_token(username: str , id:int , expires_update : timedelta):
    user = {"username": username, "user_id": id}
    expires = datetime.datetime.now(datetime.timezone.utc) + expires_update
    user.update({'exp': expires})
    return jwt.encode(user, SECRET_KEY, algorithm=ALGO)


async def get_current_user(token: Annotated[str, Depends(oauthbearer)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGO])
        username = payload.get('username')
        user_id = payload.get('user_id')

        if id is None or username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='INVALID TOKEN')

        return {'username': username, 'user_id': user_id}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='INVALID TOKEN')




async def verify_password(username: str, password: str, db) :
    user = db.query(Users).filter(Users.username == username).first()
    print(user)
    if not user:
        return False

    if bcrypt_context.verify(password , user.password):
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
) :
    UserRequest(username=username, email=email, password=password, full_name=full_name)

    url = await create_upload_file(file)

    user = Users(
        username=username,
        email=email,
        password=bcrypt_context.hash(password),
        full_name=full_name,
        avatar_url = url
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user

@router.post('/login' , response_model=Token)
async def login( db: db_dependency , form_data : OAuth2PasswordRequestForm = Depends() ):
    username = form_data.username
    password = form_data.password

    user =  await verify_password(username,password ,db)
    print(user)
    if not user:
        raise HTTPException(status_code=401 , detail=['Not authorization'])

    access_token = await create_access_token(user.username , user.id , timedelta(minutes=60))

    return {'access_token' : access_token , 'token_type' : 'bearer'}
