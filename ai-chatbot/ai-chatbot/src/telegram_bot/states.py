from aiogram.fsm.state import State, StatesGroup

class Registration(StatesGroup):
    waiting_phone = State()

class Chat(StatesGroup):
    active = State()

class Order(StatesGroup):

    waiting_name = State()
    waiting_product = State()
    waiting_product_quantity = State()
    waiting_location = State()
    waiting_address = State()
    waiting_delivery_time = State()
    waiting_payment = State()
    confirmation = State()

class OrderStatus(StatesGroup):

    waiting_order_id = State()
