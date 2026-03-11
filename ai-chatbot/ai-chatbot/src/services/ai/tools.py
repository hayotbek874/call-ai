import json
from typing import Any

from src.core.logging import get_logger, mask_phone
from src.services.ai.crm_service import CRMService

logger = get_logger(__name__)

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": (
                "CRM dan tovar qidirish. Mijoz har qanday tovar/zargarlik/sovg'a haqida "
                "gapirsa DARHOL chaqiring. Kalit so'zlar: uzuk, sirg'a, bilakuzuk, "
                "zanjir, kulon, sovg'a, zargarlik, marjon, taqinchoq, oltin, kumush."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Mijoz so'ragan tovar nomi yoki kalit so'z",
                    },
                    "min_price": {
                        "type": "number",
                        "description": "Minimal narx (so'm)",
                    },
                    "max_price": {
                        "type": "number",
                        "description": "Maksimal narx (so'm)",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_details",
            "description": (
                "Artikul bo'yicha tovar ma'lumotini olish. "
                "Mijoz artikul/kod aytganda chaqiring (masalan: KL123, BR45)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "article": {
                        "type": "string",
                        "description": "Tovar artikuli, masalan KL123",
                    },
                },
                "required": ["article"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_order",
            "description": (
                "CRM da yangi buyurtma yaratish. FAQAT barcha ma'lumot yig'ilgandan "
                "va mijoz tasdiqlangandan keyin chaqiring: ism, telefon, manzil, tovar."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {
                        "type": "string",
                        "description": "Telefon raqam, masalan +998901234567",
                    },
                    "first_name": {
                        "type": "string",
                        "description": "Mijoz ismi",
                    },
                    "last_name": {
                        "type": "string",
                        "description": "Mijoz familiyasi",
                    },
                    "address": {
                        "type": "string",
                        "description": "To'liq yetkazish manzili",
                    },
                    "delivery_region": {
                        "type": "string",
                        "description": "Viloyat nomi (Toshkent, Samarqand, ...)",
                    },
                    "items": {
                        "type": "array",
                        "description": "Buyurtma tovarlari",
                        "items": {
                            "type": "object",
                            "properties": {
                                "article": {"type": "string", "description": "Tovar artikuli"},
                                "name": {"type": "string", "description": "Tovar nomi"},
                                "price": {"type": "number", "description": "Narx (so'm)"},
                                "quantity": {"type": "integer", "description": "Soni (default 1)"},
                            },
                            "required": ["name", "price"],
                        },
                    },
                },
                "required": ["phone", "first_name", "address", "delivery_region", "items"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_customer_orders",
            "description": "Mijozning oldingi buyurtmalarini ko'rish. Telefon raqam kerak.",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "description": "Telefon raqam"},
                },
                "required": ["phone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_status",
            "description": "Buyurtma holatini tekshirish. Buyurtma raqami kerak.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "Buyurtma raqami"},
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_product_stock",
            "description": "Tovar mavjudligini tekshirish. Artikul kerak.",
            "parameters": {
                "type": "object",
                "properties": {
                    "article": {"type": "string", "description": "Tovar artikuli"},
                },
                "required": ["article"],
            },
        },
    },
]

class ToolExecutor:
    def __init__(self, crm_service: CRMService) -> None:
        self._crm = crm_service

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> str:
        await logger.info("tool_execute_start", tool=tool_name, args=arguments)

        handler = getattr(self, f"_tool_{tool_name}", None)
        if not handler:
            await logger.warning("tool_not_found", tool=tool_name)
            return json.dumps({"error": f"Noma'lum tool: {tool_name}"}, ensure_ascii=False)

        try:
            result = await handler(**arguments)
            await logger.info(
                "tool_execute_ok", tool=tool_name,
                result_len=len(result), preview=result[:200],
            )
            return result
        except Exception as e:
            await logger.error("tool_execute_error", tool=tool_name, error=str(e))
            return json.dumps(
                {"error": f"CRM xatolik: {e}. Qayta urinib ko'ring."},
                ensure_ascii=False,
            )

    async def _tool_search_products(
        self,
        query: str,
        min_price: float | None = None,
        max_price: float | None = None,
    ) -> str:
        products, total = await self._crm.search_products(
            query=query, min_price=min_price, max_price=max_price, limit=5,
        )

        if not products:
            return json.dumps(
                {"found": 0, "message": "Tovar topilmadi. Boshqa kalit so'z bilan qidiring."},
                ensure_ascii=False,
            )

        items = []
        for p in products:
            price = 0
            qty = 0
            if p.offers and p.offers[0].prices:
                price = p.offers[0].prices[0].price or 0
            if p.offers:
                qty = int(p.offers[0].quantity or 0)
            items.append({
                "article": p.article or "—",
                "name": p.name or "Nomsiz",
                "price": price,
                "stock": qty,
            })

        return json.dumps(
            {"found": total, "showing": len(items), "products": items},
            ensure_ascii=False,
        )

    async def _tool_get_product_details(self, article: str) -> str:
        product = await self._crm.get_product_by_article(article)
        if not product:
            return json.dumps(
                {"error": f"Artikul {article} topilmadi."},
                ensure_ascii=False,
            )
        return self._crm.format_product(product)

    async def _tool_create_order(
        self,
        phone: str,
        first_name: str,
        items: list[dict],
        last_name: str | None = None,
        address: str | None = None,
        delivery_region: str | None = None,
    ) -> str:
        await logger.info(
            "tool_create_order",
            phone=phone[-4:],
            name=first_name,
            items_count=len(items),
        )

        result = await self._crm.create_order(
            phone=phone,
            first_name=first_name,
            last_name=last_name,
            address=address,
            items=items,
            delivery_region=delivery_region,
        )

        if not result:
            return json.dumps(
                {"error": "Buyurtma yaratilmadi. CRM xatolik. Qayta urinib ko'ring."},
                ensure_ascii=False,
            )

        is_tashkent = delivery_region and any(
            kw in delivery_region.lower()
            for kw in ("tashkent", "toshkent", "ташкент", "тошкент")
        )
        delivery_cost = 39_000 if is_tashkent else 49_000
        item_total = sum(it.get("price", 0) * it.get("quantity", 1) for it in items)

        return json.dumps({
            "success": True,
            "order_id": result.id,
            "customer": first_name,
            "phone": phone,
            "items_total": item_total,
            "delivery_cost": delivery_cost,
            "grand_total": item_total + delivery_cost,
            "delivery_region": delivery_region or "noma'lum",
        }, ensure_ascii=False)

    async def _tool_get_customer_orders(self, phone: str) -> str:
        orders = await self._crm.get_customer_orders(phone)
        if not orders:
            return json.dumps({"orders": [], "message": "Buyurtmalar topilmadi."}, ensure_ascii=False)

        items = []
        for o in orders:
            items.append({
                "id": o.id,
                "status": o.status,
                "total": o.total_summ or 0,
            })
        return json.dumps({"orders": items}, ensure_ascii=False)

    async def _tool_get_order_status(self, order_id: str) -> str:
        order = await self._crm.get_order_by_id(order_id)
        if not order:
            return json.dumps({"error": f"Buyurtma #{order_id} topilmadi."}, ensure_ascii=False)
        return json.dumps({
            "id": order.id,
            "status": order.status,
            "total": order.total_summ or 0,
        }, ensure_ascii=False)

    async def _tool_check_product_stock(self, article: str) -> str:
        stock = await self._crm.check_product_stock(article)
        if not stock:
            return json.dumps({"error": f"Artikul {article} topilmadi."}, ensure_ascii=False)
        return stock
