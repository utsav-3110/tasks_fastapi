import os
from datetime import timedelta, datetime, timezone
from typing import Annotated
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi_limiter.depends import RateLimiter
from jose import jwt, JWTError
from fastapi import APIRouter, HTTPException, Depends, status
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from database import get_db
from models.PatchTaskModel import PatchTaskModel
from models.token import Token
from tables.tasks import Tasks
from tables.users import Users

load_dotenv()

oauthbearer = OAuth2PasswordBearer(tokenUrl='/api/v1/admin/login')
SECRET_KEY = os.getenv("SECRET_KEY")
ALGO = os.getenv("ALGO")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")


async def create_access_token_admin(username: str, expires_delta: timedelta):
    data = {"username": username}
    expire = datetime.now(timezone.utc) + expires_delta
    data.update({"exp": expire})
    return jwt.encode(data, SECRET_KEY, algorithm=ALGO)


async def verfy_admin(token: Annotated[str, Depends(oauthbearer)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGO])
        username = payload.get("username")

        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        if username != ADMIN_USERNAME:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        return {"username": username}

    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


router = APIRouter(
    prefix='/admin',
    tags=['admin']
)

admin_dependency = Annotated[dict, Depends(verfy_admin)]
db_dependency = Annotated[Session, Depends(get_db)]


@router.post("/login", response_model=Token,  dependencies=[Depends(RateLimiter(times=5, seconds=60))])
async def admin_login(form_data: OAuth2PasswordRequestForm = Depends()):
    username = form_data.username
    password = form_data.password

    if username != ADMIN_USERNAME or password != ADMIN_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    access_token = await create_access_token_admin(username, timedelta(minutes=10))

    return {'access_token': access_token, 'token_type': 'bearer'}


@router.get("/tasks")
async def get_all_tasks(admin: admin_dependency, db: db_dependency):
    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    return db.query(Tasks).all()


@router.post('/users')
async def get_all_tasks(admin: admin_dependency, db: db_dependency):
    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    return db.query(Users).all()


@router.patch('/tasks/{task_id}')
async def patch_task(
        task_id: int,
        data: PatchTaskModel,
        db: db_dependency,
        admin : admin_dependency
):
    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    task = db.query(Tasks).filter(Tasks.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail=['Task not found'])

    if data.title is not None:
        task.title = data.title
    if data.description is not None:
        task.description = data.description
    if data.deadline is not None:
        task.deadline = data.deadline

    db.commit()
    db.refresh(task)

    return task


@router.delete('/tasks/{task_id}')
async def delete_task(
        task_id: int,
        db: db_dependency,
        admin : admin_dependency
):
    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


    task = db.query(Tasks).filter(Tasks.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail=['Task not found'])

    db.delete(task)
    db.commit()

    return {
        'msg': 'task deleted successfully'
    }



@router.delete('/user/soft-delete')
async def soft_delete(
        user_id : int,
        db: db_dependency,
        admin: admin_dependency
):

    user = db.query(Users).filter(Users.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail='User not found')

    if user.is_deleted :
        raise HTTPException(status_code=404, detail='User not found')

    user.is_deleted = True

    db.commit()

    return { 'mes' : ' you account is deleted '}




@router.delete('/hard-delete')
async def hard_delete(  user_id : int, db: db_dependency ,  admin : admin_dependency ):

    user = db.query(Users).filter(Users.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail='User not found')



    db.delete(user)
    db.commit()

    return {'mes': ' you account is deleted '}


