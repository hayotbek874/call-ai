from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

class ContragentType(StrEnum):
    INDIVIDUAL = "individual"
    LEGAL_ENTITY = "legal-entity"
    ENTREPRENEUR = "enterpreneur"

class CustomerType(StrEnum):
    CUSTOMER = "customer"
    CUSTOMER_CORPORATE = "customer_corporate"

class Sex(StrEnum):
    MALE = "male"
    FEMALE = "female"

class CallType(StrEnum):
    IN = "in"
    OUT = "out"

class CallHangupStatus(StrEnum):
    ANSWERED = "answered"
    BUSY = "busy"
    CANCEL = "cancel"
    NO_ANSWER = "no answer"
    FAILED = "failed"

class PrivilegeType(StrEnum):
    PERSONAL_DISCOUNT = "personal_discount"
    LOYALTY_LEVEL = "loyalty_level"
    LOYALTY_EVENT = "loyalty_event"
    NONE = "none"

class MarkingProvider(StrEnum):
    CHESTNY_ZNAK = "chestny_znak"
    GIIS_DMDK = "giis_dmdk"

class CRMBase(BaseModel):

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        from_attributes=True,
        extra="allow",
    )

class CRMPagination(CRMBase):

    limit: int = 20
    total_count: int = Field(0, alias="totalCount")
    current_page: int = Field(1, alias="currentPage")
    total_page_count: int = Field(1, alias="totalPageCount")

class Address(CRMBase):

    id: int | None = None
    index: str | None = None
    country_iso: str | None = Field(None, alias="countryIso")
    region: str | None = None
    region_id: int | None = Field(None, alias="regionId")
    city: str | None = None
    city_id: int | None = Field(None, alias="cityId")
    city_type: str | None = Field(None, alias="cityType")
    street: str | None = None
    street_id: int | None = Field(None, alias="streetId")
    street_type: str | None = Field(None, alias="streetType")
    building: str | None = None
    flat: str | None = None
    floor: int | None = None
    block: int | None = None
    house: str | None = None
    housing: str | None = None
    metro: str | None = None
    notes: str | None = None
    text: str | None = None
    external_id: str | None = Field(None, alias="externalId")
    name: str | None = None

class Source(CRMBase):

    source: str | None = None
    medium: str | None = None
    campaign: str | None = None
    keyword: str | None = None
    content: str | None = None

class Contragent(CRMBase):

    contragent_type: ContragentType | None = Field(None, alias="contragentType")
    legal_name: str | None = Field(None, alias="legalName")
    legal_address: str | None = Field(None, alias="legalAddress")
    inn: str | None = Field(None, alias="INN")
    okpo: str | None = Field(None, alias="OKPO")
    kpp: str | None = Field(None, alias="KPP")
    ogrn: str | None = Field(None, alias="OGRN")
    ogrnip: str | None = Field(None, alias="OGRNIP")
    certificate_number: str | None = Field(None, alias="certificateNumber")
    certificate_date: date | None = Field(None, alias="certificateDate")
    bik: str | None = Field(None, alias="BIK")
    bank: str | None = None
    bank_address: str | None = Field(None, alias="bankAddress")
    corr_account: str | None = Field(None, alias="corrAccount")
    bank_account: str | None = Field(None, alias="bankAccount")

class Phone(CRMBase):
    number: str | None = None

class CustomerCreate(CRMBase):

    external_id: str | None = Field(None, alias="externalId")
    is_contact: bool | None = Field(None, alias="isContact")
    created_at: datetime | None = Field(None, alias="createdAt")
    vip: bool | None = None
    bad: bool | None = None
    contragent: Contragent | None = None
    custom_fields: dict[str, Any] | None = Field(None, alias="customFields")
    personal_discount: float | None = Field(None, alias="personalDiscount")
    discount_card_number: str | None = Field(None, alias="discountCardNumber")
    address: Address | None = None
    first_name: str | None = Field(None, alias="firstName")
    last_name: str | None = Field(None, alias="lastName")
    patronymic: str | None = None
    email: str | None = None
    phones: list[Phone] | None = None
    birthday: date | None = None
    photo_url: str | None = Field(None, alias="photoUrl")
    manager_id: int | None = Field(None, alias="managerId")
    sex: Sex | None = None
    source: Source | None = None
    subscribed: bool | None = None
    tags: list[str] | None = None
    attached_tag: str | None = Field(None, alias="attachedTag")
    browser_id: str | None = Field(None, alias="browserId")

class CustomerEdit(CustomerCreate):
    pass

class CustomerPhone(CRMBase):
    number: str | None = None

