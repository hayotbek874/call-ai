from src.core.logging import get_logger
from src.services.ai.crm_service import CRMService

logger = get_logger(__name__)

class ProductSearchService:

    def __init__(self, crm_service: CRMService) -> None:
        self._crm = crm_service

    async def search_by_lot(self, lot: str | None) -> str | None:

        if not lot:
            return None
        await logger.info("product_search", lot=lot)
        product = await self._crm.get_product_by_article(lot)
        if not product:
            await logger.info("product_not_found", lot=lot)
            return None
        text = self._crm.format_product(product)
        await logger.info("product_found", lot=lot, name=product.name)
        return text

    async def search_by_name(self, query: str, limit: int = 5) -> list[str]:

        if not query:
            return []
        products = await self._crm.search_products(query=query, limit=limit)
        return [self._crm.format_product(p) for p in products]
