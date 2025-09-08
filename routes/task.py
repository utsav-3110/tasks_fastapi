from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session

from database import get_db
from models.PatchTaskModel import PatchTaskModel
from routes.user import oauthbearer, get_current_user
from tables.tasks import Tasks
from tables.users import Users

user_dependency = Annotated[dict, Depends(get_current_user)]
db_dependency = Annotated[Session, Depends(get_db)]

router = APIRouter(
    prefix='/task',
    tags=['Task']
)


async def check_account_status(user_id, db):
    user = db.query(Users).filter(Users.id == user_id).first()

    if not user:
        raise HTTPException(status_code=401, detail='Not authorization')

    return user.is_deleted


@router.post('/create')
async def task_create(title: str, description: str, deadline: datetime, user: user_dependency, db: db_dependency):
    if not user:
        raise HTTPException(status_code=401, detail='Not authorization')

    task = Tasks(
        title=title,
        description=description,
        deadline=deadline,
        owner_id=user.get('user_id')
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    return task


@router.get('/get-all-task')
async def get_task(user: user_dependency, db: db_dependency):
    if not user:
        raise HTTPException(status_code=401, detail='Not authorization')

    if await check_account_status(user.get('user_id'), db):
        raise HTTPException(status_code=404, detail='No user found')

    tasks = db.query(Tasks).filter(Tasks.owner_id == user.get('user_id')).all()

    if not tasks:
        raise HTTPException(status_code=401, detail='No tasks created by you ')

    return tasks


@router.patch('/{task_id}')
async def patch_task(
        task_id: int,
        data: PatchTaskModel,
        user: user_dependency,
        db: db_dependency
):
    if not user:
        raise HTTPException(status_code=401, detail='Not authorized')

    if await check_account_status(user.get('user_id'), db):
        raise HTTPException(status_code=404, detail='No user found')

    task = db.query(Tasks).filter(Tasks.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail='Task not found')

    if task.owner_id != user.get('user_id'):
        raise HTTPException(status_code=401, detail='Not authorized')

    if data.title is not None:
        task.title = data.title
    if data.description is not None:
        task.description = data.description
    if data.deadline is not None:
        task.deadline = data.deadline

    db.commit()
    db.refresh(task)

    return task


@router.delete('/{task_id}')
async def delete_task(
        task_id: int,
        user: user_dependency,
        db: db_dependency
):
    if not user:
        raise HTTPException(status_code=401, detail='Not authorized')

    if await check_account_status(user.get('user_id'), db):
        raise HTTPException(status_code=404, detail='No user found')

    task = db.query(Tasks).filter(Tasks.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail='Task not found')

    if task.owner_id != user.get('user_id'):
        raise HTTPException(status_code=401, detail='Not authorized')

    db.delete(task)
    db.commit()

    return {
        'msg': 'task deleted successfully'
    }
