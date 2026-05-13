from aiogram import Router

from .course import router as course_router
from .payment import router as payment_router
from .start import router as start_router

router = Router()
router.include_router(start_router)
router.include_router(course_router)
router.include_router(payment_router)
