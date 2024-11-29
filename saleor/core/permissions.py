from enum import Enum

class BasePermissionEnum(Enum):
    @property
    def codename(self):
        return self.value.split(".")[1]

class OrderPermissions(str, Enum):
    MANAGE_ORDERS = "order.manage_orders"
    MANAGE_CHECKOUTS = "checkout.manage_checkouts" 