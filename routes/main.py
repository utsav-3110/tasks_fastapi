from fastapi import APIRouter
from  . import task
from . import user

prefix = '/api/v1'

router = APIRouter(
    prefix=prefix,
)



router.include_router(task.router)
router.include_router(user.router)
