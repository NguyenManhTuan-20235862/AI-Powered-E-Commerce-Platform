# Data Safety

- **Migration MỚI soạn trong phiên làm việc (chưa commit/merge)**: KHÔNG BAO
  GIỜ tự chạy `alembic upgrade head` (hay bất kỳ lệnh ghi schema DB thật nào
  khác) với migration này mà không cho user xem file migration trước. Áp
  dụng cho cả migration Claude tự tạo lẫn migration đã có sẵn trong working
  tree nhưng chưa qua review/PR.
- **Migration ĐÃ commit/merge vào `dev` từ trước** (đã qua review/PR theo
  đúng quy trình `alembic revision --autogenerate` → review → PR → merge):
  để `docker-entrypoint.sh` (`backend/`) tự động chạy `alembic upgrade head`
  lúc container `backend` khởi động (`docker compose up`) là AN TOÀN và ĐÚNG
  THIẾT KẾ — KHÔNG vi phạm rule trên. Rule trên chỉ chặn việc TỰ Ý áp dụng
  migration chưa ai xem qua, không phải chặn việc áp dụng lại migration đã
  được duyệt. Không cần hỏi lại user mỗi lần `docker compose up` chỉ vì
  entrypoint gọi `alembic upgrade head` với migration cũ đã merge.
- **KHÔNG BAO GIỜ** xóa container/volume có dữ liệu (MySQL, MongoDB, hoặc
  bất kỳ volume nào) mà không xác nhận đã có backup.
- Dữ liệu test tạo ra để verify PHẢI được dọn sạch sau khi xong — kể cả
  cache Redis stale nếu có thao tác trực tiếp SQL/Mongo trong lúc verify.
- Không commit `.env` thật, chỉ `.env*.example`.
