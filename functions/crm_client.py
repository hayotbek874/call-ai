
from __future__ import annotations

from functools import wraps

from retailcrm.versions.v5 import Client as RetailCRMv5

# A placeholder for a real logger
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _log_sync(fn):
    @wraps(fn)
    def wrapper(self, *args, **kwargs):
        logger.info(f"retailcrm.{fn.__name__}", extra={"args_count": len(args)})
        resp = fn(self, *args, **kwargs)
        if resp and not resp.is_successful():
            logger.warning(
                f"retailcrm.{fn.__name__}.error",
                extra={
                    "status": resp.get_status_code(),
                    "errors": resp.get_errors(),
                },
            )
        return resp
    return wrapper


class CRMClient(RetailCRMv5):

    def __init__(self, crm_url: str, api_key: str):
        super().__init__(crm_url, api_key)
    @_log_sync
    def customer_create(self, customer: dict, site: str | None = None):
        return super().customer_create(customer, site)

    @_log_sync
    def customer_edit(self, customer: dict, uid_type: str = "externalId", site: str | None = None):
        return super().customer_edit(customer, uid_type, site)

    @_log_sync
    def customer(self, uid: str, uid_type: str = "externalId", site: str | None = None):
        return super().customer(uid, uid_type, site)

    @_log_sync
    def customers(self, filters: dict | None = None, limit: int = 20, page: int = 1):
        return super().customers(filters, limit, page)

    @_log_sync
    def order_create(self, order: dict, site: str | None = None):
        return super().order_create(order, site)

    @_log_sync
    def order_edit(self, order: dict, uid_type: str = "externalId", site: str | None = None):
        return super().order_edit(order, uid_type, site)

    @_log_sync
    def order(self, uid: str, uid_type: str = "externalId", site: str | None = None):
        return super().order(uid, uid_type, site)

    @_log_sync
    def orders(self, filters: dict | None = None, limit: int = 20, page: int = 1):
        return super().orders(filters, limit, page)

    @_log_sync
    def order_payment_create(self, payment: dict, site: str | None = None):
        return super().order_payment_create(payment, site)

    @_log_sync
    def order_payment_edit(self, payment: dict, uid_type: str = "externalId", site: str | None = None):
        return super().order_payment_edit(payment, uid_type, site)

    @_log_sync
    def products(self, filters: dict | None = None, limit: int = 20, page: int = 1):
        return super().products(filters, limit, page)

    @_log_sync
    def product_groups(self, filters: dict | None = None, limit: int = 20, page: int = 1):
        return super().product_groups(filters, limit, page)

    @_log_sync
    def offers(self, filters: dict | None = None, limit: int = 20, page: int = 1):
        return super().offers(filters, limit, page)

    @_log_sync
    def inventories(self, filters: dict | None = None, limit: int = 20, page: int = 1):
        return super().inventories(filters, limit, page)

    @_log_sync
    def telephony_call_event(self, event: dict):
        return super().telephony_call_event(event)

    @_log_sync
    def telephony_calls_upload(self, calls: list[dict]):
        return super().telephony_calls_upload(calls)

    @_log_sync
    def telephony_manager(self, phone: str, details: bool = True, ignore_status: bool = True):
        return super().telephony_manager(phone, details, ignore_status)
    
    @_log_sync
    def statuses(self):
        return super().statuses()

    @_log_sync
    def payment_types(self):
        return super().payment_types()

    @_log_sync
    def delivery_types(self):
        return super().delivery_types()

    @_log_sync
    def order_methods(self):
        return super().order_methods()

    @_log_sync
    def sites(self):
        return super().sites()

