"""Pydantic schema: Review (MongoDB collection `reviews`, task 3.2.2).

Cùng pattern với `app/schemas/chat_log.py` (task 3.2.1, xem file đó để hiểu
`PyObjectId`) - KHÔNG kế thừa `BaseSchema` (`app/schemas/base.py`,
`from_attributes=True` dành cho đọc từ SQLAlchemy ORM, không cần cho document
MongoDB đọc về dạng `dict`).

QUYẾT ĐỊNH THIẾT KẾ (task 3.2.2):

1) Denormalize `user_name` (snapshot tên user lúc viết review) thay vì chỉ
   lưu `user_id` rồi join ngược sang MySQL mỗi lần đọc:
   - Lợi: `GET /products/{id}/reviews` (Public, có thể nhiều review/trang)
     đọc thẳng 1 collection, KHÔNG cần N+1 query (hoặc batch query) sang
     MySQL chỉ để lấy tên hiển thị - đúng triết lý MongoDB (tối ưu đọc bằng
     denormalize thay vì join, MongoDB không có JOIN thật).
   - Hại: nếu user đổi `full_name` bên MySQL SAU khi đã viết review, các
     review CŨ vẫn hiển thị tên CŨ (không tự đồng bộ) - lệch dữ liệu, nhưng
     là độ lệch NHỎ và thường CHẤP NHẬN ĐƯỢC (nhiều nền tảng review thật cũng
     hiển thị tên "tại thời điểm viết", không retroactive update).
   - Quyết định: CHẤP NHẬN độ lệch này, KHÔNG xây cơ chế đồng bộ (event/job
     nghe user đổi tên rồi `update_many` các review liên quan) - chi phí xây
     + bảo trì cơ chế đó không tương xứng với lợi ích cho dự án đồ án solo,
     phạm vi 13 tuần. Xem thêm phân tích đầy đủ gửi kèm ngoài file này.

2) Soft-delete (`is_deleted`) thay vì xóa cứng khi Admin gọi
   `DELETE /reviews/{review_id}`:
   - Khác `products.is_active` (MySQL, task 3.1.2) - lý do soft-delete ở đó
     là ràng buộc TOÀN VẸN THỰC SỰ (order_items.product_id vẫn phải tham
     chiếu được sản phẩm cũ cho lịch sử hóa đơn). Review KHÔNG có bảng nào
     tham chiếu ngược lại `reviews.id` - không có rủi ro toàn vẹn kiểu đó.
   - Lý do soft-delete ở ĐÂY khác hẳn: đây là hành động MODERATION ("xóa
     review VI PHẠM") - giữ lại bản ghi ẩn phục vụ audit trail (biết Admin
     nào xóa gì, tranh chấp với user sau này có bằng chứng) và cho phép
     "undo" nếu Admin xóa nhầm - hành động xóa cứng thì KHÔNG thể hoàn tác.
   - Đánh đổi: mọi query đọc công khai (`GET /products/{id}/reviews`) PHẢI
     luôn nhớ filter `is_deleted: false` - rủi ro thật nếu code sau này quên
     filter (nội dung vi phạm hiện lại). Chấp nhận rủi ro này vì lợi ích audit
     trail/undo lớn hơn, và filter này sẽ nằm cố định trong 1 hàm
     repository/service dùng chung (task 6.x), không rải rác nhiều nơi.
   - `is_deleted` là CHI TIẾT NỘI BỘ - KHÔNG xuất hiện trong `ReviewRead`
     (response công khai), chỉ có trong `ReviewInDB` (đọc raw ở tầng
     service/repository).

3) Unique index đề xuất `(user_id, order_id, product_id)`: NGĂN user gửi
   NHIỀU review trùng lặp cho CÙNG 1 sản phẩm TỪ CÙNG 1 đơn hàng (spam-submit
   nút "Gửi đánh giá" nhiều lần) - nhưng VẪN CHO PHÉP user review lại cùng 1
   sản phẩm nếu mua ở 1 đơn hàng KHÁC (trải nghiệm mua lần sau có thể khác
   lần trước - hợp lý cho phép). Index mặc định KHÔNG dùng partial filter
   (`is_deleted` không nằm trong điều kiện unique) - nghĩa là sau khi 1 review
   bị Admin xóa mềm, user KHÔNG viết lại review mới cho đúng đơn hàng/sản
   phẩm đó được nữa (chấp nhận, tránh lách luật: viết bậy → bị xóa → viết
   bậy tiếp). Nếu sau này muốn cho user "viết lại" sau khi bị xóa, đổi sang
   partial unique index (`partialFilterExpression={"is_deleted": False}`) -
   để ngỏ, KHÔNG làm ở task này (chưa có yêu cầu nghiệp vụ rõ ràng).
"""

from datetime import datetime, timezone
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

