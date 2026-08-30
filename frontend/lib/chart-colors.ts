/**
 * Hex khớp CHÍNH XÁC `docs/DESIGN_TOKENS.md`/`app/globals.css` - dùng cho
 * thuộc tính SVG (`stroke`/`fill`) của Recharts (task 5.3.2, `RevenueChart`/
 * `TopProductsChart`). Recharts vẽ dataset qua SVG primitive, KHÔNG nhận
 * class Tailwind cho `stroke`/`fill` (khác Tooltip/Legend - render qua
 * HTML/DOM overlay, dùng class Tailwind bình thường ngay trong component,
 * không cần hằng số ở đây) - PHẢI truyền thẳng giá trị hex, đặt 1 nguồn duy
 * nhất ở đây để không lặp lại/lệch nếu design token đổi sau này.
 *
 * KHÔNG dùng theme màu mặc định của Recharts (tự sinh dải màu rainbow nếu
 * không cấu hình `stroke`/`fill` tường minh cho từng `<Line>`/`<Bar>`).
 */
export const CHART_COLOR_PRIMARY = "#c67139"; // --color-accent
export const CHART_COLOR_SECONDARY = "#7a8a5e"; // --color-accent-2
export const CHART_COLOR_GRID = "#82796a"; // --color-neutral-600 (foreground-muted)
export const CHART_COLOR_AXIS_TEXT = "#645c50"; // --color-neutral-700 (foreground-secondary)
