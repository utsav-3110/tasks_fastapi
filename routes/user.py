import datetime
from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, UploadFile, Form, File, Header
from pydantic import EmailStr
from sqlalchemy.orm import Session
from models.sign_up_request import UserRequest
from tables.rate_limit import RateLimit
from tables.users import Users
from utils.cloudinary_upload import create_upload_file
from passlib.context import CryptContext
from database import get_db
from utils.api_response import api_response, serialize_user
from jose import jwt, JWTError
from dotenv import load_dotenv
import re
import os


#loads the env file

load_dotenv()


#scret key and algo from env file
SECRET_KEY = os.getenv("SECRET_KEY")
ALGO = os.getenv("ALGO")


#router prefix for example /users /tasks and tags for docs
router = APIRouter(
    prefix='/user',
    tags=['User']
)

# creating context for encrypt and decrypt the password
bcrypt_context = CryptContext(schemes=['bcrypt'])

# creating users dependency type -> Session (from sql alchemy) -> depends on get
db_dependency = Annotated[Session, Depends(get_db)]


async def create_access_token(email: EmailStr, expires_update: timedelta):
    try:
        user = {"email": email}
        expires = datetime.datetime.now(datetime.timezone.utc) + expires_update
        user.update({'exp': expires})
        return jwt.encode(user, SECRET_KEY, algorithm=ALGO)
    except Exception as e:
        return api_response(False, 500, f"Error creating access token: {str(e)}")


async def get_current_user(db: db_dependency, Authorization: str = Header(...)):
    try:
        if not Authorization or not (Authorization.startswith("Bearer ") or Authorization.startswith("bearer ")):
            return api_response(False, 401, "Invalid Authorization header")

        token = Authorization.split()[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGO])

        email = payload.get('email')

        if email is None:
            return api_response(False, 401, 'Invalid token')

        user = get_user_by_email(email, db)


        if not user:
            return api_response(False, 404, 'Account not found')

        if user.is_admin:
            return {'email': email, 'user_id': user.id, 'role': 'admin'}

        return {'email': email, 'user_id': user.id}
    except JWTError as e:
        print(f'JWT token error: {str(e)}')
        return False
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return False



user_dependency = Annotated[dict, Depends(get_current_user)]


async def verify_password(email: EmailStr, password: str, db):
    try:
        user = get_user_by_email(email, db)
        if user and bcrypt_context.verify(password, user.password):
            return user
        return False
    except Exception as e:
        return api_response(False, 500, f"Error verifying password: {str(e)}")


def get_user_by_email(email: EmailStr, db: db_dependency):
    try:
        return db.query(Users).filter(Users.email == email).first()
    except Exception as e:
        print(f"Error fetching user by email: {str(e)}")
        return None



def get_user_by_id(id: str, db: db_dependency):
    try:
        return db.query(Users).filter(Users.id == id).first()
    except Exception as e:
        print(f"Error fetching user by ID: {str(e)}")
        return None




def set_rate_limiter(email: EmailStr, db):
    try:
        user = db.query(RateLimit).filter(RateLimit.email == email).first()
        today = datetime.date.today()

        if not user:
            db.add(RateLimit(email=email, attempt=1, attempt_date=today))
            db.commit()
            return True

        if user.attempt_date != today:
            user.attempt = 1
            user.attempt_date = today
            db.commit()
            return True

        # Same day → check limit
        if user.attempt >= 5:
            return False

        user.attempt += 1
        db.commit()
        return True

    except Exception as e:
        return api_response(False, 500, f"Error setting the rate limiter : {str(e)}")

def reset_rate_limit(email : EmailStr , db):
    try:
        user = db.query(RateLimit).filter(RateLimit.email == email).first()
        db.delete(user)
        db.commit()
    except Exception as e:
        return api_response(False, 500, f"Error resetting the rate limiter  {str(e)}")



