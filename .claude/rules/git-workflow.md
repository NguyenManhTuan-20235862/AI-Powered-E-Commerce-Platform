# Git Workflow

## Đầu mỗi phiên làm việc mới — BẮT BUỘC xác nhận trước khi nhận task

Chạy các lệnh sau, báo cáo kết quả cho user, rồi mới nhận task cụ thể:

```bash
pwd
git remote -v
git branch --show-current
git fetch origin
git log --oneline -5 origin/dev
```

- Nếu branch hiện tại **KHÔNG bắt nguồn từ `origin/dev` mới nhất** (base sai
  — ví dụ vô tình base từ `main`, hoặc branch cũ đã lỗi thời) → **DỪNG LẠI,
  báo ngay** — KHÔNG tự tạo branch mới hay code tiếp cho tới khi user xác nhận.
- Nếu đang đứng trực tiếp trên `dev`/`main` (chưa tách feature branch) → báo
  user, KHÔNG tự ý code trực tiếp lên đó.

## Branch strategy

- `main` → `dev` → `feature/<mô-tả-ngắn>` (hoặc `fix/<mô-tả-ngắn>` cho sửa
  lỗi nhỏ).
- MỌI feature/fix branch PHẢI tạo từ `origin/dev` mới nhất, KHÔNG BAO GIỜ
  từ `main`.

## Pull Request

- PR LUÔN có base = `dev`, KHÔNG BAO GIỜ base = `main` — trừ khi user yêu
  cầu tường minh 1 PR đồng bộ dev→main tại mốc cụ thể.
- Trước khi `gh pr create`, LUÔN chạy `git log --oneline origin/dev..HEAD`
  để xác nhận diff dự kiến CHỈ chứa đúng commit của task đang làm, không
  lẫn commit khác.

## Bài học từ sự cố thật

Branch `claude/rc-j2an8f` được Claude Code on the web tự tạo từ `main` thay
vì `dev` → PR mở ra có base sai → diff lẫn 67 file của 6 PR khác không liên
quan tới task đang làm → phải sửa lại base branch + tiêu đề/mô tả PR sau khi
phát hiện. Đây là lý do bước xác nhận môi trường ở đầu phiên (mục trên) là
bắt buộc, không phải thủ tục hình thức — sai base branch không lộ ra ngay,
chỉ lộ khi xem diff PR.