class CustomerTag(CRMBase):
    name: str | None = None
    color: str | None = None
    color_code: str | None = Field(None, alias="colorCode")
    attached: bool | None = None

class Segment(CRMBase):
    id: int | None = None
    code: str | None = None
    name: str | None = None
    created_at: datetime | None = Field(None, alias="createdAt")
    is_dynamic: bool | None = Field(None, alias="isDynamic")
    customers_count: int | None = Field(None, alias="customersCount")
    active: bool | None = None

class Subscription(CRMBase):
    id: int | None = None
    channel: str | None = None
    name: str | None = None
    code: str | None = None
    active: bool | None = None
    auto_subscribe: bool | None = Field(None, alias="autoSubscribe")
    ordering: int | None = None

class CustomerSubscription(CRMBase):
    subscription: Subscription | None = None
    subscribed: bool | None = None
    changed_at: datetime | None = Field(None, alias="changedAt")

class MGChannel(CRMBase):
    id: int | None = None
    external_id: int | None = Field(None, alias="externalId")
    type: str | None = None
    active: bool | None = None
    name: str | None = None
    allowed_send_by_phone: bool | None = Field(None, alias="allowedSendByPhone")

class MGCustomer(CRMBase):
    id: int | None = None
    external_id: int | None = Field(None, alias="externalId")
    mg_channel: MGChannel | None = Field(None, alias="mgChannel")

class Customer(CRMBase):

    type: CustomerType | None = None
    id: int | None = None
    external_id: str | None = Field(None, alias="externalId")
    is_contact: bool | None = Field(None, alias="isContact")
    created_at: datetime | None = Field(None, alias="createdAt")
    manager_id: int | None = Field(None, alias="managerId")
    vip: bool | None = None
    bad: bool | None = None
    site: str | None = None
    contragent: Contragent | None = None
    tags: list[CustomerTag] | None = None
    first_client_id: str | None = Field(None, alias="firstClientId")
    last_client_id: str | None = Field(None, alias="lastClientId")
    custom_fields: dict[str, Any] | None = Field(None, alias="customFields")
    personal_discount: float | None = Field(None, alias="personalDiscount")
    discount_card_number: str | None = Field(None, alias="discountCardNumber")
    avg_margin_summ: float | None = Field(None, alias="avgMarginSumm")
    margin_summ: float | None = Field(None, alias="marginSumm")
    total_summ: float | None = Field(None, alias="totalSumm")
    average_summ: float | None = Field(None, alias="averageSumm")
    orders_count: int | None = Field(None, alias="ordersCount")
    cost_summ: float | None = Field(None, alias="costSumm")
    address: Address | None = None
    segments: list[Segment] | None = None
    maturation_time: int | None = Field(None, alias="maturationTime")
    first_name: str | None = Field(None, alias="firstName")
    last_name: str | None = Field(None, alias="lastName")
    patronymic: str | None = None
    sex: Sex | None = None
    presumable_sex: str | None = Field(None, alias="presumableSex")
    email: str | None = None
    customer_subscriptions: list[CustomerSubscription] | None = Field(
        None, alias="customerSubscriptions",
    )
    phones: list[CustomerPhone] | None = None
    birthday: date | None = None
    source: Source | None = None
    mg_customers: list[MGCustomer] | None = Field(None, alias="mgCustomers")
    photo_url: str | None = Field(None, alias="photoUrl")

class CustomerResponse(CRMBase):

    success: bool = True
    customer: Customer | None = None

class CustomersListResponse(CRMBase):

    success: bool = True
    customers: list[Customer] = Field(default_factory=list)
    pagination: CRMPagination | None = None

class CustomerCreateResponse(CRMBase):

    success: bool = True
    id: int | None = None

class OrderItemProperty(CRMBase):

    code: str | None = None
    name: str | None = None
    value: str | None = None

class OrderItemOffer(CRMBase):

    id: int | None = None
    external_id: str | None = Field(None, alias="externalId")
    xml_id: str | None = Field(None, alias="xmlId")

class MarkingObject(CRMBase):
    code: str | None = None
    provider: MarkingProvider | None = None

class CodeValue(CRMBase):
    code: str | None = None
    value: str | None = None

class PriceType(CRMBase):
    code: str | None = None

class OrderItemCreate(CRMBase):

    initial_price: float | None = Field(None, alias="initialPrice")
    discount_manual_amount: float | None = Field(None, alias="discountManualAmount")
    discount_manual_percent: float | None = Field(None, alias="discountManualPercent")
    vat_rate: str | None = Field(None, alias="vatRate")
    created_at: datetime | None = Field(None, alias="createdAt")
    quantity: float | None = None
    comment: str | None = None
    properties: list[OrderItemProperty] | None = None
    purchase_price: float | None = Field(None, alias="purchasePrice")
    ordering: int | None = None
    offer: OrderItemOffer | None = None
    product_name: str | None = Field(None, alias="productName")
    status: str | None = None
    price_type: PriceType | None = Field(None, alias="priceType")
    external_ids: list[CodeValue] | None = Field(None, alias="externalIds")
    marking_objects: list[MarkingObject] | None = Field(None, alias="markingObjects")

