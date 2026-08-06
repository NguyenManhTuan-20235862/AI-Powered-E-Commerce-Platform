"""Lưu file upload cục bộ (task 3.4.1 - `POST /products/{id}/image`).

Giải pháp ĐƠN GIẢN NHẤT phù hợp quy mô đồ án - lưu vào thư mục local trong
container (`UPLOAD_ROOT`, đường dẫn tương đối tới CWD - luôn là `/app` theo
`WORKDIR` của cả `Dockerfile.dev` lẫn `Dockerfile.prod`), serve qua
`StaticFiles` mount sẵn trong `app/main.py` tại `UPLOAD_URL_PREFIX`. CHƯA
dùng cloud storage (S3/Cloudinary...) - xem `docs/KNOWN_TODOS.md` cho lý do +
việc cần làm khi deploy thật (task 7.5):

- Dev (`docker-compose.yml`, bind mount `./backend:/app`): file ghi vào đây
  THẬT SỰ persist trên host giữa các lần restart container - tiện test ngay,
  không cần thêm cấu hình.
- `Dockerfile.prod` KHÔNG có bind mount: file sẽ MẤT khi container bị
  recreate (filesystem ephemeral) - giới hạn CỐ Ý chấp nhận cho giai đoạn
  hiện tại (dự án chưa deploy thật), KHÔNG phải bug.
"""

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import API_PREFIX

UPLOAD_ROOT = Path("uploads")
# Cùng tiền tố API_PREFIX dù StaticFiles không phải router (không đi qua
# app.include_router(..., prefix=API_PREFIX)) - để nếu sau này nginx (task
# 2.4.1, hiện CHƯA vào docker-compose.yml) được bật lại, request tới URL này
# vẫn khớp `location /api/` (proxy nguyên path sang Backend) thay vì rơi vào
# `location /` (proxy sang Frontend, sẽ 404 vì Frontend không phục vụ path này).
UPLOAD_URL_PREFIX = f"{API_PREFIX}/uploads"

ALLOWED_IMAGE_EXTENSIONS: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024  # 5MB


def save_product_image(file: UploadFile, product_id: int) -> str:
    """Lưu file ảnh upload cho 1 sản phẩm, trả về URL công khai (path tương
    đối, phục vụ qua `StaticFiles` mount ở `app/main.py`) để lưu vào
    `products.image_url`.

    Validate content_type (whitelist ảnh phổ biến) + giới hạn dung lượng
    (5MB, đọc + check TRƯỚC khi ghi file - tránh ghi file khổng lồ ra đĩa rồi
    mới phát hiện quá lớn). `nginx.conf` (task 2.4.1) đã có
    `client_max_body_size 10m` nhưng nginx CHƯA được đưa vào
    `docker-compose.yml` (dev bypass thẳng `:8000`, xem CLAUDE.md) - Backend
    tự giới hạn ở đây, không dựa hoàn toàn vào nginx (chỉ 1 lớp phòng thủ
    hiện đang thật sự chạy).
    """
    if file.content_type not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Định dạng ảnh không hợp lệ - chỉ chấp nhận JPEG/PNG/WEBP/GIF",
        )

    contents = file.file.read()
    if len(contents) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ảnh vượt quá dung lượng cho phép (tối đa 5MB)",
        )

    subdir = UPLOAD_ROOT / "products"
    subdir.mkdir(parents=True, exist_ok=True)

    # uuid4 (không phải tên file gốc client gửi lên) - tránh path traversal
    # (VD filename "../../etc/passwd") và tránh trùng tên giữa nhiều lần
    # upload cho CÙNG 1 sản phẩm (ảnh cũ không tự xóa - xem Ghi chú
    # docs/KNOWN_TODOS.md, chấp nhận vài file rác thay vì rủi ro xóa nhầm).
    extension = ALLOWED_IMAGE_EXTENSIONS[file.content_type]
    filename = f"{product_id}-{uuid.uuid4().hex[:12]}{extension}"
    (subdir / filename).write_bytes(contents)

    return f"{UPLOAD_URL_PREFIX}/products/{filename}"
