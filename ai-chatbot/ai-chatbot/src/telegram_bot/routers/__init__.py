from src.telegram_bot.routers.chat import router as chat_router
from src.telegram_bot.routers.order import router as order_router
from src.telegram_bot.routers.phone import router as phone_router
from src.telegram_bot.routers.start import router as start_router

__all__ = ["start_router", "phone_router", "chat_router", "order_router"]