class TimeInterval(CRMBase):
    from_time: str | None = Field(None, alias="from")
    to_time: str | None = Field(None, alias="to")
    custom: str | None = None

class DeliveryServiceInput(CRMBase):
    name: str | None = None
    code: str | None = None
    active: bool | None = None
    delivery_type: str | None = Field(None, alias="deliveryType")

class PackageItemOrderProduct(CRMBase):
    id: int | None = None
    external_ids: list[CodeValue] | None = Field(None, alias="externalIds")

class DeclaredValueItem(CRMBase):
    order_product: PackageItemOrderProduct | None = Field(None, alias="orderProduct")
    value: float | None = None

class PackageItem(CRMBase):
    order_product: PackageItemOrderProduct | None = Field(None, alias="orderProduct")
    quantity: float | None = None

class Package(CRMBase):
    package_id: str | None = Field(None, alias="packageId")
    weight: float | None = None
    length: int | None = None
    width: int | None = None
    height: int | None = None
    items: list[PackageItem] | None = None

class DeliveryDataInput(CRMBase):

    external_id: str | None = Field(None, alias="externalId")
    track_number: str | None = Field(None, alias="trackNumber")
    locked: bool | None = None
    tariff: str | None = None
    pickuppoint_id: str | None = Field(None, alias="pickuppointId")
    payer_type: str | None = Field(None, alias="payerType")
    shipmentpoint_id: str | None = Field(None, alias="shipmentpointId")
    extra_data: dict[str, Any] | None = Field(None, alias="extraData")
    item_declared_values: list[DeclaredValueItem] | None = Field(
        None, alias="itemDeclaredValues",
    )
    packages: list[Package] | None = None

class OrderDeliveryInput(CRMBase):

    code: str | None = None
    data: DeliveryDataInput | None = None
    service: DeliveryServiceInput | None = None
    cost: float | None = None
    net_cost: float | None = Field(None, alias="netCost")
    delivery_date: date | None = Field(None, alias="date")
    time: TimeInterval | None = None
    address: Address | None = None
    vat_rate: str | None = Field(None, alias="vatRate")

class OrderPaymentInput(CRMBase):

    external_id: str | None = Field(None, alias="externalId")
    amount: float | None = None
    paid_at: datetime | None = Field(None, alias="paidAt")
    comment: str | None = None
    type: str | None = None
    status: str | None = None

class OrderCustomerInput(CRMBase):

    id: int | None = None
    external_id: str | None = Field(None, alias="externalId")
    browser_id: str | None = Field(None, alias="browserId")
    site: str | None = None
    type: CustomerType | None = None
    nick_name: str | None = Field(None, alias="nickName")

class EntityWithExternalId(CRMBase):
    id: int | None = None
    external_id: str | None = Field(None, alias="externalId")

class OrderCreate(CRMBase):

    number: str | None = None
    external_id: str | None = Field(None, alias="externalId")
    privilege_type: PrivilegeType | None = Field(None, alias="privilegeType")
    country_iso: str | None = Field(None, alias="countryIso")
    created_at: datetime | None = Field(None, alias="createdAt")
    status_updated_at: datetime | None = Field(None, alias="statusUpdatedAt")
    discount_manual_amount: float | None = Field(None, alias="discountManualAmount")
    discount_manual_percent: float | None = Field(None, alias="discountManualPercent")
    mark: int | None = None
    mark_datetime: datetime | None = Field(None, alias="markDatetime")
    last_name: str | None = Field(None, alias="lastName")
    first_name: str | None = Field(None, alias="firstName")
    patronymic: str | None = None
    phone: str | None = None
    additional_phone: str | None = Field(None, alias="additionalPhone")
    email: str | None = None
    call: bool | None = None
    expired: bool | None = None
    customer_comment: str | None = Field(None, alias="customerComment")
    manager_comment: str | None = Field(None, alias="managerComment")
    contragent: Contragent | None = None
    status_comment: str | None = Field(None, alias="statusComment")
    weight: float | None = None
    length: int | None = None
    width: int | None = None
    height: int | None = None
    shipment_date: date | None = Field(None, alias="shipmentDate")
    shipped: bool | None = None
    custom_fields: dict[str, Any] | None = Field(None, alias="customFields")
    order_type: str | None = Field(None, alias="orderType")
    order_method: str | None = Field(None, alias="orderMethod")
    customer: OrderCustomerInput | None = None
    contact: EntityWithExternalId | None = None
    company: EntityWithExternalId | None = None
    manager_id: int | None = Field(None, alias="managerId")
    status: str | None = None
    items: list[OrderItemCreate] | None = None
    delivery: OrderDeliveryInput | None = None
    source: Source | None = None
    shipment_store: str | None = Field(None, alias="shipmentStore")
    payments: list[OrderPaymentInput] | None = None
    loyalty_event_discount_id: int | None = Field(None, alias="loyaltyEventDiscountId")
    apply_round: bool | None = Field(None, alias="applyRound")
    is_from_cart: bool | None = Field(None, alias="isFromCart")

