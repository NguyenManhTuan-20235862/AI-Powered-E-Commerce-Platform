"""Import toàn bộ model ở đây để Base.metadata luôn đầy đủ khi Alembic autogenerate."""

from app.models.cart import CartItem
from app.models.category import Category
from app.models.order import Order, OrderItem, OrderStatus, Payment, PaymentStatus
from app.models.product import Product
from app.models.user import User, UserRole

__all__ = [
    "CartItem",
    "Category",
    "Order",
    "OrderItem",
    "OrderStatus",
    "Payment",
    "PaymentStatus",
    "Product",
    "User",
    "UserRole",
]
