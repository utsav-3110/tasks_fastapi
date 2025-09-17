from datetime import datetime
from typing import Annotated
from fastapi import APIRouter, Depends, Form
from sqlalchemy.orm import Session
from database import get_db
from models.PatchTaskModel import PatchTaskModel
from routes.user import get_current_user
from tables.tasks import Tasks
from tables.users import Users
from utils.api_response import api_response, serialize_task

user_dependency = Annotated[dict, Depends(get_current_user)]
db_dependency = Annotated[Session, Depends(get_db)]

router = APIRouter(
    prefix='/task',
    tags=['Task']
)

async def check_account_status(user_id, db):
    try:
        user = db.query(Users).filter(Users.id == user_id).first()
        if not user or user.is_deleted:
            return True
        return False
    except Exception as e:
        return api_response(False, 500, f"An error occurred while checking account status: {str(e)}")


@router.post('/create')
async def task_create(user: user_dependency, db: db_dependency, title: str = Form(...), description: str = Form(...), deadline: datetime = Form(...)):
    try:
        if not user:
            return api_response(False, 401, "Invalid Authorization header")

        task = Tasks(
            title=title,
            description=description,
            deadline=deadline,
            owner_id=user.get('user_id')
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        return api_response(True, 201, task)

    except Exception as e:
        return api_response(False, 500, f"An error occurred while creating task: {str(e)}")


@router.get('/get-all-task')
async def get_task(user: user_dependency, db: db_dependency, user_id: int | None = None):
    try:

        if not user:
            return api_response(False, 401, "Invalid Authorization header")


        if await check_account_status(user.get("user_id"), db):
            return api_response(False, 404, "User not found")


        if user_id is not None:
            if user.get("role") != "admin":
                return api_response(False, 403, "Forbidden: Admin access required")
            tasks = db.query(Tasks).filter(Tasks.owner_id == user_id).all()
        else:

            tasks = db.query(Tasks).filter(Tasks.owner_id == user.get('user_id')).all()

        if not tasks:
            return api_response(False, 404, "No tasks found")

        return api_response(True, 200, {
            "tasks": [serialize_task(task) for task in tasks]
        })

    except Exception as e:
        return api_response(False, 500, f"An error occurred while retrieving tasks: {str(e)}")


@router.patch('/{task_id}')
async def patch_task(
        task_id: int,
        data: PatchTaskModel,
        user: user_dependency,
        db: db_dependency
):
    try:
        if not user:
            return api_response(False, 401, 'Not authorized')

        if await check_account_status(user.get('user_id'), db):
            return api_response(False, 404, 'No user found')

        task = db.query(Tasks).filter(Tasks.id == task_id).first()

        if not task:
            return api_response(False, 404, 'Task not found')

        if task.owner_id != user.get('user_id') and user.get('role') != 'admin':
            return api_response(False, 401, 'Not authorized')

        if data.title is not None:
            task.title = data.title
        if data.description is not None:
            task.description = data.description
        if data.deadline is not None:
            task.deadline = data.deadline

        db.commit()
        db.refresh(task)

        return api_response(True, 200, task)

    except Exception as e:
        return api_response(False, 500, f"An error occurred while updating task: {str(e)}")


@router.delete('/{task_id}')
async def delete_task(
        task_id: int,
        user: user_dependency,
        db: db_dependency
):
    try:
        if not user:
            return api_response(False, 401, 'Not authorized')

        if await check_account_status(user.get('user_id'), db):
            return api_response(False, 404, 'No user found')

        task = db.query(Tasks).filter(Tasks.id == task_id).first()

        if not task:
            return api_response(False, 404, 'Task not found')

        if task.owner_id != user.get('user_id') and user.get('role') != 'admin':
            return api_response(False, 401, 'Not authorized')

        db.delete(task)
        db.commit()

        return api_response(True, 200, 'Task deleted successfully')

    except Exception as e:
        return api_response(False, 500, f"An error occurred while deleting task: {str(e)}")
