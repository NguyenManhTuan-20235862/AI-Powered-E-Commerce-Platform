# Data Safety

- **KHÔNG BAO GIỜ** chạy `alembic upgrade head` hay bất kỳ lệnh ghi schema
  DB thật nào mà không cho user xem migration file trước.
- **KHÔNG BAO GIỜ** xóa container/volume có dữ liệu (MySQL, MongoDB, hoặc
  bất kỳ volume nào) mà không xác nhận đã có backup.
- Dữ liệu test tạo ra để verify PHẢI được dọn sạch sau khi xong — kể cả
  cache Redis stale nếu có thao tác trực tiếp SQL/Mongo trong lúc verify.
- Không commit `.env` thật, chỉ `.env*.example`.
