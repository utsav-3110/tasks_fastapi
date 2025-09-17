from tables.tasks import Tasks
from tables.users import Users


def api_response(success , statuscode , description):
    return {
        'success' : success ,
        'statuscode' : statuscode,
        'data' : description
    }

def serialize_user(user: Users) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "avatar_url": user.avatar_url,
    }


def serialize_task(task : Tasks) -> dict:
    return {
        "task_id" : task.id,
        "task_title" : task.title,
        "task_description": task.description,
        "task_deadline" : task.deadline,
        "task_owner" : task.owner_id
    }