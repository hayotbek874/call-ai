import asyncio
import json
import re
import uuid
from typing import Any

from redis.asyncio import Redis

from src.clients.crm_client import CRMClient
from src.core.logging import get_logger, mask_phone
from src.schemas.crm import (
    Customer,
    CustomerCreate,
    CustomerCreateResponse,
    CustomerEdit,
    CustomersListResponse,
    Order,
    OrderCreate,
    OrderCreateResponse,
    OrderItemCreate,
    OrderResponse,
    OrdersListResponse,
    Product,
    ProductFilter,
    ProductGroup,
    ProductsListResponse,
    ProductGroupsListResponse,
)

logger = get_logger(__name__)

class CRMService:

    PRODUCT_CACHE = "crm:product:{article}"
    SEARCH_CACHE = "crm:search:{query}"
    CATEGORIES_CACHE = "crm:categories"
    CUSTOMER_CACHE = "crm:customer:{phone}"
    CACHE_TTL = 300

    def __init__(self, crm: CRMClient, redis: Redis) -> None:
        self._crm = crm
        self._redis = redis

    ALL_PRODUCTS_CACHE = "crm:all_products"
    ALL_PRODUCTS_TTL = 600

    async def _get_all_products(self) -> list[Product]:

        cached = await self._redis.get(self.ALL_PRODUCTS_CACHE)
        if cached:
            data = json.loads(cached if isinstance(cached, str) else cached.decode())
            return [Product.model_validate(p) for p in data]

        all_products: list[Product] = []
        page = 1

        while True:
            resp = await asyncio.to_thread(
                self._crm.products,
                filters={"active": 1},
                limit=100,
                page=page,
            )

            if not resp or not resp.is_successful():
                break

            raw = resp.get_response()
            parsed = ProductsListResponse.model_validate(raw)

            if not parsed.products:
                break

            all_products.extend(parsed.products)

            if parsed.pagination:
                total_pages = parsed.pagination.total_page_count or 1
                if page >= total_pages:
                    break
            else:
                break

            page += 1

        if all_products:
            await self._redis.setex(
                self.ALL_PRODUCTS_CACHE,
                self.ALL_PRODUCTS_TTL,
                json.dumps([p.model_dump(by_alias=True) for p in all_products]),
            )

        await logger.info(
            "crm_all_products_loaded",
            total_count=len(all_products),
        )
        return all_products

    async def search_products(
        self,
        *,
        query: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        category: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Product], int]:

        await logger.info(
            "crm_search_products_start",
            query=query,
            min_price=min_price,
            max_price=max_price,
            category=category,
            limit=limit,
            offset=offset,
        )

        all_products = await self._get_all_products()

        if not all_products:
            return [], 0

        GENERIC_TERMS = {
            "sovg'a", "sovga", "подарок", "podarok", "gift",
            "zargarlik", "украшение", "ukrasheniye", "jewelry",
            "tovar", "товар", "product", "kerak", "нужно", "qidirish",
            "ищу", "ko'rsating", "покажите", "bor", "есть",
        }

        query_lower = query.lower().strip() if query else None
        is_generic_query = query_lower and any(term in query_lower for term in GENERIC_TERMS)

        filtered: list[Product] = []

        for p in all_products:

            if query_lower and not is_generic_query:
                name_match = p.name and query_lower in p.name.lower()
                article_match = p.article and query_lower in p.article.lower()

                offer_match = False
                if p.offers:
                    for o in p.offers:
                        if o.article and query_lower in o.article.lower():
                            offer_match = True
                            break
                        if o.name and query_lower in o.name.lower():
                            offer_match = True
                            break

                if not (name_match or article_match or offer_match):
                    continue

            if min_price is not None:
                product_price = 0
                if p.offers and p.offers[0].prices:
                    product_price = p.offers[0].prices[0].price or 0
                if product_price < min_price:
                    continue

            if max_price is not None:
                product_price = 0
                if p.offers and p.offers[0].prices:
                    product_price = p.offers[0].prices[0].price or 0
                if product_price > max_price:
                    continue

            if category and p.groups:
                category_match = any(
                    g.external_id == category or g.name == category
                    for g in p.groups
                )
                if not category_match:
                    continue

            filtered.append(p)

        total = len(filtered)
        result = filtered[offset : offset + limit]

        await logger.info(
            "crm_search_products_success",
            query=query,
            total_found=total,
            returned=len(result),
            offset=offset,
        )

        return result, total

    async def get_product_by_article(self, article: str) -> Product | None:

        article_upper = article.upper().strip()
        cache_key = self.PRODUCT_CACHE.format(article=article_upper)
        cached = await self._redis.get(cache_key)
        if cached:
            data = json.loads(cached if isinstance(cached, str) else cached.decode())
            return Product.model_validate(data)

        resp = await asyncio.to_thread(
            self._crm.products,
            filters={"name": article, "active": 1},
            limit=20,
        )

        if not resp or not resp.is_successful():

            resp = await asyncio.to_thread(
                self._crm.products,
                filters={"active": 1},
                limit=100,
            )

        if not resp or not resp.is_successful():
            return None

        raw = resp.get_response()
        parsed = ProductsListResponse.model_validate(raw)
        if not parsed.products:
            return None

        for product in parsed.products:
            if product.article and product.article.upper().strip() == article_upper:
                await self._redis.setex(
                    cache_key,
                    self.CACHE_TTL,
                    json.dumps(product.model_dump(by_alias=True)),
                )
                return product

            if product.offers:
                for offer in product.offers:
                    if offer.article and offer.article.upper().strip() == article_upper:
                        await self._redis.setex(
                            cache_key,
                            self.CACHE_TTL,
                            json.dumps(product.model_dump(by_alias=True)),
                        )
                        return product

        return None

    async def get_categories(self) -> list[ProductGroup]:

        cached = await self._redis.get(self.CATEGORIES_CACHE)
        if cached:
            data = json.loads(cached if isinstance(cached, str) else cached.decode())
            return [ProductGroup.model_validate(g) for g in data]

        resp = await asyncio.to_thread(self._crm.product_groups, limit=100)
        if not resp or not resp.is_successful():
            return []

        raw = resp.get_response()
        parsed = ProductGroupsListResponse.model_validate(raw)
        groups = parsed.product_group

        if groups:
            await self._redis.setex(
                self.CATEGORIES_CACHE,
                self.CACHE_TTL * 6,
                json.dumps([g.model_dump(by_alias=True) for g in groups]),
            )
        return groups

    async def check_product_stock(self, article: str) -> str | None:
        product = await self.get_product_by_article(article)
        if not product:
            return None

        name = product.name or "Без названия"
        lines = [f"Товар: {article} — {name}\n"]

        if not product.offers:
            lines.append("Нет вариантов в наличии.")
            return "\n".join(lines)

        total_qty = 0
        for offer in product.offers:
            qty = int(offer.quantity or 0)
            total_qty += qty
            size = ""
            if offer.properties and isinstance(offer.properties, dict):
                sv = offer.properties.get("size")
                if isinstance(sv, dict):
                    sv = sv.get("value")
                if sv:
                    size = f" (размер {sv})"
            price_str = ""
            if offer.prices:
                price_str = f" — {offer.prices[0].price:,.0f} сум"
            status = "✅ в наличии" if qty > 0 else "❌ нет в наличии"
            lines.append(f"• {offer.name or 'Вариант'}{size}{price_str}: {qty} шт {status}")

        lines.append(f"\nИтого в наличии: {total_qty} шт")
        return "\n".join(lines)

    async def get_product_offers(self, article: str) -> str | None:
        product = await self.get_product_by_article(article)
        if not product:
            return None

        if not product.offers:
            return f"У товара {article} ({product.name}) нет доступных вариантов."

        lines = [f"Варианты товара {article} — {product.name}:\n"]
        for i, offer in enumerate(product.offers, 1):
            size = ""
            color = ""
            if offer.properties and isinstance(offer.properties, dict):
                sv = offer.properties.get("size")
                if isinstance(sv, dict):
                    sv = sv.get("value")
                if sv:
                    size = f"Размер: {sv}"
                cv = offer.properties.get("color")
                if isinstance(cv, dict):
                    cv = cv.get("value")
                if cv:
                    color = f"Цвет: {cv}"

            price_str = "цена не указана"
            if offer.prices:
                price_str = f"{offer.prices[0].price:,.0f} сум"

            qty = int(offer.quantity or 0)
            parts = [f"{i}. {offer.name or 'Вариант'}"]
            if size:
                parts.append(size)
            if color:
                parts.append(color)
            parts.append(f"Цена: {price_str}")
            parts.append(f"В наличии: {qty} шт")
            lines.append(" | ".join(parts))

        return "\n".join(lines)

    async def find_or_create_customer(
        self,
        phone: str,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> Customer | None:
        await logger.info("crm_find_or_create_customer", phone=mask_phone(phone))

        resp = await asyncio.to_thread(
            self._crm.customers,
            filters={"name": phone},
            limit=1,
        )
        if resp and resp.is_successful():
            raw = resp.get_response()
            parsed = CustomersListResponse.model_validate(raw)
            if parsed.customers:
                return parsed.customers[0]
        dto = CustomerCreate(
            first_name=first_name or "Клиент",
            last_name=last_name,
            phones=[{"number": phone}],
            external_id=f"ai_{phone.replace('+', '')}",
            source={"source": "ai-chatbot", "medium": "chat"},
        )
        create_resp = await asyncio.to_thread(self._crm.customer_create, dto)
        if not create_resp or not create_resp.is_successful():
            await logger.warning("crm_customer_create_failed", phone=mask_phone(phone))
            return None

        create_data = CustomerCreateResponse.model_validate(create_resp.get_response())
        await logger.info(
            "crm_customer_created",
            phone=mask_phone(phone),
            crm_id=create_data.id,
        )

        if create_data.id:
            get_resp = await asyncio.to_thread(
                self._crm.customer, str(create_data.id), "id",
            )
            if get_resp and get_resp.is_successful():
                raw_customer = get_resp.get_response().get("customer", {})
                return Customer.model_validate(raw_customer)
        return None

    async def get_customer_by_phone(self, phone: str) -> Customer | None:
        resp = await asyncio.to_thread(
            self._crm.customers,
            filters={"name": phone},
            limit=1,
        )
        if not resp or not resp.is_successful():
            return None
        raw = resp.get_response()
        parsed = CustomersListResponse.model_validate(raw)
        return parsed.customers[0] if parsed.customers else None
    async def create_order(
        self,
        *,
        phone: str,
        first_name: str,
        last_name: str | None = None,
        address: str | None = None,
        items: list[dict],
        delivery_region: str | None = None,
        channel: str = "ai-chatbot",
    ) -> OrderCreateResponse | None:
        await logger.info(
            "crm_create_order",
            phone=mask_phone(phone),
            items_count=len(items),
        )

        customer = await self.find_or_create_customer(phone, first_name, last_name)

        order_items: list[OrderItemCreate] = []
        for item in items:
            oi = OrderItemCreate(
                initial_price=item.get("price", 0),
                quantity=item.get("quantity", 1),
                product_name=item.get("name", "Товар"),
            )

            article = item.get("article")
            if article:
                product = await self.get_product_by_article(article)
                if product and product.offers:
                    oi.offer = {"id": product.offers[0].id}
            order_items.append(oi)

        delivery_cost = 49_000
        if delivery_region and any(
            kw in delivery_region.lower()
            for kw in ("tashkent", "toshkent", "ташкент", "тошкент")
        ):
            delivery_cost = 39_000

        ext_id = f"ai_{uuid.uuid4().hex[:12]}"
        order_dto = OrderCreate(
            external_id=ext_id,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            order_method="phone",
            order_type="eshop",
            items=order_items,
            delivery={
                "code": "courier",
                "cost": delivery_cost,
                "address": {"text": address or ""},
            },
            customer_comment=f"Заказ через AI-чатбот ({channel})",
            source={"source": "ai-chatbot", "medium": channel},
            status="new",
        )
        if customer and customer.id:
            order_dto.customer = {"id": customer.id}

        resp = await asyncio.to_thread(self._crm.order_create, order_dto)
        if not resp or not resp.is_successful():
            await logger.warning("crm_order_create_failed", phone=mask_phone(phone))
            return None

        result = OrderCreateResponse.model_validate(resp.get_response())
        await logger.info(
            "crm_order_created",
            phone=mask_phone(phone),
            order_id=result.id,
        )
        return result

    async def get_customer_orders(
        self,
        phone: str,
        limit: int = 5,
    ) -> list[Order]:

        resp = await asyncio.to_thread(
            self._crm.orders,
            filters={"phone": phone},
            limit=limit,
        )
        if not resp or not resp.is_successful():
            return []

        raw = resp.get_response()
        parsed = OrdersListResponse.model_validate(raw)
        return parsed.orders

    async def get_order_by_id(self, order_id: str) -> Order | None:

        resp = await asyncio.to_thread(self._crm.order, order_id, "id")
        if not resp or not resp.is_successful():
            return None
        raw = resp.get_response()
        parsed = OrderResponse.model_validate(raw)
        return parsed.order

    @staticmethod
    def format_product(p: Product) -> str:
        name = p.name or "Без названия"
        article = p.article or "—"
        desc = p.description or ""

        if desc and "<" in desc:
            desc = re.sub(r"<[^>]+>", "", desc).strip()
        if len(desc) > 200:
            desc = desc[:200] + "…"

        price, qty = 0, 0
        sizes: list[str] = []
        if p.offers:
            first = p.offers[0]
            if first.prices:
                price = first.prices[0].price or 0
            qty = int(first.quantity or 0)
            for o in p.offers:
                if o.properties and isinstance(o.properties, dict):
                    sv = o.properties.get("size")
                    if isinstance(sv, dict):
                        sv = sv.get("value")
                    if sv:
                        sizes.append(str(sv))

        sizes_str = ", ".join(sizes) if sizes else "уточнить"
        return (
            f"Лот: {article} | {name}\n"
            f"Описание: {desc}\n"
            f"Цена: {price:,.0f} сум | В наличии: {qty} шт | Размеры: {sizes_str}"
        )

    @staticmethod
    def format_product_short(p: Product) -> str:
        price = 0
        if p.offers and p.offers[0].prices:
            price = p.offers[0].prices[0].price or 0
        return f"{p.article or '—'} — {p.name} ({price:,.0f} сум)"

    @staticmethod
    def format_order(o: Order) -> str:
        items_str = ""
        if o.items:
            item_lines = []
            for it in o.items:
                n = it.offer.name if it.offer else "Товар"
                item_lines.append(f"  • {n} ×{int(it.quantity or 1)} = {it.initial_price:,.0f} сум")
            items_str = "\n".join(item_lines)

        status = o.status or "unknown"
        total = o.total_summ or 0
        return (
            f"Заказ #{o.id} | Статус: {status}\n"
            f"Товары:\n{items_str}\n"
            f"Итого: {total:,.0f} сум"
        )
