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

        return super().customer_create(self._dump(customer), site)

    @_log_sync
    def customer_edit(
        self,
        customer: CustomerEdit | dict,
        uid_type: str = "externalId",
        site: str | None = None,
    ) -> CRMResponse:

        return super().customer_edit(self._dump(customer), uid_type, site)

    @_log_sync
    def customer(
        self,
        uid: str,
        uid_type: str = "externalId",
        site: str | None = None,
    ) -> CRMResponse:

        return super().customer(uid, uid_type, site)

    @_log_sync
    def customers(
        self,
        filters: dict | None = None,
        limit: int = 20,
        page: int = 1,
    ) -> CRMResponse:

        return super().customers(filters, limit, page)

    @_log_sync
    def order_create(
        self,
        order: OrderCreate | dict,
        site: str | None = None,
    ) -> CRMResponse:

        return super().order_create(self._dump(order), site)

    @_log_sync
    def order_edit(
        self,
        order: OrderEdit | dict,
        uid_type: str = "externalId",
        site: str | None = None,
    ) -> CRMResponse:

        return super().order_edit(self._dump(order), uid_type, site)

    @_log_sync
    def order(
        self,
        uid: str,
        uid_type: str = "externalId",
        site: str | None = None,
    ) -> CRMResponse:

        return super().order(uid, uid_type, site)

    @_log_sync
    def orders(
        self,
        filters: dict | None = None,
        limit: int = 20,
        page: int = 1,
    ) -> CRMResponse:

        return super().orders(filters, limit, page)

    @_log_sync
    def order_payment_create(
        self,
        payment: OrderPaymentCreate | dict,
        site: str | None = None,
    ) -> CRMResponse:

        return super().order_payment_create(self._dump(payment), site)

    @_log_sync
    def order_payment_edit(
        self,
        payment: OrderPaymentEdit | dict,
        uid_type: str = "externalId",
        site: str | None = None,
    ) -> CRMResponse:

        return super().order_payment_edit(self._dump(payment), uid_type, site)

    @_log_sync
    def products(
        self,
        filters: ProductFilter | dict | None = None,
        limit: int = 20,
        page: int = 1,
    ) -> CRMResponse:

        f = self._dump(filters) if filters else None
        return super().products(f, limit, page)

    @_log_sync
    def product_groups(
        self,
        filters: dict | None = None,
        limit: int = 20,
        page: int = 1,
    ) -> CRMResponse:

        return super().product_groups(filters, limit, page)

    @_log_sync
    def offers(
        self,
        filters: dict | None = None,
        limit: int = 20,
        page: int = 1,
    ) -> CRMResponse:

        return super().offers(filters, limit, page)

    @_log_sync
    def inventories(
        self,
        filters: dict | None = None,
        limit: int = 20,
        page: int = 1,
    ) -> CRMResponse:

        return super().inventories(filters, limit, page)

    @_log_sync
    def telephony_call_event(
        self,
        event: TelephonyCallEvent | dict,
    ) -> CRMResponse:

        return super().telephony_call_event(self._dump(event))

    @_log_sync
    def telephony_calls_upload(
        self,
        calls: list[TelephonyCallRecord | dict],
    ) -> CRMResponse:

        payload = [self._dump(c) for c in calls]
        return super().telephony_calls_upload(payload)

    @_log_sync
    def telephony_manager(
        self,
        phone: str,
        details: bool = True,
        ignore_status: bool = True,
    ) -> CRMResponse:

        return super().telephony_manager(phone, details, ignore_status)

    @_log_sync
    def statuses(self) -> CRMResponse:

        return super().statuses()

    @_log_sync
    def payment_types(self) -> CRMResponse:

        return super().payment_types()

    @_log_sync
    def delivery_types(self) -> CRMResponse:

        return super().delivery_types()

    @_log_sync
    def order_methods(self) -> CRMResponse:

        return super().order_methods()

    @_log_sync
    def sites(self) -> CRMResponse:

        return super().sites()