class OrderEdit(OrderCreate):
    pass

class OfferResponse(CRMBase):

    display_name: str | None = Field(None, alias="displayName")
    id: int | None = None
    external_id: str | None = Field(None, alias="externalId")
    xml_id: str | None = Field(None, alias="xmlId")
    name: str | None = None
    article: str | None = None
    vat_rate: str | None = Field(None, alias="vatRate")
    properties: dict[str, Any] | None = None
    unit: dict[str, Any] | None = None
    barcode: str | None = None

class OrderItemDiscount(CRMBase):
    type: str | None = None
    amount: float | None = None

class OrderItemPriceEntry(CRMBase):
    price: float | None = None
    quantity: float | None = None

class OrderItem(CRMBase):

    id: int | None = None
    external_ids: list[CodeValue] | None = Field(None, alias="externalIds")
    price_type: PriceType | None = Field(None, alias="priceType")
    initial_price: float | None = Field(None, alias="initialPrice")
    discounts: list[OrderItemDiscount] | None = None
    discount_total: float | None = Field(None, alias="discountTotal")
    prices: list[OrderItemPriceEntry] | None = None
    vat_rate: str | None = Field(None, alias="vatRate")
    created_at: datetime | None = Field(None, alias="createdAt")
    quantity: float | None = None
    status: str | None = None
    comment: str | None = None
    offer: OfferResponse | None = None
    is_canceled: bool | None = Field(None, alias="isCanceled")
    properties: list[OrderItemProperty] | None = None
    purchase_price: float | None = Field(None, alias="purchasePrice")
    ordering: int | None = None
    bonuses_charge_total: float | None = Field(None, alias="bonusesChargeTotal")
    bonuses_credit_total: float | None = Field(None, alias="bonusesCreditTotal")
    marking_objects: list[MarkingObject] | None = Field(None, alias="markingObjects")

class DeliveryDataResponse(CRMBase):

    external_id: str | None = Field(None, alias="externalId")
    track_number: str | None = Field(None, alias="trackNumber")
    status: str | None = None
    locked: bool | None = None
    pickup_point_address: str | None = Field(None, alias="pickuppointAddress")
    days: str | None = None
    status_text: str | None = Field(None, alias="statusText")
    status_date: datetime | None = Field(None, alias="statusDate")
    tariff: str | None = None
    tariff_name: str | None = Field(None, alias="tariffName")
    pickuppoint_id: str | None = Field(None, alias="pickuppointId")
    pickuppoint_name: str | None = Field(None, alias="pickuppointName")
    pickuppoint_schedule: str | None = Field(None, alias="pickuppointSchedule")
    pickuppoint_phone: str | None = Field(None, alias="pickuppointPhone")
    payer_type: str | None = Field(None, alias="payerType")
    status_comment: str | None = Field(None, alias="statusComment")
    cost: float | None = None
    min_term: int | None = Field(None, alias="minTerm")
    max_term: int | None = Field(None, alias="maxTerm")
    shipmentpoint_id: str | None = Field(None, alias="shipmentpointId")
    shipmentpoint_name: str | None = Field(None, alias="shipmentpointName")
    shipmentpoint_address: str | None = Field(None, alias="shipmentpointAddress")
    extra_data: dict[str, Any] | None = Field(None, alias="extraData")
    packages: list[Package] | None = None

class DeliveryService(CRMBase):
    name: str | None = None
    code: str | None = None
    active: bool | None = None

class OrderDeliveryResponse(CRMBase):

    code: str | None = None
    integration_code: str | None = Field(None, alias="integrationCode")
    data: DeliveryDataResponse | None = None
    service: DeliveryService | None = None
    cost: float | None = None
    net_cost: float | None = Field(None, alias="netCost")
    delivery_date: date | None = Field(None, alias="date")
    time: TimeInterval | None = None
    address: Address | None = None
    vat_rate: str | None = Field(None, alias="vatRate")

