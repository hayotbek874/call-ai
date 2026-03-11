"""
RetailCRM client — inherits from retailcrm v5 SDK.

Only endpoints needed for Stratix AI ChatBot are overridden here.
Every method is typed: request DTO → retailcrm.response.Response.

Library: retailcrm==5.3.0  (pip install retailcrm)
Docs:    https://docs.retailcrm.ru/Developers/API/APIVersions/APIv5
"""

import logging
from functools import wraps

from retailcrm.response import Response as CRMResponse
from retailcrm.versions.v5 import Client as RetailCRMv5

from src.core.logging import get_logger
from src.schemas.crm import (
    CustomerCreate,
    CustomerEdit,
    OrderCreate,
    OrderEdit,
    OrderPaymentCreate,
    OrderPaymentEdit,
    ProductFilter,
    TelephonyCallEvent,
    TelephonyCallRecord,
)

logger = get_logger(__name__)
_sync_logger = logging.getLogger(__name__)


def _log_sync(fn):
    @wraps(fn)
    def wrapper(self, *args, **kwargs):
        _sync_logger.info("retailcrm.%s  args_count=%d", fn.__name__, len(args))
        resp = fn(self, *args, **kwargs)
        if resp and not resp.is_successful():
            _sync_logger.warning(
                "retailcrm.%s.error  status=%s  errors=%s",
                fn.__name__,
                resp.get_status_code(),
                resp.get_errors(),
            )
        return resp
    return wrapper


