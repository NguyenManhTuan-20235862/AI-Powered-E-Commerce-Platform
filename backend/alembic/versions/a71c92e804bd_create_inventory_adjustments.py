"""Create immutable Admin inventory adjustments.

Revision ID: a71c92e804bd
Revises: f00f506b3a6b
"""
from alembic import op
import sqlalchemy as sa

revision = "a71c92e804bd"
down_revision = "f00f506b3a6b"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "inventory_adjustments",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("product_id", sa.BigInteger(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("product_name", sa.String(255), nullable=False),
        sa.Column("change_quantity", sa.Integer(), nullable=False),
        sa.Column("stock_before", sa.Integer(), nullable=False),
        sa.Column("stock_after", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(20), nullable=False),
        sa.Column("note", sa.String(500), nullable=True),
        sa.Column("admin_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("idempotency_key", sa.String(64, collation="ascii_bin"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("admin_id", "idempotency_key", name="uq_inventory_admin_key"),
    )
    op.create_index("ix_inventory_product_created", "inventory_adjustments", ["product_id", "created_at"])
    op.create_index("ix_inventory_created", "inventory_adjustments", ["created_at"])


def downgrade():
    op.drop_table("inventory_adjustments")