class Payment(CRMBase):

    id: int | None = None
    status: str | None = None
    type: str | None = None
    external_id: str | None = Field(None, alias="externalId")
    amount: float | None = None
    paid_at: datetime | None = Field(None, alias="paidAt")
    comment: str | None = None

class LoyaltyLevel(CRMBase):
    id: int | None = None
    name: str | None = None

class LoyaltyEventDiscount(CRMBase):
    id: int | None = None

class LinkedOrder(CRMBase):
    id: int | None = None
    number: str | None = None
    external_id: str | None = Field(None, alias="externalId")

class OrderLink(CRMBase):
    order: LinkedOrder | None = None
    created_at: datetime | None = Field(None, alias="createdAt")
    comment: str | None = None

class Company(CRMBase):
    id: int | None = None
    external_id: str | None = Field(None, alias="externalId")
    active: bool | None = None
    name: str | None = None
    brand: str | None = None
    site: str | None = None
    created_at: datetime | None = Field(None, alias="createdAt")
    contragent: Contragent | None = None
    address: Address | None = None
    avg_margin_summ: float | None = Field(None, alias="avgMarginSumm")
    margin_summ: float | None = Field(None, alias="marginSumm")
    total_summ: float | None = Field(None, alias="totalSumm")
    average_summ: float | None = Field(None, alias="averageSumm")
    cost_summ: float | None = Field(None, alias="costSumm")
    orders_count: int | None = Field(None, alias="ordersCount")
    custom_fields: dict[str, Any] | None = Field(None, alias="customFields")

class Order(CRMBase):

    id: int | None = None
    slug: int | None = None
    number: str | None = None
    external_id: str | None = Field(None, alias="externalId")
    order_type: str | None = Field(None, alias="orderType")
    order_method: str | None = Field(None, alias="orderMethod")
    privilege_type: PrivilegeType | None = Field(None, alias="privilegeType")
    country_iso: str | None = Field(None, alias="countryIso")
    created_at: datetime | None = Field(None, alias="createdAt")
    status_updated_at: datetime | None = Field(None, alias="statusUpdatedAt")
    summ: float | None = None
    total_summ: float | None = Field(None, alias="totalSumm")
    prepay_sum: float | None = Field(None, alias="prepaySum")
    purchase_summ: float | None = Field(None, alias="purchaseSumm")
    currency: str | None = None
    personal_discount_percent: float | None = Field(None, alias="personalDiscountPercent")
    loyalty_level: LoyaltyLevel | None = Field(None, alias="loyaltyLevel")
    loyalty_event_discount: LoyaltyEventDiscount | None = Field(
        None, alias="loyaltyEventDiscount",
    )
    bonuses_credit_total: float | None = Field(None, alias="bonusesCreditTotal")
    bonuses_charge_total: float | None = Field(None, alias="bonusesChargeTotal")
    mark: int | None = None
    mark_datetime: datetime | None = Field(None, alias="markDatetime")
    last_name: str | None = Field(None, alias="lastName")
    first_name: str | None = Field(None, alias="firstName")
    patronymic: str | None = None
    phone: str | None = None
    additional_phone: str | None = Field(None, alias="additionalPhone")
    email: str | None = None
    call: bool | None = None
    expired: bool | None = None
    customer_comment: str | None = Field(None, alias="customerComment")
    manager_comment: str | None = Field(None, alias="managerComment")
    manager_id: int | None = Field(None, alias="managerId")
    customer: Customer | None = None
    contact: Customer | None = None
    company: Company | None = None
    contragent: Contragent | None = None
    delivery: OrderDeliveryResponse | None = None
    site: str | None = None
    status: str | None = None
    status_comment: str | None = Field(None, alias="statusComment")
    source: Source | None = None
    items: list[OrderItem] | None = None
    full_paid_at: datetime | None = Field(None, alias="fullPaidAt")
    payments: list[Payment] | None = None
    from_api: bool | None = Field(None, alias="fromApi")
    weight: float | None = None
    length: int | None = None
    width: int | None = None
    height: int | None = None
    shipment_store: str | None = Field(None, alias="shipmentStore")
    shipment_date: date | None = Field(None, alias="shipmentDate")
    shipped: bool | None = None
    links: list[OrderLink] | None = None
    custom_fields: dict[str, Any] | None = Field(None, alias="customFields")
    client_id: str | None = Field(None, alias="clientId")

class OrderResponse(CRMBase):

    success: bool = True
    order: Order | None = None

class OrdersListResponse(CRMBase):

    success: bool = True
    orders: list[Order] = Field(default_factory=list)
    pagination: CRMPagination | None = None

