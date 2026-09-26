"""add attempt_count and txn_ref to payments

Revision ID: b2c9d4e7f1a3
Revises: a71c92e804bd
Create Date: 2026-09-26 10:00:00.000000

Task "Chốt các trường hợp lỗi và retry của thanh toán" (#2 phân biệt từng lần
thanh toán): thêm 2 cột vào `payments` để mỗi LẦN THỬ thanh toán VNPay có
`vnp_TxnRef` riêng - callback của lần thử cũ không tác động sang lần mới. Xem
docstring `app/services/payment_service.py`.

`attempt_count` server_default="0" - backfill an toàn cho các dòng payment CŨ
đã tồn tại (nếu có). `txn_ref` nullable - dòng cũ chưa có giá trị (sẽ được đặt
ở lần create/retry kế tiếp), unique để idempotency ở tầng DB.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c9d4e7f1a3'
down_revision: Union[str, Sequence[str], None] = 'a71c92e804bd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "payments",
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column("payments", sa.Column("txn_ref", sa.String(length=32), nullable=True))
    op.create_unique_constraint("uq_payments_txn_ref", "payments", ["txn_ref"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_payments_txn_ref", "payments", type_="unique")
    op.drop_column("payments", "txn_ref")
    op.drop_column("payments", "attempt_count")
