from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from routes.user import get_current_user
from tables.tasks import Tasks
from tables.users import Users
from utils.api_response import api_response

router = APIRouter(
    prefix='/admin',
    tags=['admin']
)

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[Session, Depends(get_current_user)]


@router.get("/tasks")
async def get_all_tasks(user: user_dependency, db: db_dependency):
    try:
        if user.get('role') != 'admin':
            return api_response(False, 401, 'Invalid Credentials')

        tasks = db.query(Tasks).all()
        return tasks

    except Exception as e:
        return api_response(False, 500, f"An error occurred: {str(e)}")


@router.get('/users')
async def get_all_users(user: user_dependency, db: db_dependency):
    try:
        if user.get('role') != 'admin':
            return api_response(False, 401, 'Invalid Credentials')

        users = db.query(Users).all()
        return users

    except Exception as e:
        return api_response(False, 500, f"An error occurred: {str(e)}")
