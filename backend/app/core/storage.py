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

# Magic byte (file signature) cho từng định dạng whitelist ở trên - dùng để
# xác định ĐÚNG loại ảnh từ NỘI DUNG file thật, không tin `Content-Type` client
# tự khai (header này client hoàn toàn tự set tùy ý lúc gửi multipart form,
# không phải giá trị do trình duyệt validate nội dung thật - 1 file `.exe`
# hoàn toàn có thể gửi kèm `Content-Type: image/png`). Chỉ sniff đúng 4 định
# dạng đã whitelist (KHÔNG viết bộ nhận diện file tổng quát) - tương xứng quy
# mô đồ án, không cần thêm dependency (`Pillow`/`python-magic`) chỉ cho việc
# so khớp vài byte đầu cố định.
_JPEG_SIGNATURE = b"\xff\xd8\xff"
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_GIF_SIGNATURES = (b"GIF87a", b"GIF89a")


def _sniff_image_extension(contents: bytes) -> str | None:
    """Trả về extension ĐÚNG (`.jpg`/`.png`/`.gif`/`.webp`) suy ra từ magic
    byte thật của `contents`, hoặc `None` nếu không khớp bất kỳ định dạng nào
    trong whitelist - dùng thay cho việc suy ra extension từ `Content-Type`
    (có thể bị client khai sai/giả mạo)."""
    if contents.startswith(_JPEG_SIGNATURE):
        return ".jpg"
    if contents.startswith(_PNG_SIGNATURE):
        return ".png"
    if contents.startswith(_GIF_SIGNATURES):
        return ".gif"
    # WEBP: RIFF <4-byte size> WEBP - 4 byte đầu "RIFF", 4 byte kế tiếp là độ
    # dài file (bỏ qua, không cần validate), byte 8-11 phải là "WEBP".
    if len(contents) >= 12 and contents[0:4] == b"RIFF" and contents[8:12] == b"WEBP":
        return ".webp"
    return None


def save_product_image(file: UploadFile, product_id: int) -> str:
    """Lưu file ảnh upload cho 1 sản phẩm, trả về URL công khai (path tương
    đối, phục vụ qua `StaticFiles` mount ở `app/main.py`) để lưu vào
    `products.image_url`.

    Validate content_type (whitelist ảnh phổ biến, kiểm tra RẺ trước - reject
    ngay không cần đọc hết file nếu header đã sai) + giới hạn dung lượng
    (5MB, đọc + check TRƯỚC khi ghi file - tránh ghi file khổng lồ ra đĩa rồi
    mới phát hiện quá lớn) + validate NỘI DUNG THẬT qua magic byte
    (`_sniff_image_extension`) - `Content-Type` chỉ là gợi ý client tự khai,
    KHÔNG đủ tin cậy để xác nhận file thật sự là ảnh (không phải file thực thi/
    script đổi tên đội lốt ảnh). Dùng extension SNIFF ĐƯỢC (không phải suy từ
    `Content-Type`) để đặt tên file lưu trên đĩa - đảm bảo extension luôn khớp
    ĐÚNG nội dung thật, kể cả khi `Content-Type` header khai sai định dạng cụ
    thể (VD PNG thật nhưng khai `image/jpeg` - vẫn được chấp nhận vì cả 2 đều
    nằm trong whitelist, nhưng lưu đúng đuôi `.png`).

    `nginx.conf` (task 2.4.1) đã có `client_max_body_size 10m` nhưng nginx
    CHƯA được đưa vào `docker-compose.yml` (dev bypass thẳng `:8000`, xem
    CLAUDE.md) - Backend tự giới hạn ở đây, không dựa hoàn toàn vào nginx
    (chỉ 1 lớp phòng thủ hiện đang thật sự chạy).
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

    extension = _sniff_image_extension(contents)
    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nội dung file không phải ảnh hợp lệ (JPEG/PNG/WEBP/GIF) - không khớp định dạng khai báo",
        )

    subdir = UPLOAD_ROOT / "products"
    subdir.mkdir(parents=True, exist_ok=True)

    # uuid4 (không phải tên file gốc client gửi lên) - tránh path traversal
    # (VD filename "../../etc/passwd") và tránh trùng tên giữa nhiều lần
    # upload cho CÙNG 1 sản phẩm (ảnh cũ dọn riêng qua `delete_product_image()`
    # - router gọi SAU khi ảnh mới đã lưu + commit thành công).
    filename = f"{product_id}-{uuid.uuid4().hex[:12]}{extension}"
    (subdir / filename).write_bytes(contents)

    return f"{UPLOAD_URL_PREFIX}/products/{filename}"


def delete_product_image(image_url: str | None) -> None:
    """Xóa file ảnh CŨ tương ứng `image_url` (nếu có) khỏi đĩa - gọi SAU khi
    ảnh MỚI đã `save_product_image()` + commit DB thành công (task "Hoàn
    thiện quản trị sản phẩm, danh mục và kho", đóng `docs/KNOWN_TODOS.md`
    #18) - thứ tự này tránh mất ảnh cũ nếu bước lưu ảnh mới thất bại giữa
    chừng (sản phẩm vẫn còn ảnh cũ hợp lệ để hiển thị).

    Chỉ xóa nếu `image_url` do CHÍNH `save_product_image()` tạo ra (bắt đầu
    bằng `UPLOAD_URL_PREFIX`) - bỏ qua im lặng nếu `None`/giá trị khác (VD
    seed data cũ hoặc URL ngoài, không có file cục bộ tương ứng để xóa).
    Validate path thật sự nằm trong `UPLOAD_ROOT` sau khi resolve (chặn path
    traversal nếu `image_url` từng bị chỉnh sửa bất thường) trước khi unlink,
    bỏ qua nếu file không tồn tại (`missing_ok=True` - không coi là lỗi, VD
    file đã bị xóa tay từ trước).
    """
    if not image_url or not image_url.startswith(f"{UPLOAD_URL_PREFIX}/"):
        return

    relative_path = image_url[len(UPLOAD_URL_PREFIX) + 1 :]
    file_path = (UPLOAD_ROOT / relative_path).resolve()
    try:
        file_path.relative_to(UPLOAD_ROOT.resolve())
    except ValueError:
        return
    file_path.unlink(missing_ok=True)