class OrderCreateResponse(CRMBase):

    success: bool = True
    id: int | None = None
    order: Order | None = None

class OrderPaymentCreate(CRMBase):

    order: EntityWithExternalId | None = None
    external_id: str | None = Field(None, alias="externalId")
    amount: float | None = None
    paid_at: datetime | None = Field(None, alias="paidAt")
    comment: str | None = None
    type: str | None = None
    status: str | None = None

class OrderPaymentEdit(CRMBase):

    id: int | None = None
    order: EntityWithExternalId | None = None
    amount: float | None = None
    paid_at: datetime | None = Field(None, alias="paidAt")
    comment: str | None = None
    type: str | None = None
    status: str | None = None

class PaymentCreateResponse(CRMBase):
    success: bool = True
    id: int | None = None

class ProductProperty(CRMBase):

    code: str | None = None
    name: str | None = None
    value: str | None = None

class OfferPrice(CRMBase):

    price_type: str | None = Field(None, alias="priceType")
    price: float | None = None
    ordering: int | None = None

class Unit(CRMBase):
    code: str | None = None
    name: str | None = None
    sym: str | None = None

class OfferImage(CRMBase):
    url: str | None = None
    width: int | None = None
    height: int | None = None

class ProductOffer(CRMBase):

    id: int | None = None
    external_id: str | None = Field(None, alias="externalId")
    xml_id: str | None = Field(None, alias="xmlId")
    article: str | None = None
    name: str | None = None
    active: bool | None = None
    barcode: str | None = None
    vat_rate: str | None = Field(None, alias="vatRate")
    properties: dict[str, Any] | None = None
    prices: list[OfferPrice] | None = None
    images: list[str] | None = None
    weight: float | None = None
    length: float | None = None
    width: float | None = None
    height: float | None = None
    quantity: float | None = None
    unit: Unit | None = None

class ProductGroup(CRMBase):

    id: int | None = None
    parent_id: int | None = Field(None, alias="parentId")
    external_id: str | None = Field(None, alias="externalId")
    name: str | None = None
    active: bool | None = None
    site: str | None = None
    ordering: int | None = None
    description: str | None = None

class Product(CRMBase):

    id: int | None = None
    external_id: str | None = Field(None, alias="externalId")
    article: str | None = None
    name: str | None = None
    description: str | None = None
    url: str | None = None
    image_url: str | None = Field(None, alias="imageUrl")
    popular: bool | None = None
    stock: bool | None = None
    novelty: bool | None = None
    recommended: bool | None = None
    active: bool | None = None
    quantity: float | None = None
    manufacturer: str | None = None
    groups: list[ProductGroup] | None = None
    markable: bool | None = None
    offers: list[ProductOffer] | None = None
    properties: dict[str, Any] | None = None
    min_price: float | None = Field(None, alias="minPrice")
    max_price: float | None = Field(None, alias="maxPrice")

class ProductsListResponse(CRMBase):

    success: bool = True
    products: list[Product] = Field(default_factory=list)
    pagination: CRMPagination | None = None

class ProductGroupsListResponse(CRMBase):

    success: bool = True
    product_group: list[ProductGroup] = Field(
        default_factory=list, alias="productGroup",
    )
    pagination: CRMPagination | None = None

class StoreOffer(CRMBase):

    id: int | None = None
    external_id: str | None = Field(None, alias="externalId")
    xml_id: str | None = Field(None, alias="xmlId")
    article: str | None = None
    name: str | None = None
    active: bool | None = None
    barcode: str | None = None
    vat_rate: str | None = Field(None, alias="vatRate")
    properties: dict[str, Any] | None = None
    prices: list[OfferPrice] | None = None
    images: list[str] | None = None
    weight: float | None = None
    quantity: float | None = None
    unit: Unit | None = None
    product_id: int | None = Field(None, alias="productId")
    product_name: str | None = Field(None, alias="productName")
    product_active: bool | None = Field(None, alias="productActive")

class OffersListResponse(CRMBase):

    success: bool = True
    offers: list[StoreOffer] = Field(default_factory=list)
    pagination: CRMPagination | None = None

class InventoryEntry(CRMBase):

    id: int | None = None
    external_id: str | None = Field(None, alias="externalId")
    xml_id: str | None = Field(None, alias="xmlId")
    quantity: float | None = None
    purchase_price: float | None = Field(None, alias="purchasePrice")
    stores: list[dict[str, Any]] | None = None

class InventoriesListResponse(CRMBase):

    success: bool = True
    offers: list[InventoryEntry] = Field(default_factory=list)
    pagination: CRMPagination | None = None

