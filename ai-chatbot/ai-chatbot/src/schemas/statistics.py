from dataclasses import dataclass

@dataclass(slots=True, frozen=True)
class UserStats:
    total: int
    active: int
    by_channel: dict[str, int]
    today_new: int

@dataclass(slots=True, frozen=True)
class OrderStats:
    total: int
    pending: int
    completed: int
    cancelled: int
    today_total: int
    today_revenue: int
    by_status: dict[str, int]
    by_channel: dict[str, int]

@dataclass(slots=True, frozen=True)
class ConversationStats:
    total_messages: int
    today_messages: int
    by_role: dict[str, int]
    by_channel: dict[str, int]

@dataclass(slots=True, frozen=True)
class CallStats:
    total: int
    today_total: int
    by_status: dict[str, int]
    avg_duration: float

@dataclass(slots=True, frozen=True)
class AdminStats:
    total_admins: int

@dataclass(slots=True, frozen=True)
class DashboardStats:
    users: UserStats
    orders: OrderStats
    conversations: ConversationStats
    calls: CallStats
    admins: AdminStats
    collected_at: str