# Xem app/schemas/chat_log.py (task 3.2.1) để biết lý do dùng cách này thay
# vì custom type kiểu Pydantic v1 cũ.
PyObjectId = Annotated[str, BeforeValidator(str)]


class ReviewBase(BaseModel):
    """Field chung cho 1 document `reviews`."""

    # int - khớp BIGINT của products.id/orders.id bên MySQL. KHÔNG phải FK
    # thật (khác hệ CSDL) - xem mục "Tham chiếu logic" ở docs/DATABASE_SCHEMA.md.
    product_id: int
    user_id: int
    # Denormalize (snapshot lúc viết review) - xem phân tích đánh đổi ở
    # docstring module phía trên.
    user_name: str
    # NOT NULL (khác giả định "order_id optional" gợi ý ban đầu) - theo đúng
    # docs/API_SPEC.md mục 7: POST /products/{id}/reviews CHỈ cho phép khi ĐÃ
    # MUA sản phẩm, không có luồng review "chưa xác minh mua hàng" nào trong
    # spec hiện tại - nên mọi document hợp lệ LUÔN phải có đúng 1 order_id đã
    # verify (task 6.x, service layer). Nếu sau này nghiệp vụ đổi (cho phép
    # review không cần mua hàng), đổi field này sang `int | None` lúc đó.
    order_id: int
    rating: int = Field(ge=1, le=5)
    comment: str | None = None
    # Optional - để ngỏ mở rộng (upload ảnh review), CHƯA có route upload
    # thật trong repo (chỉ mới có python-multipart trong requirements-core.txt,
    # xem CLAUDE.md) - lưu URL string đơn thuần giống pattern products.image_url,
    # không phải blob/binary.
    images: list[str] | None = None
    # Luôn True given order_id bắt buộc + đã verify ở trên (task 6.x) - vẫn
    # khai báo tường minh thay vì suy ra ngầm từ order_id có tồn tại hay
    # không, để (a) tiện đọc trực tiếp ở response mà không phải tính lại, và
    # (b) forward-compatible nếu sau này nghiệp vụ nới lỏng cho review không
    # cần mua hàng (lúc đó field này mới thật sự có giá trị False).
    is_verified_purchase: bool = True


class ReviewCreate(ReviewBase):
    """Dùng để validate dữ liệu TRƯỚC KHI insert vào MongoDB (task 3.2.3/6.x).

    Giống `ChatLogCreate` (`app/schemas/chat_log.py`) - đây là cấu trúc
    document ĐẦY ĐỦ sẵn sàng insert (`product_id`/`user_id`/`user_name` lấy từ
    path param + user đang đăng nhập, `order_id` lấy từ kết quả tra cứu "user
    đã mua sản phẩm này chưa" bên MySQL), KHÔNG PHẢI nguyên văn request body
    HTTP client gửi lên (client thực tế nhiều khả năng chỉ gửi
    `rating`/`comment`/`images` - phần còn lại tầng service tự điền trước khi
    gọi schema này). Việc map request body -> schema này thuộc task 6.x (chưa
    implement router thật).

    KHÔNG có `_id`/`is_deleted`/`created_at`/`updated_at` - do MongoDB/tầng
    service tự set lúc insert.
    """


class ReviewInDB(ReviewBase):
    """Document ĐẦY ĐỦ đúng như lưu thật trong MongoDB - có `_id`,
    `is_deleted` (cờ soft-delete nội bộ), `created_at`, `updated_at`.

    Dùng ở tầng service/repository (task 6.x) khi đọc raw document từ
    MongoDB - KHÔNG dùng trực tiếp làm `response_model` cho API công khai
    (`is_deleted` là chi tiết nội bộ, không nên lộ ra ngoài - xem
    `ReviewRead` bên dưới).
    """

    id: PyObjectId = Field(alias="_id")
    is_deleted: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = None

    model_config = ConfigDict(populate_by_name=True)


class ReviewRead(ReviewBase):
    """Response schema CÔNG KHAI cho `GET /products/{id}/reviews` (Public) và
    `POST /products/{id}/reviews` (Customer) - xem `app/routers/review.py`.

    Giữ tên `ReviewRead` (KHÔNG đổi thành `ReviewResponse` dù được gợi ý ban
    đầu) vì `app/routers/review.py` ĐÃ import + dùng tên `ReviewRead` làm
    `response_model` từ trước (task 1.4.x, khung endpoint) - đổi tên ở đây mà
    không sửa router sẽ vỡ import; sửa router lại ngoài phạm vi task 3.2.2
    (chỉ thiết kế document + schema, chưa động vào logic router).

    KHÔNG có `is_deleted` - review đã xóa mềm không nên lộ field nội bộ này
    ra API công khai (tầng service tự filter `is_deleted: false` trước khi
    trả review nào ra ngoài, task 6.x).
    """

    id: PyObjectId = Field(alias="_id")
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(populate_by_name=True)
