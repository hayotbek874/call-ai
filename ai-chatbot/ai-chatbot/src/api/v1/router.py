from fastapi import APIRouter

from src.api.v1.routes.admin import router as admin_router
from src.api.v1.routes.ari import router as ari_router
from src.api.v1.routes.chat import router as chat_router
from src.api.v1.routes.health import router as health_router
from src.api.v1.routes.instagram import router as instagram_router
from src.api.v1.routes.orders import router as orders_router
from src.api.v1.routes.payments import router as payments_router
from src.api.v1.routes.statistics import router as statistics_router
from src.api.v1.routes.users import router as users_router
from src.api.v1.routes.voice import router as voice_router

v1_router = APIRouter()
v1_router.include_router(health_router)
v1_router.include_router(admin_router)
v1_router.include_router(statistics_router)
v1_router.include_router(chat_router)
v1_router.include_router(users_router)
v1_router.include_router(orders_router)
v1_router.include_router(instagram_router)
v1_router.include_router(payments_router)
v1_router.include_router(voice_router)
v1_router.include_router(ari_router)