class ProductFilter(CRMBase):

    ids: list[int] | None = None
    active: int | None = None
    min_price: float | None = Field(None, alias="minPrice")
    max_price: float | None = Field(None, alias="maxPrice")
    name: str | None = None
    article: str | None = None
    offer_active: int | None = Field(None, alias="offerActive")
    group_external_id: str | None = Field(None, alias="groupExternalId")
    groups: list[int] | None = None
    sites: list[str] | None = None
    properties: dict[str, str] | None = None

class TelephonyCallEvent(CRMBase):

    phone: str
    type: CallType
    codes: list[str] | None = None
    hangup_status: CallHangupStatus | None = Field(None, alias="hangupStatus")
    external_phone: str | None = Field(None, alias="externalPhone")
    service_code: str | None = Field(None, alias="serviceCode")
    internal_phone: str | None = Field(None, alias="internalPhone")
    external_id: str | None = Field(None, alias="externalId")
    duration: int | None = None
    record_url: str | None = Field(None, alias="recordUrl")
    site: str | None = None
    webphone_link: str | None = Field(None, alias="webphoneLink")

class TelephonyCallRecord(CRMBase):

    call_date: datetime = Field(alias="date")
    type: CallType
    phone: str
    code: str | None = None
    result: CallHangupStatus | None = None
    duration: int | None = None
    external_id: str | None = Field(None, alias="externalId")
    record_url: str | None = Field(None, alias="recordUrl")
    internal_phone: str | None = Field(None, alias="internalPhone")
    external_phone: str | None = Field(None, alias="externalPhone")
    site: str | None = None

class TelephonyCallsUpload(CRMBase):

    calls: list[TelephonyCallRecord]

class TelephonyManager(CRMBase):

    id: int | None = None
    first_name: str | None = Field(None, alias="firstName")
    last_name: str | None = Field(None, alias="lastName")
    patronymic: str | None = None
    email: str | None = None
    code: str | None = None

class TelephonyManagerResponse(CRMBase):

    success: bool = True
    manager: TelephonyManager | None = None
    customer: Customer | None = None

class TelephonyCallEventResponse(CRMBase):

    success: bool = True
    status: str | None = None
    external_id: str | None = Field(None, alias="externalId")

class TelephonyCallsUploadResponse(CRMBase):

    success: bool = True
    processed_calls_count: int | None = Field(None, alias="processedCallsCount")
    duplicate_calls_count: int | None = Field(None, alias="duplicateCallsCount")

class StatusGroup(CRMBase):

    name: str | None = None
    code: str | None = None
    active: bool | None = None
    ordering: int | None = None
    process: bool | None = None
    statuses: list[str] | None = None

class OrderStatus(CRMBase):

    name: str | None = None
    code: str | None = None
    active: bool | None = None
    ordering: int | None = None
    group: str | None = None

class PaymentType(CRMBase):

    name: str | None = None
    code: str | None = None
    active: bool | None = None
    default_for_crm: bool | None = Field(None, alias="defaultForCrm")
    default_for_api: bool | None = Field(None, alias="defaultForApi")
    description: str | None = None
    delivery_types: list[str] | None = Field(None, alias="deliveryTypes")
    payment_statuses: list[str] | None = Field(None, alias="paymentStatuses")

class PaymentStatus(CRMBase):

    name: str | None = None
    code: str | None = None
    active: bool | None = None
    default_for_crm: bool | None = Field(None, alias="defaultForCrm")
    default_for_api: bool | None = Field(None, alias="defaultForApi")
    ordering: int | None = None
    payment_complete: bool | None = Field(None, alias="paymentComplete")
    description: str | None = None
    payment_types: list[str] | None = Field(None, alias="paymentTypes")

class DeliveryType(CRMBase):

    name: str | None = None
    code: str | None = None
    active: bool | None = None
    default_for_crm: bool | None = Field(None, alias="defaultForCrm")
    default_for_api: bool | None = Field(None, alias="defaultForApi")
    description: str | None = None
    default_cost: float | None = Field(None, alias="defaultCost")
    default_net_cost: float | None = Field(None, alias="defaultNetCost")
    default_for_old_templates: bool | None = Field(None, alias="defaultForOldTemplates")
    integration_code: str | None = Field(None, alias="integrationCode")
    delivery_services: list[str] | None = Field(None, alias="deliveryServices")
    payment_types: list[str] | None = Field(None, alias="paymentTypes")

class OrderMethod(CRMBase):

    name: str | None = None
    code: str | None = None
    active: bool | None = None
    default_for_crm: bool | None = Field(None, alias="defaultForCrm")
    default_for_api: bool | None = Field(None, alias="defaultForApi")

