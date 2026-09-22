"""Delta adjustments serialized with checkout by the same Product row lock."""
from datetime import date, timedelta

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.inventory import InventoryAdjustment
from app.models.product import Product
from app.models.user import User
from app.schemas.common import paginated_response
from app.schemas.inventory import InventoryAdjustCreate, InventoryAdjustmentRead, LowStockRead


def _to_read(record: InventoryAdjustment, admin_name: str) -> InventoryAdjustmentRead:
    """`admin_name` KHÔNG phải cột trên `InventoryAdjustment` - JOIN riêng
    (xem docstring `InventoryAdjustmentRead.admin_name`), nên không thể
    `model_validate(record)` trực tiếp (thiếu field bắt buộc) - dựng dict từ
    record + admin_name truyền vào, cùng pattern `ReviewAdminRead` (review
    service)."""
    return InventoryAdjustmentRead.model_validate(
        {
            "id": record.id,
            "product_id": record.product_id,
            "product_name": record.product_name,
            "change_quantity": record.change_quantity,
            "stock_before": record.stock_before,
            "stock_after": record.stock_after,
            "reason": record.reason,
            "note": record.note,
            "admin_id": record.admin_id,
            "admin_name": admin_name,
            "created_at": record.created_at,
        }
    )


def _replay(record, payload, admin_name: str):
    if any(getattr(record, field) != value for field, value in payload.model_dump().items()):
        raise HTTPException(409, "Yêu cầu đã được dùng cho nội dung điều chỉnh khác")
    return _to_read(record, admin_name)


def adjust_stock(db: Session, admin_id: int, admin_name: str, key: str, payload: InventoryAdjustCreate):
    """`admin_name`: full_name của Admin đang gọi (`current_user.full_name`,
    router truyền vào sẵn - tránh query `users` thừa vì đã có object User qua
    dependency injection). Luôn ĐÚNG admin đang gọi cho cả nhánh tạo mới LẪN
    replay (idempotency key tra theo `admin_id=admin_id`, không thể thuộc
    Admin khác)."""
    lookup = lambda: db.query(InventoryAdjustment).filter_by(admin_id=admin_id, idempotency_key=key).first()
    try:
        existing = lookup()
        if existing is not None:
            return _replay(existing, payload, admin_name)
        product = db.query(Product).filter_by(id=payload.product_id).populate_existing().with_for_update().one_or_none()
        if product is None:
            raise HTTPException(404, "Không tìm thấy sản phẩm")
        # Insert/flush the unique claim before validating stock: a retry after a
        # successful depletion must replay, not fail insufficient-stock validation.
        record = InventoryAdjustment(
            **payload.model_dump(), admin_id=admin_id, idempotency_key=key,
            product_name=product.name, stock_before=product.stock_quantity,
            stock_after=product.stock_quantity,
        )
        db.add(record)
        db.flush()
        after = product.stock_quantity + payload.change_quantity
        if after < 0:
            raise HTTPException(409, f"Không đủ tồn kho để giảm (hiện còn {product.stock_quantity})")
        if after > 2147483647:
            raise HTTPException(409, "Tồn kho vượt giới hạn cho phép")
        product.stock_quantity = after
        record.stock_after = after
        db.flush()
        result = _to_read(record, admin_name)
        db.commit()
        return result
    except IntegrityError:
        # Rollback refreshes MySQL REPEATABLE READ snapshot. The unique insert
        # waits for a concurrent winner to commit; read that committed result.
        db.rollback()
        existing = lookup()
        if existing is None:
            raise
        return _replay(existing, payload, admin_name)
    except Exception:
        db.rollback()
        raise


def list_adjustments(db, page, page_size, product_id=None, reason=None, date_from=None, date_to=None):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(400, "Ngày bắt đầu phải trước hoặc bằng ngày kết thúc")
    query = db.query(InventoryAdjustment)
    if product_id is not None:
        query = query.filter_by(product_id=product_id)
    if reason is not None:
        query = query.filter_by(reason=reason)
    if date_from:
        query = query.filter(InventoryAdjustment.created_at >= date_from)
    if date_to:
        query = query.filter(InventoryAdjustment.created_at < date_to + timedelta(days=1))
    total = query.count()
    records = query.order_by(InventoryAdjustment.created_at.desc(), InventoryAdjustment.id.desc()).offset((page-1)*page_size).limit(page_size).all()

    # JOIN BATCH tên Admin sang `users` (1 query `WHERE id IN (...)` cho toàn
    # bộ `admin_id` xuất hiện trong TRANG hiện tại, KHÔNG N+1) - cùng
    # convention `review_service.list_reviews_admin()` join `product_name`.
    admin_ids = {r.admin_id for r in records}
    admin_names: dict[int, str] = {}
    if admin_ids:
        admin_names = dict(db.query(User.id, User.full_name).filter(User.id.in_(admin_ids)).all())

    items = [_to_read(r, admin_names.get(r.admin_id, f"#{r.admin_id}")) for r in records]
    return paginated_response(items, total, page, page_size)


def low_stock(db, page, page_size, threshold, is_active):
    query = db.query(Product).filter(Product.stock_quantity < threshold)
    if is_active is not None:
        query = query.filter(Product.is_active == is_active)
    total = query.count()
    rows = query.order_by(Product.stock_quantity, Product.id).offset((page-1)*page_size).limit(page_size).all()
    return paginated_response([LowStockRead.model_validate(p) for p in rows], total, page, page_size)