@router.post('/sign-up')
async def sign_up(
        db: db_dependency,
        username: str = Form(...),
        email: EmailStr = Form(...),
        password: str = Form(...),
        full_name: str = Form(...),
        file: UploadFile = File(...)
):
    try:
        # Validate request data
        UserRequest(username=username, email=email, password=password, full_name=full_name)

        # Upload avatar
        url = await create_upload_file(file)

        # Check if the user already exists
        user = get_user_by_email(email, db)
        if user:
            return api_response(False, 409, {'error': 'Email already exists, try to login'})


        if len(password) < 8:
            return api_response(False, 400, {'error': 'Password must be at least 8 characters long.'})
        if not re.search(r'[A-Z]', password):
            return api_response(False, 400, {'error': 'Password must contain at least one uppercase letter.'})
        if not re.search(r'[a-z]', password):
            return api_response(False, 400, {'error': 'Password must contain at least one lowercase letter.'})
        if not re.search(r'\d', password):
            return api_response(False, 400, {'error': 'Password must contain at least one number.'})
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return api_response(False, 400, {'error': 'Password must contain at least one special character.'})


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

        return api_response(True, 200, {'user': serialize_user(user)})

    except Exception as e:
        db.rollback()
        return api_response(False, 404, {'error': f"Error signing up: {str(e)}"})


@router.post('/login')
async def login(
        db: db_dependency,
        email: EmailStr = Form(...),
        password: str = Form(...)
):
    try:
        if not set_rate_limiter(email , db):
            return api_response(False, 429, "Too Many request try to login after 24 hours")

        user = await verify_password(email, password, db)

        if not user:
            return api_response(False, 401, 'Invalid credentials')

        if user.is_deleted:
            return api_response(False, 404, 'Account not found')

        access_token = await create_access_token(user.email, timedelta(minutes=60))

        reset_rate_limit(email , db)

        return api_response(True, 200, {
            'access_token': access_token,
            'token_type': 'bearer'
        })

    except Exception as e:
        return api_response(False, 500, f"Error during login: {str(e)}")


@router.patch('/update')
async def update(
        db: db_dependency,
        user: user_dependency,
        file: UploadFile = File(None),
        email: EmailStr = Form(None),
        full_name: str = Form(None),
        password: str = Form(None),
        user_id: int | None = None,
):
    try:

        if not user:
            return api_response(False, 404, 'Account not found')


        if user_id is not None:
            if user.get("role") != "admin":
                return api_response(False, 403, "Forbidden: Admin access required")
            user_db =  get_user_by_id(str(user_id), db)
        else:
            user_db =  get_user_by_id(user.get('user_id'), db)




        if not user_db:
            return api_response(False, 404, 'Account not found')

        if user_db.is_deleted and user.get("role") != "admin":
            return api_response(False, 404, 'Account not found')

        if email is not None:
            user_db.email = email
        if full_name is not None:
            user_db.full_name = full_name
        if password is not None:
            user_db.password = bcrypt_context.hash(password)

        if file:
            url = await create_upload_file(file)
            user_db.avatar_url = url

        db.commit()
        db.refresh(user_db)

        return api_response(True, 200, serialize_user(user_db))

    except Exception as e:
        db.rollback()
        return api_response(False, 500, f"Error updating user: {str(e)}")


@router.delete('/soft-delete')
async def soft_delete(db: db_dependency, user: user_dependency):
    try:
        if not user:
            return api_response(False, 404, 'Account not found')

        user_db = get_user_by_id(user.get('user_id'), db)

        if not user_db:
            return api_response(False, 404, 'Account not found')

        if user_db.is_deleted:
            return api_response(False, 404, 'Account not found')

        if user_db.id != user.get('user_id') and user.get('role') != 'admin':
            return api_response(False, 401, 'Not authorized')

        user_db.is_deleted = True

        db.commit()

        return api_response(True, 200, 'Your account is deleted')

    except Exception as e:
        db.rollback()
        return api_response(False, 500, f"Error during soft delete: {str(e)}")


@router.delete('/hard-delete')
async def hard_delete(db: db_dependency, user: user_dependency):
    try:
        if not user:
            return api_response(False, 404, 'Account not found')

        user_db = get_user_by_id(user.get('user_id'), db)

        if not user_db:
            return api_response(False, 404, 'Account not found')

        if user_db.id != user.get('user_id') and user.get('role') != 'admin':
            return api_response(False, 401, 'Not authorized')

        db.delete(user_db)
        db.commit()

        return api_response(True, 200, 'Your account is deleted')

    except Exception as e:
        db.rollback()
        return api_response(False, 500, f"Error during hard delete: {str(e)}")
