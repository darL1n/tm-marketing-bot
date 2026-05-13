from aiogram import Router

from .commands import router as commands_router
from .review import router as review_router

router = Router()
router.include_router(commands_router)
router.include_router(review_router)
