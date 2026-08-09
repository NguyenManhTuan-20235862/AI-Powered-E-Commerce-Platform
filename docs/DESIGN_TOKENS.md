# Design Tokens (task 4.1.1)

Nguồn sự thật duy nhất cho màu/font/radius/shadow dùng trong `frontend/`.
Token được **trích xuất** từ theme đã chốt ở task 1.3.4 (trang đăng nhập/đăng
ký, Claude Design — thương hiệu "Vun", tông ấm kem/cam đất/xanh rêu, font
serif heading + sans-serif body, bo góc mềm) — KHÔNG phải theme mới, không
đổi hướng thẩm mỹ.

## Khai báo ở đâu

- `frontend/app/globals.css` — khối `:root { --color-*, --font-*, --radius-*, --shadow-lg }`
  là nơi khai báo GIÁ TRỊ THẬT (hex/font-family). Đổi theme (nếu có) chỉ sửa ở đây.
- `frontend/tailwind.config.ts` — map các biến trên thành `theme.extend.colors`/
  `fontFamily`/`borderRadius`/`boxShadow` với tên ngữ nghĩa, để dùng qua class
  Tailwind (`bg-primary`, `font-heading`...). KHÔNG lặp lại giá trị hex ở đây.
- `frontend/app/(auth)/auth.css` — CSS thuần (không phải Tailwind utility) cho
  riêng layout 2 cột của `/login`, `/register` — vẫn giữ nguyên cách viết cũ
  (đã test/hoạt động đúng, có `color-mix()`/keyframe/media query khó tái tạo
  gọn bằng utility). File này đọc CHUNG các biến `--color-*`/`--font-*` khai
  báo ở `globals.css`, không tự khai báo `:root` riêng nữa.

Trang mới (catalog, admin, theme-preview...) dùng thẳng class Tailwind ở
bảng dưới, không viết CSS riêng như `auth.css` trừ khi có layout thật sự đặc
biệt không biểu diễn gọn bằng utility (giống lý do giữ nguyên `auth.css`).

## Bảng token

| Class Tailwind | Biến CSS gốc | Giá trị | Dùng khi nào |
|---|---|---|---|
| `bg-background` | `--color-bg` | `#f5ead8` | Nền toàn trang (`<body>`). |
| `bg-surface` | `--color-surface` | `#ebddc5` | Nền card/input/header/sidebar — PHÂN BIỆT với nền trang để tạo độ sâu (không phải trắng phẳng). |
| `text-foreground` | `--color-text` | `#201e1d` | Chữ chính (heading, body text đậm). |
| `text-foreground-secondary` | `--color-neutral-700` | `#645c50` | Chữ phụ (subheading, label). |
| `text-foreground-muted` | `--color-neutral-600` | `#82796a` | Chữ mờ (hint, placeholder, caption). |
| `bg-primary` / `text-primary` | `--color-accent` | `#c67139` | Màu thương hiệu chính — CTA/button chính, link, trạng thái active. |
| `bg-primary-hover` | `--color-accent-600` | `#b2622d` | Hover state của `primary`. |
| `bg-primary-100`/`700`/`800`, tương tự `300` | `--color-accent-100/300/700/800` | xem `globals.css` | Sắc độ nhạt/đậm của primary — banner lỗi, badge, text trên nền nhạt. |
| `bg-secondary` / `text-secondary` | `--color-accent-2` | `#7a8a5e` | Màu phụ (xanh rêu) — banner thành công, tag, panel minh họa. |
| `bg-secondary-100`/`300`/`800`/`900` | `--color-accent-2-*` | xem `globals.css` | Sắc độ của secondary — tương tự primary. |
| `bg-error` / `text-error` | `--color-error` | `#ba1a1a` | Lỗi/danger (validate form, banner lỗi API) — task 4.3.2, thêm mới (trước đó chưa có token lỗi nào). Đỏ Material chuẩn, CỐ TÌNH tách khỏi bảng "đất/rêu" thương hiệu — màu lỗi cần nổi bật/dễ nhận biết hơn là nhất quán tông ấm. |
| `bg-error-container` | `--color-error-container` | `#ffdad6` | Nền nhạt cho banner lỗi (dùng cùng `text-error` cho chữ, tương tự cách `primary-100` dùng cho banner primary). |
| `border-border` | `--color-divider` (`color-mix`) | text 16% opacity | Viền input/card/divider — mờ, không dùng màu xám trung tính rời rạc. |
| `font-heading` | `--font-heading` | Caprasimo | Heading, brand mark, button, tab — chữ có cá tính. |
| `font-body` (= mặc định `font-sans`) | `--font-body` | Figtree | Body text, input, label, paragraph. |
| `rounded-2xl` | `--radius-md` | `16px` | Bo góc card/input tiêu chuẩn — TRÙNG giá trị mặc định Tailwind, không cần token riêng. |
| `rounded-4xl` | `--radius-lg` | `28px` | Bo góc phần tử lớn (ảnh minh họa, card nổi bật). |
| `rounded-full` | — | `999px` | Button/tab dạng pill (theo `.btn`/`.auth-tab` gốc). |
| `shadow-warm` | `--shadow-lg` | đổ bóng nâu ấm | Card/element cần nổi khối — thay cho `shadow-lg` mặc định (đen thuần, lệch tông). |

## Admin có cần theme riêng không?

**Chưa cần tách riêng ở thời điểm hiện tại.** Dùng CHUNG bộ token này cho cả
Customer lẫn Admin (task 4.4) — lý do: (1) đây là đồ án solo, tách riêng 2 hệ
theme tốn công thiết kế + bảo trì thêm mà chưa có yêu cầu nghiệp vụ nào đòi
hỏi Admin phải nhìn khác biệt hẳn Customer (VD không có yêu cầu "Admin phải
trông nghiêm túc/công sở hơn"); (2) `Sidebar.tsx` (đã refactor ở task 4.1.1)
dùng `primary-100` cho hover state, `surface` cho nền — đã đủ phân biệt trực
quan với vùng Customer (Header dùng `surface` tương tự nhưng bố cục ngang)
mà không cần bảng màu thứ 2. Nếu tới task 4.4 phát sinh nhu cầu thật (VD cần
"chế độ tối" riêng cho Admin dùng nhiều giờ), cân nhắc thêm 1 lớp token phụ
(`data-theme="admin"` + biến CSS override trong `admin/layout.tsx`) THAY VÌ
tạo bảng màu Tailwind hoàn toàn tách biệt — giữ nguyên tên class (`bg-primary`...)
để code component không phải viết 2 lần cho 2 theme.

## Trang demo

`frontend/app/(customer)/theme-preview/page.tsx` — xem trực quan toàn bộ
bảng trên + component mẫu (button/input/card). File TẠM THỜI, xóa khi không
còn cần đối chiếu.
