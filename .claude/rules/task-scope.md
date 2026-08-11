# Task Scope

## Làm đúng phạm vi

User làm việc theo WBS chi tiết theo từng task nhỏ (VD task 4.3.2) — CHỈ làm
đúng phạm vi được giao trong task đó.

Nếu phát hiện cần sửa/thêm gì NGOÀI phạm vi (kể cả nhỏ, kể cả có vẻ hiển
nhiên đúng) → **DỪNG LẠI HỎI TRƯỚC**, đừng tự làm rồi báo cáo sau — trừ khi
đó là bug chặn đứng không thể hoàn thành task hiện tại nếu không sửa. Kể cả
trong trường hợp bug chặn đứng, vẫn phải nói rõ ràng đây là việc ngoài
phạm vi trước khi sửa.

## Ghi lại việc cố ý chưa làm

`docs/KNOWN_TODOS.md` dùng để ghi lại các việc cố ý chưa làm/phát sinh —
cập nhật file này ngay khi có phát hiện mới, không để trôi.

## Trước khi commit

- LUÔN liệt kê đầy đủ danh sách file dự kiến trước khi commit thật, dùng:
  ```bash
  git status --porcelain --untracked-files=all
  ```
  Chú ý `core.quotePath=false` nếu repo có tên file tiếng Việt (mặc định
  Git escape ký tự Unicode trong output, dễ đọc nhầm/bỏ sót tên file).
- Rà soát kỹ file phụ thuộc dễ bị sót — ví dụ: file mới import từ file khác
  cũng mới nhưng quên liệt kê, hoặc thay đổi ở nhiều nơi rải rác cùng do 1
  nguyên nhân (VD sửa 1 quyết định kiến trúc kéo theo sửa nhiều router/schema).
- Xác nhận danh sách file với user TRƯỚC KHI commit thật — không tự
  `git add .` rồi commit ngay.
- Nếu working tree có thay đổi KHÔNG liên quan tới task đang làm (VD fix nhỏ
  từ trước chưa commit) → BÁO user biết trước, đừng tự gộp chung hay tự tách
  riêng mà không hỏi.