class OrderType(CRMBase):

    name: str | None = None
    code: str | None = None
    active: bool | None = None
    default_for_crm: bool | None = Field(None, alias="defaultForCrm")
    default_for_api: bool | None = Field(None, alias="defaultForApi")

class Site(CRMBase):

    name: str | None = None
    code: str | None = None
    url: str | None = None
    description: str | None = None
    catalog: str | None = None
    country_iso: str | None = Field(None, alias="countryIso")
    currency_iso: str | None = Field(None, alias="currencyIso")
    default_for_crm: bool | None = Field(None, alias="defaultForCrm")
    ymlUrl: str | None = None
    load_from_yml: bool | None = Field(None, alias="loadFromYml")
    ordering: int | None = None
    is_demo: bool | None = Field(None, alias="isDemo")
    active: bool | None = None

class Store(CRMBase):

    name: str | None = None
    code: str | None = None
    type: str | None = None
    description: str | None = None
    external_id: str | None = Field(None, alias="externalId")
    email: str | None = None
    active: bool | None = None

class ProductStatus(CRMBase):

    name: str | None = None
    code: str | None = None
    active: bool | None = None
    ordering: int | None = None
    cancel_status: bool | None = Field(None, alias="cancelStatus")

class PriceTypeRef(CRMBase):

    id: int | None = None
    code: str | None = None
    name: str | None = None
    active: bool | None = None
    default: bool | None = None
    ordering: int | None = None
    description: str | None = None
    filter_type: str | None = Field(None, alias="filterType")
    currency: str | None = None
    geo: list[dict[str, Any]] | None = None

class UserGroup(CRMBase):

    name: str | None = None
    code: str | None = None
    is_manager: bool | None = Field(None, alias="isManager")
    is_delivery_man: bool | None = Field(None, alias="isDeliveryMen")

class CRMUser(CRMBase):

    id: int | None = None
    first_name: str | None = Field(None, alias="firstName")
    last_name: str | None = Field(None, alias="lastName")
    patronymic: str | None = None
    email: str | None = None
    phone: str | None = None
    status: str | None = None
    is_admin: bool | None = Field(None, alias="isAdmin")
    is_manager: bool | None = Field(None, alias="isManager")
    groups: list[UserGroup] | None = None
    mg_user_id: int | None = Field(None, alias="mgUserId")
    photo_url: str | None = Field(None, alias="photoUrl")
    active: bool | None = None
    online: bool | None = None

class StatusesResponse(CRMBase):
    success: bool = True
    statuses: dict[str, OrderStatus] = Field(default_factory=dict)

class StatusGroupsResponse(CRMBase):
    success: bool = True
    status_groups: dict[str, StatusGroup] = Field(
        default_factory=dict, alias="statusGroups",
    )

class PaymentTypesResponse(CRMBase):
    success: bool = True
    payment_types: dict[str, PaymentType] = Field(
        default_factory=dict, alias="paymentTypes",
    )

class PaymentStatusesResponse(CRMBase):
    success: bool = True
    payment_statuses: dict[str, PaymentStatus] = Field(
        default_factory=dict, alias="paymentStatuses",
    )

class DeliveryTypesResponse(CRMBase):
    success: bool = True
    delivery_types: dict[str, DeliveryType] = Field(
        default_factory=dict, alias="deliveryTypes",
    )

class OrderMethodsResponse(CRMBase):
    success: bool = True
    order_methods: dict[str, OrderMethod] = Field(
        default_factory=dict, alias="orderMethods",
    )

class OrderTypesResponse(CRMBase):
    success: bool = True
    order_types: dict[str, OrderType] = Field(
        default_factory=dict, alias="orderTypes",
    )

class SitesResponse(CRMBase):
    success: bool = True
    sites: dict[str, Site] = Field(default_factory=dict)

class StoresResponse(CRMBase):
    success: bool = True
    stores: dict[str, Store] = Field(default_factory=dict)

class ProductStatusesResponse(CRMBase):
    success: bool = True
    product_statuses: dict[str, ProductStatus] = Field(
        default_factory=dict, alias="productStatuses",
    )

class PriceTypesResponse(CRMBase):
    success: bool = True
    price_types: list[PriceTypeRef] = Field(default_factory=list, alias="priceTypes")

class UsersListResponse(CRMBase):
    success: bool = True
    users: list[CRMUser] = Field(default_factory=list)
    pagination: CRMPagination | None = None

class UserResponse(CRMBase):
    success: bool = True
    user: CRMUser | None = None

class UserGroupsResponse(CRMBase):
    success: bool = True
    groups: list[UserGroup] = Field(default_factory=list)

class CRMSuccessResponse(CRMBase):

    success: bool = True
    id: int | None = None
    errors: dict[str, Any] | None = None