class CRMClient(RetailCRMv5):

    def __init__(self, crm_url: str, api_key: str) -> None:
        super().__init__(crm_url, api_key)

    @staticmethod
    def _dump(dto) -> dict:
        if isinstance(dto, dict):
            return dto
        return dto.model_dump(by_alias=True, exclude_none=True)

    @_log_sync
    def customer_create(
        self,
        customer: CustomerCreate | dict,
        site: str | None = None,
    ) -> CRMResponse:
        """POST /api/v5/customers/create → ``{success, id}``."""
        return super().customer_create(self._dump(customer), site)

    @_log_sync
    def customer_edit(
        self,
        customer: CustomerEdit | dict,
        uid_type: str = "externalId",
        site: str | None = None,
    ) -> CRMResponse:
        """POST /api/v5/customers/{externalId}/edit → ``{success, id}``."""
        return super().customer_edit(self._dump(customer), uid_type, site)

    @_log_sync
    def customer(
        self,
        uid: str,
        uid_type: str = "externalId",
        site: str | None = None,
    ) -> CRMResponse:
        """GET /api/v5/customers/{externalId} → ``{success, customer}``."""
        return super().customer(uid, uid_type, site)

    @_log_sync
    def customers(
        self,
        filters: dict | None = None,
        limit: int = 20,
        page: int = 1,
    ) -> CRMResponse:
        """GET /api/v5/customers → ``{success, customers[], pagination}``."""
        return super().customers(filters, limit, page)

    @_log_sync
    def order_create(
        self,
        order: OrderCreate | dict,
        site: str | None = None,
    ) -> CRMResponse:
        """POST /api/v5/orders/create → ``{success, id, order}``."""
        return super().order_create(self._dump(order), site)

    @_log_sync
    def order_edit(
        self,
        order: OrderEdit | dict,
        uid_type: str = "externalId",
        site: str | None = None,
    ) -> CRMResponse:
        """POST /api/v5/orders/{externalId}/edit → ``{success, id, order}``."""
        return super().order_edit(self._dump(order), uid_type, site)

    @_log_sync
    def order(
        self,
        uid: str,
        uid_type: str = "externalId",
        site: str | None = None,
    ) -> CRMResponse:
        """GET /api/v5/orders/{externalId} → ``{success, order}``."""
        return super().order(uid, uid_type, site)

    @_log_sync
    def orders(
        self,
        filters: dict | None = None,
        limit: int = 20,
        page: int = 1,
    ) -> CRMResponse:
        """GET /api/v5/orders → ``{success, orders[], pagination}``."""
        return super().orders(filters, limit, page)

    @_log_sync
    def order_payment_create(
        self,
        payment: OrderPaymentCreate | dict,
        site: str | None = None,
    ) -> CRMResponse:
        """POST /api/v5/orders/payments/create → ``{success, id}``."""
        return super().order_payment_create(self._dump(payment), site)

    @_log_sync
    def order_payment_edit(
        self,
        payment: OrderPaymentEdit | dict,
        uid_type: str = "externalId",
        site: str | None = None,
    ) -> CRMResponse:
        """POST /api/v5/orders/payments/{id}/edit → ``{success}``."""
        return super().order_payment_edit(self._dump(payment), uid_type, site)


    @_log_sync
    def products(
        self,
        filters: ProductFilter | dict | None = None,
        limit: int = 20,
        page: int = 1,
    ) -> CRMResponse:
        """GET /api/v5/store/products → ``{success, products[], pagination}``."""
        f = self._dump(filters) if filters else None
        return super().products(f, limit, page)

    @_log_sync
    def product_groups(
        self,
        filters: dict | None = None,
        limit: int = 20,
        page: int = 1,
    ) -> CRMResponse:
        """GET /api/v5/store/product-groups → ``{success, productGroup[]}``."""
        return super().product_groups(filters, limit, page)

    @_log_sync
    def offers(
        self,
        filters: dict | None = None,
        limit: int = 20,
        page: int = 1,
    ) -> CRMResponse:
        """GET /api/v5/store/offers → ``{success, offers[], pagination}``."""
        return super().offers(filters, limit, page)

    @_log_sync
    def inventories(
        self,
        filters: dict | None = None,
        limit: int = 20,
        page: int = 1,
    ) -> CRMResponse:
        """GET /api/v5/store/inventories → ``{success, offers[]}``."""
        return super().inventories(filters, limit, page)


    @_log_sync
    def telephony_call_event(
        self,
        event: TelephonyCallEvent | dict,
    ) -> CRMResponse:
        """POST /api/v5/telephony/call/event → ``{success, status}``."""
        return super().telephony_call_event(self._dump(event))

    @_log_sync
    def telephony_calls_upload(
        self,
        calls: list[TelephonyCallRecord | dict],
    ) -> CRMResponse:
        """POST /api/v5/telephony/calls/upload → ``{success, processedCallsCount}``."""
        payload = [self._dump(c) for c in calls]
        return super().telephony_calls_upload(payload)

    @_log_sync
    def telephony_manager(
        self,
        phone: str,
        details: bool = True,
        ignore_status: bool = True,
    ) -> CRMResponse:
        """GET /api/v5/telephony/manager → ``{success, manager, customer}``."""
        return super().telephony_manager(phone, details, ignore_status)


    @_log_sync
    def statuses(self) -> CRMResponse:
        """GET /api/v5/reference/statuses → ``{success, statuses{}}``."""
        return super().statuses()

    @_log_sync
    def payment_types(self) -> CRMResponse:
        """GET /api/v5/reference/payment-types → ``{success, paymentTypes{}}``."""
        return super().payment_types()

    @_log_sync
    def delivery_types(self) -> CRMResponse:
        """GET /api/v5/reference/delivery-types → ``{success, deliveryTypes{}}``."""
        return super().delivery_types()

    @_log_sync
    def order_methods(self) -> CRMResponse:
        """GET /api/v5/reference/order-methods → ``{success, orderMethods{}}``."""
        return super().order_methods()


    @_log_sync
    def sites(self) -> CRMResponse:
        """GET /api/v5/reference/sites → ``{success, sites{}}``."""
        return super().sites()

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()
    token = os.getenv("CRM_API_KEY")
    print("CRM API Key:", token[:4] + "..." if token else "Not found")
    url = os.getenv("CRM_BASE_URL")
    print("CRM Base URL:", url if url else "Not found")

    crm = CRMClient(crm_url=url, api_key=token)
    print(str(crm.statuses()))
    print(crm.payment_types().get_response())
    print(crm.products().get_response())
