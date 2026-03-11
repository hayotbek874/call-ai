from src.api.v1.routes.chat import router as chat_router
from src.api.v1.routes.health import router as health_router
from src.api.v1.routes.instagram import router as instagram_router
from src.api.v1.routes.orders import router as orders_router
from src.api.v1.routes.payments import router as payments_router
from src.api.v1.routes.users import router as users_router

__all__ = [
    "chat_router",
    "health_router",
    "instagram_router",
    "orders_router",
    "payments_router",
    "users_router",
]
