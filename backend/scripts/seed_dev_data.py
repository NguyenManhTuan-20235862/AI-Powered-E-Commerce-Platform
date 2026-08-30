"""Seed dữ liệu development mẫu (category/product/admin) - TÁCH BIỆT HOÀN
TOÀN khỏi Alembic migration (KHÔNG tạo/sửa schema gì ở đây, chỉ insert dữ
liệu vào bảng đã tồn tại) và khỏi dữ liệu test tạm thời tạo qua API lúc
verify tính năng (script này không xóa gì cả, chỉ thêm nếu chưa có).

KHÔNG tự chạy khi `docker compose up` (main.py/docker-entrypoint.sh không gọi
file này) - chỉ chạy THỦ CÔNG khi cần dữ liệu mẫu để phát triển/xem UI:

    docker compose exec backend python -m scripts.seed_dev_data

Idempotent - dựa trên unique key THẬT của từng bảng (`categories.slug`,
`products.slug`, `users.email` qua `seed_admin()` có sẵn - xem
docs/DATABASE_SCHEMA.md) - chạy lại nhiều lần AN TOÀN, không tạo trùng.
KHÔNG có `drop_all()`/`delete()` nào ở đây - không xóa dữ liệu cũ (kể cả dữ
liệu developer tạo qua API, hay 3 category/product thủ công ban đầu) trước
khi seed.

Admin: dùng LẠI `scripts.seed_admin.seed_admin()` có sẵn (KHÔNG viết lại
logic hash password/idempotency riêng) - đã tự dùng đúng
`app.core.security.hash_password` (bcrypt qua passlib), KHÔNG insert plain
text.

Slug: dùng LẠI `product_service.slugify()` có sẵn (task 3.4.1, KHÔNG viết
logic slug riêng) để tự sinh slug từ tên cho 6 category/120 product demo
bên dưới - tránh phải gõ tay hàng trăm slug, và đảm bảo khớp CHÍNH XÁC cách
Backend thật tự sinh slug khi Admin tạo sản phẩm không truyền slug qua API.
3 category/product thủ công ban đầu (gốm sứ/vải dệt/đồ gỗ) VẪN giữ slug
khai tay như cũ (không đổi hành vi đã hoạt động).

`image_url` để `None` cho toàn bộ sản phẩm demo (không có ảnh thật) -
`ProductCard.tsx` (Frontend) đã có sẵn fallback UI (icon khung ảnh) cho
`image_url == null`, không cần bịa URL placeholder giả.
"""

from decimal import Decimal

from app.core.database import SessionLocal
from app.models.category import Category
from app.models.product import Product
from app.services import product_service
from scripts.seed_admin import seed_admin

# Dữ liệu tối thiểu để xem được catalog có nội dung thật (không phải mảng
# rỗng) - KHÔNG bịa field ngoài những gì model thật yêu cầu (xem
# app/models/category.py, app/models/product.py): category chỉ cần
# name/slug/description, product cần thêm category_id (resolve qua slug bên
# dưới)/price/stock_quantity - `is_active` để mặc định model (True),
# `image_url` để trống (None, model cho phép nullable).
_CATEGORIES = [
    {"name": "Gốm sứ", "slug": "gom-su", "description": "Đồ gốm sứ thủ công"},
    {"name": "Vải dệt", "slug": "vai-det", "description": "Sản phẩm dệt may thủ công"},
    {"name": "Đồ gỗ", "slug": "do-go", "description": "Đồ nội thất/trang trí gỗ thủ công"},
]

_PRODUCTS = [
    {
        "slug": "binh-gom-hoa-van",
        "name": "Bình gốm hoa văn truyền thống",
        "category_slug": "gom-su",
        "price": Decimal("450000.00"),
        "stock_quantity": 20,
        "description": "Bình gốm thủ công, hoa văn truyền thống.",
    },
    {
        "slug": "khan-choang-len-det-tay",
        "name": "Khăn choàng len dệt tay",
        "category_slug": "vai-det",
        "price": Decimal("320000.00"),
        "stock_quantity": 15,
        "description": "Khăn choàng dệt tay từ sợi len tự nhiên.",
    },
    {
        "slug": "ghe-go-thu-cong",
        "name": "Ghế gỗ thủ công",
        "category_slug": "do-go",
        "price": Decimal("1250000.00"),
        "stock_quantity": 8,
        "description": "Ghế gỗ chạm khắc thủ công.",
    },
]

# ---- Dữ liệu demo cho trang chủ (category showcase) - 6 category x 20
# product = 120 product, TÁCH KHỎI _CATEGORIES/_PRODUCTS ở trên (giữ nguyên,
# không đổi hành vi cũ) - key trong _DEMO_PRODUCTS_BY_CATEGORY là TÊN category
# (không phải slug) để khỏi phải tự đoán/gõ tay slug tiếng Việt, slug thật sự
# dùng để insert/idempotency-check đều tính qua product_service.slugify() lúc
# chạy, xem _seed_demo_categories()/_seed_demo_products() bên dưới.

_DEMO_CATEGORY_DESCRIPTIONS: dict[str, str] = {
    "Điện tử": "Thiết bị điện tử, phụ kiện công nghệ cho công việc và giải trí.",
    "Thời trang": "Quần áo, giày dép và phụ kiện thời trang nam nữ.",
    "Nhà cửa": "Đồ gia dụng, trang trí và vật dụng sinh hoạt trong nhà.",
    "Làm đẹp": "Mỹ phẩm chăm sóc da, trang điểm và chăm sóc cá nhân.",
    "Đồ chơi": "Đồ chơi giáo dục và giải trí cho trẻ em mọi lứa tuổi.",
    "Sách": "Sách văn học, kỹ năng sống và sách thiếu nhi.",
}

# stock_quantity ("stock" trong mỗi dict bên dưới) đa dạng theo yêu cầu: đa
# số 10-50, mỗi category có sẵn 3-4 sản phẩm cố tình để thấp (2-5) rải rác
# ở nhiều vị trí khác nhau (KHÔNG cùng 1 index cố định) để test hết hàng.

_DEMO_PRODUCTS_BY_CATEGORY: dict[str, list[dict]] = {
    "Điện tử": [
        {"name": "Tai nghe không dây chống ồn", "price": "2490000.00", "stock": 15, "description": "Tai nghe Bluetooth chống ồn chủ động, pin sử dụng liên tục 30 giờ, âm bass mạnh mẽ."},
        {"name": "Bàn phím cơ RGB 87 phím", "price": "890000.00", "stock": 32, "description": "Bàn phím cơ switch blue, đèn LED RGB 16.8 triệu màu, gõ clicky rõ ràng."},
        {"name": "Chuột không dây gaming", "price": "450000.00", "stock": 40, "description": "Cảm biến quang học 6400 DPI, kết nối 2.4GHz ổn định, pin dùng 2 tháng."},
        {"name": "Loa Bluetooth mini chống nước", "price": "590000.00", "stock": 2, "description": "Loa di động chuẩn chống nước IPX7, âm thanh 360 độ, pin 12 giờ."},
        {"name": "Sạc dự phòng 20000mAh", "price": "350000.00", "stock": 48, "description": "Sạc nhanh 2 chiều, đủ sạc đầy điện thoại 4-5 lần, có màn hình hiển thị %."},
        {"name": "Ổ cứng di động 1TB", "price": "1190000.00", "stock": 19, "description": "Ổ cứng di động USB 3.0, tốc độ truyền cao, vỏ nhôm chống sốc."},
        {"name": "Webcam Full HD 1080p", "price": "620000.00", "stock": 27, "description": "Webcam họp trực tuyến độ nét cao, tự động lấy nét, có mic khử ồn."},
        {"name": "Đèn bàn học LED chống cận", "price": "280000.00", "stock": 36, "description": "Đèn LED 3 mức sáng, ánh sáng dịu mắt, có cổng sạc USB tích hợp."},
        {"name": "Máy chiếu mini di động", "price": "3290000.00", "stock": 12, "description": "Máy chiếu mini hỗ trợ Full HD, kết nối không dây điện thoại/laptop."},
        {"name": "Router wifi mesh 2 băng tần", "price": "1590000.00", "stock": 5, "description": "Phủ sóng wifi toàn nhà, băng tần kép, dễ dàng lắp đặt qua app."},
        {"name": "Bàn phím cơ không dây mini 60%", "price": "990000.00", "stock": 21, "description": "Kích thước nhỏ gọn, kết nối Bluetooth đa thiết bị, pin sạc trong."},
        {"name": "Tai nghe nhét tai true wireless", "price": "790000.00", "stock": 33, "description": "Chống ồn thụ động, hộp sạc di động, chống nước IPX4."},
        {"name": "Giá đỡ điện thoại để bàn", "price": "89000.00", "stock": 50, "description": "Chất liệu hợp kim nhôm, gấp gọn tiện lợi, tương thích mọi dòng máy."},
        {"name": "Cáp sạc nhanh USB-C 100W", "price": "149000.00", "stock": 3, "description": "Dây bọc dù chống đứt gãy, hỗ trợ sạc nhanh cho laptop và điện thoại."},
        {"name": "Ốp lưng điện thoại chống sốc", "price": "99000.00", "stock": 45, "description": "Chất liệu silicone cao cấp, chống sốc 4 góc, mỏng nhẹ ôm sát máy."},
        {"name": "Đồng hồ thông minh theo dõi sức khỏe", "price": "1890000.00", "stock": 4, "description": "Đo nhịp tim, SpO2, theo dõi giấc ngủ, chống nước bơi lội."},
        {"name": "Máy hút bụi cầm tay không dây", "price": "990000.00", "stock": 16, "description": "Lực hút mạnh, pin dùng 40 phút, kèm nhiều đầu hút đa năng."},
        {"name": "Loa vi tính 2.1 subwoofer", "price": "690000.00", "stock": 22, "description": "Bass mạnh mẽ nhờ loa siêu trầm rời, cổng kết nối AUX/USB."},
        {"name": "Bộ chuyển đổi HDMI to VGA", "price": "129000.00", "stock": 41, "description": "Hỗ trợ xuất hình Full HD, tương thích laptop/máy chiếu đời cũ."},
        {"name": "Camera an ninh wifi trong nhà", "price": "450000.00", "stock": 28, "description": "Xoay 360 độ, đàm thoại 2 chiều, xem trực tiếp qua app điện thoại."},
    ],
    "Thời trang": [
        {"name": "Áo thun cotton unisex trơn", "price": "149000.00", "stock": 50, "description": "Chất liệu cotton 100% thoáng mát, form rộng unisex, nhiều màu."},
        {"name": "Áo sơ mi công sở tay dài", "price": "359000.00", "stock": 30, "description": "Vải kate không nhăn, form slim fit, phù hợp môi trường công sở."},
        {"name": "Quần jean nam slim fit", "price": "429000.00", "stock": 24, "description": "Chất denim co giãn nhẹ, form slim tôn dáng, bền màu qua nhiều lần giặt."},
        {"name": "Chân váy chữ A midi", "price": "279000.00", "stock": 2, "description": "Dáng chữ A tôn eo, chất liệu tuyết mưa mềm mại, dễ phối đồ."},
        {"name": "Áo khoác bomber nữ", "price": "549000.00", "stock": 18, "description": "Chất liệu dù 2 lớp giữ ấm tốt, form basic dễ mặc, có túi 2 bên."},
        {"name": "Váy đầm suông dạo phố", "price": "389000.00", "stock": 26, "description": "Chất liệu linen thoáng mát, dáng suông thoải mái, phù hợp mùa hè."},
        {"name": "Áo hoodie nỉ bông form rộng", "price": "319000.00", "stock": 35, "description": "Nỉ bông dày dặn giữ ấm, form rộng unisex, có túi kangaroo."},
        {"name": "Quần short kaki nam", "price": "219000.00", "stock": 42, "description": "Chất kaki co giãn, form regular fit, phù hợp mặc hằng ngày."},
        {"name": "Áo len cổ lọ nữ", "price": "259000.00", "stock": 5, "description": "Len mềm mịn giữ ấm tốt, form ôm nhẹ, thích hợp mùa đông."},
        {"name": "Giày sneaker trắng basic", "price": "459000.00", "stock": 20, "description": "Đế cao su êm chân, phối được với mọi trang phục, dễ vệ sinh."},
        {"name": "Dép quai ngang nam nữ", "price": "129000.00", "stock": 48, "description": "Chất liệu cao su nhẹ, đế êm chống trơn trượt, thiết kế unisex."},
        {"name": "Thắt lưng da nam", "price": "199000.00", "stock": 31, "description": "Da bò thật, khóa kim loại chắc chắn, phù hợp cả công sở lẫn dạo phố."},
        {"name": "Túi tote vải canvas", "price": "149000.00", "stock": 37, "description": "Chất liệu canvas bền chắc, sức chứa lớn, in họa tiết đơn giản."},
        {"name": "Mũ lưỡi trai unisex", "price": "99000.00", "stock": 3, "description": "Vải kaki chống nắng, có thể điều chỉnh size, phối đồ dễ dàng."},
        {"name": "Khăn choàng cổ len", "price": "159000.00", "stock": 44, "description": "Len mềm mại giữ ấm, kích thước dài rộng, nhiều màu trơn."},
        {"name": "Áo blazer nữ công sở", "price": "599000.00", "stock": 14, "description": "Form vest ôm dáng, chất liệu dày dặn, phù hợp môi trường công sở."},
        {"name": "Quần legging thể thao", "price": "179000.00", "stock": 29, "description": "Chất liệu co giãn 4 chiều, thấm hút mồ hôi tốt, phù hợp tập gym/yoga."},
        {"name": "Áo polo nam cổ bẻ", "price": "249000.00", "stock": 33, "description": "Vải cá sấu thoáng mát, form regular, phù hợp mặc đi làm/dạo phố."},
        {"name": "Vớ cotton cổ ngắn (set 5 đôi)", "price": "89000.00", "stock": 46, "description": "Chất cotton thấm hút mồ hôi, co giãn tốt, set 5 đôi nhiều màu."},
        {"name": "Kính mát unisex chống UV", "price": "229000.00", "stock": 25, "description": "Tròng kính chống tia UV400, gọng nhựa bền nhẹ, phong cách basic."},
    ],
    "Nhà cửa": [
        {"name": "Nồi cơm điện tử 1.8L", "price": "890000.00", "stock": 18, "description": "Lòng nồi chống dính cao cấp, nấu nhanh giữ ấm lâu, phù hợp 3-5 người ăn."},
        {"name": "Bộ chăn ga gối cotton 4 món", "price": "690000.00", "stock": 22, "description": "Chất liệu cotton poly thoáng mát, họa tiết trơn nhẹ nhàng, dễ giặt ủi."},
        {"name": "Đèn ngủ để bàn cảm ứng", "price": "199000.00", "stock": 3, "description": "Điều chỉnh độ sáng bằng cảm ứng chạm, ánh sáng dịu mắt, kiểu dáng nhỏ gọn."},
        {"name": "Thảm trải sàn phòng khách", "price": "459000.00", "stock": 2, "description": "Chất liệu lông ngắn mềm mại, chống trượt đế, dễ vệ sinh."},
        {"name": "Bình giữ nhiệt inox 500ml", "price": "189000.00", "stock": 39, "description": "Giữ nhiệt nóng/lạnh 12 giờ, chất liệu inox 304 an toàn, nắp chống rò rỉ."},
        {"name": "Bộ dao inox nhà bếp 6 món", "price": "349000.00", "stock": 27, "description": "Lưỡi dao inox sắc bén, tay cầm chống trượt, kèm giá đựng gọn gàng."},
        {"name": "Máy lọc không khí mini", "price": "1290000.00", "stock": 11, "description": "Lọc bụi mịn PM2.5, khử mùi hiệu quả, phù hợp phòng dưới 20m2."},
        {"name": "Kệ gỗ để đồ đa năng", "price": "399000.00", "stock": 16, "description": "Chất liệu gỗ MDF chắc chắn, thiết kế nhiều tầng, dễ lắp ráp."},
        {"name": "Rèm cửa sổ vải chống nắng", "price": "329000.00", "stock": 5, "description": "Vải dày cản sáng tốt, chống tia UV, nhiều màu trung tính dễ phối nội thất."},
        {"name": "Nến thơm tinh dầu handmade", "price": "89000.00", "stock": 41, "description": "Sáp đậu nành tự nhiên, hương thơm dịu nhẹ, thời gian cháy 20-25 giờ."},
        {"name": "Bộ ly thủy tinh 6 chiếc", "price": "159000.00", "stock": 34, "description": "Thủy tinh trong suốt cao cấp, thiết kế đơn giản, phù hợp mọi loại đồ uống."},
        {"name": "Thớt gỗ chống khuẩn", "price": "129000.00", "stock": 38, "description": "Gỗ tự nhiên nguyên khối, kháng khuẩn tự nhiên, có lỗ treo tiện lợi."},
        {"name": "Máy xay sinh tố đa năng", "price": "690000.00", "stock": 20, "description": "Công suất mạnh mẽ, lưỡi dao inox 4 cạnh, cối xay dung tích 1.5L."},
        {"name": "Gối ôm bông ép cao cấp", "price": "199000.00", "stock": 30, "description": "Ruột bông ép êm ái, vỏ áo gối cotton thoáng mát, dễ tháo giặt."},
        {"name": "Bình xịt tưới cây mini", "price": "59000.00", "stock": 3, "description": "Vòi phun sương mịn, dung tích 500ml, chất liệu nhựa bền nhẹ."},
        {"name": "Móc treo quần áo inox (set 10 cái)", "price": "79000.00", "stock": 47, "description": "Chất liệu inox không gỉ, thiết kế chống trượt vai áo, set 10 cái."},
        {"name": "Thảm chùi chân cửa ra vào", "price": "69000.00", "stock": 43, "description": "Sợi ngắn thấm hút tốt, đế cao su chống trượt, dễ vệ sinh."},
        {"name": "Hộp đựng thực phẩm thủy tinh (set 3)", "price": "249000.00", "stock": 24, "description": "Thủy tinh chịu nhiệt, nắp nhựa kín khí, dùng được trong lò vi sóng."},
        {"name": "Quạt để bàn mini USB", "price": "149000.00", "stock": 32, "description": "Gió mát êm, cổng sạc USB tiện lợi, thiết kế nhỏ gọn để bàn làm việc."},
        {"name": "Bộ chậu cây cảnh mini để bàn", "price": "119000.00", "stock": 26, "description": "Chậu sứ mini kèm đế lót, phù hợp trang trí bàn làm việc/kệ sách."},
    ],
    "Làm đẹp": [
        {"name": "Kem chống nắng SPF50 nâng tông", "price": "259000.00", "stock": 40, "description": "Chống tia UVA/UVB, kết cấu mỏng nhẹ không bết dính, nâng tông tự nhiên."},
        {"name": "Serum vitamin C sáng da", "price": "349000.00", "stock": 28, "description": "Chiết xuất vitamin C nguyên chất, giúp làm sáng và đều màu da."},
        {"name": "Son kem lì màu đất nung", "price": "159000.00", "stock": 3, "description": "Kết cấu kem mịn lên màu chuẩn, lâu trôi, không gây khô môi."},
        {"name": "Mặt nạ giấy dưỡng ẩm (hộp 10 miếng)", "price": "189000.00", "stock": 9, "description": "Tinh chất dưỡng ẩm sâu, chất giấy mềm ôm sát da, hộp 10 miếng."},
        {"name": "Sữa rửa mặt tạo bọt dịu nhẹ", "price": "145000.00", "stock": 44, "description": "Làm sạch sâu không gây khô căng, phù hợp da nhạy cảm."},
        {"name": "Nước tẩy trang micellar 500ml", "price": "199000.00", "stock": 33, "description": "Làm sạch lớp trang điểm và bụi bẩn nhẹ nhàng, không cần rửa lại nước."},
        {"name": "Phấn phủ kiềm dầu dạng nén", "price": "219000.00", "stock": 21, "description": "Kiềm dầu suốt nhiều giờ, lớp phủ mỏng mịn tự nhiên."},
        {"name": "Chì kẻ mày lâu trôi", "price": "89000.00", "stock": 15, "description": "Đầu chì mảnh dễ tán, màu tự nhiên, giữ nét cả ngày."},
        {"name": "Dầu gội thảo dược phục hồi tóc", "price": "169000.00", "stock": 2, "description": "Chiết xuất thảo dược tự nhiên, giúp tóc chắc khỏe giảm gãy rụng."},
        {"name": "Kem dưỡng ẩm ban đêm", "price": "289000.00", "stock": 25, "description": "Kết cấu giàu dưỡng chất, phục hồi da trong lúc ngủ, không gây bí da."},
        {"name": "Bộ cọ trang điểm 8 cây", "price": "249000.00", "stock": 18, "description": "Lông cọ mềm mịn, đầy đủ cọ nền/mắt/highlight, kèm túi đựng."},
        {"name": "Nước hoa mini nữ 30ml", "price": "490000.00", "stock": 12, "description": "Hương thơm nhẹ nhàng lưu hương lâu, thiết kế chai nhỏ gọn tiện mang theo."},
        {"name": "Bảng phấn mắt 12 màu", "price": "329000.00", "stock": 5, "description": "Bảng màu đa dạng từ nhũ đến matte, lên màu chuẩn dễ phối."},
        {"name": "Máy rửa mặt silicone mini", "price": "199000.00", "stock": 23, "description": "Massage nhẹ nhàng làm sạch sâu lỗ chân lông, chống nước, sạc USB."},
        {"name": "Tinh dầu dưỡng môi", "price": "69000.00", "stock": 46, "description": "Dưỡng ẩm môi mềm mịn, thành phần tự nhiên an toàn, không màu."},
        {"name": "Kem tẩy tế bào chết body", "price": "179000.00", "stock": 30, "description": "Hạt tẩy mịn nhẹ nhàng, giúp da mềm mịn sáng khỏe sau khi dùng."},
        {"name": "Máy massage mặt cầm tay", "price": "450000.00", "stock": 3, "description": "Rung massage nhẹ nhàng hỗ trợ thẩm thấu dưỡng chất, sạc USB tiện lợi."},
        {"name": "Gương trang điểm có đèn LED", "price": "299000.00", "stock": 17, "description": "Đèn LED viền gương chỉnh 3 mức sáng, có thể xoay gập gọn."},
        {"name": "Bông tẩy trang hữu cơ (túi 100 miếng)", "price": "45000.00", "stock": 50, "description": "Sợi cotton hữu cơ mềm mại, thấm hút tốt, an toàn cho da nhạy cảm."},
        {"name": "Nước hoa hồng cân bằng da", "price": "159000.00", "stock": 36, "description": "Cân bằng độ pH sau rửa mặt, cấp ẩm nhẹ nhàng, không chứa cồn khô da."},
    ],
    "Đồ chơi": [
        {"name": "Bộ lắp ghép mô hình xe ô tô", "price": "590000.00", "stock": 14, "description": "Bộ lắp ghép nhựa ABS an toàn, rèn luyện tư duy logic và sự khéo léo."},
        {"name": "Gấu bông teddy cỡ lớn", "price": "289000.00", "stock": 20, "description": "Chất liệu bông mềm mịn, kích thước lớn ôm ấp, an toàn cho trẻ nhỏ."},
        {"name": "Xe điều khiển từ xa địa hình", "price": "450000.00", "stock": 3, "description": "Bánh xe bám địa hình tốt, pin sạc dùng được 20 phút liên tục."},
        {"name": "Bộ đồ chơi nấu ăn cho bé", "price": "259000.00", "stock": 27, "description": "Đầy đủ dụng cụ nhà bếp mini, chất liệu nhựa an toàn không mùi."},
        {"name": "Bảng vẽ điện tử cho trẻ em", "price": "199000.00", "stock": 5, "description": "Vẽ xóa dễ dàng nhiều lần, tiết kiệm giấy, kèm bút cảm ứng."},
        {"name": "Rubik 3x3 tốc độ cao", "price": "89000.00", "stock": 42, "description": "Xoay mượt êm tay, độ bền cao, phù hợp luyện tốc độ giải rubik."},
        {"name": "Bộ xếp hình gỗ tư duy", "price": "149000.00", "stock": 35, "description": "Chất liệu gỗ tự nhiên an toàn, giúp bé rèn luyện tư duy hình khối."},
        {"name": "Búp bê công chúa kèm phụ kiện", "price": "329000.00", "stock": 19, "description": "Búp bê nhựa an toàn kèm váy áo và phụ kiện trang điểm, đổi được nhiều bộ đồ."},
        {"name": "Bóng nhún trampoline mini cho bé", "price": "890000.00", "stock": 2, "description": "Khung thép chắc chắn, tay vịn an toàn, phù hợp vận động trong nhà."},
        {"name": "Bộ đồ chơi bác sĩ cho bé", "price": "179000.00", "stock": 31, "description": "Đầy đủ dụng cụ y tế mini, giúp bé nhập vai và phát triển kỹ năng xã hội."},
        {"name": "Máy bay giấy origami (bộ 20 mẫu)", "price": "59000.00", "stock": 48, "description": "Giấy in sẵn nhiều mẫu máy bay, hướng dẫn gấp chi tiết dễ làm theo."},
        {"name": "Đàn piano đồ chơi cho bé", "price": "349000.00", "stock": 5, "description": "Nhiều âm thanh nhạc cụ khác nhau, kích thích khả năng cảm âm cho bé."},
        {"name": "Bộ xếp hình nam châm 3D", "price": "259000.00", "stock": 16, "description": "Các mảnh ghép nam châm an toàn, phát triển tư duy không gian."},
        {"name": "Súng bắn nước mùa hè", "price": "99000.00", "stock": 39, "description": "Dung tích bình chứa lớn, bắn xa, chất liệu nhựa bền an toàn."},
        {"name": "Diều sáo truyền thống", "price": "79000.00", "stock": 24, "description": "Khung tre nhẹ, vải diều bền chắc, có sáo tạo âm thanh khi bay."},
        {"name": "Bộ đồ chơi xây dựng công trình", "price": "399000.00", "stock": 22, "description": "Mô phỏng công trường xây dựng thu nhỏ, kèm xe cần cẩu và phụ kiện."},
        {"name": "Thú nhồi bông thỏ mini", "price": "129000.00", "stock": 45, "description": "Kích thước nhỏ gọn dễ mang theo, bông nhồi êm mềm an toàn cho bé."},
        {"name": "Bộ đất nặn nhiều màu an toàn", "price": "89000.00", "stock": 37, "description": "Đất nặn mềm dẻo không độc hại, nhiều màu sắc kèm khuôn tạo hình."},
        {"name": "Xe đạp thăng bằng cho bé", "price": "690000.00", "stock": 10, "description": "Khung nhẹ chắc chắn, giúp bé tập giữ thăng bằng trước khi học xe đạp."},
        {"name": "Bảng chữ cái nam châm học tập", "price": "149000.00", "stock": 29, "description": "Chữ cái nam châm nhiều màu, giúp bé làm quen mặt chữ qua trò chơi."},
    ],
    "Sách": [
        {"name": "Đắc Nhân Tâm", "price": "86000.00", "stock": 50, "description": "Cuốn sách kinh điển về nghệ thuật đối nhân xử thế và giao tiếp."},
        {"name": "Nhà Giả Kim", "price": "79000.00", "stock": 44, "description": "Tiểu thuyết nổi tiếng về hành trình theo đuổi giấc mơ của chàng chăn cừu."},
        {"name": "Tuổi Trẻ Đáng Giá Bao Nhiêu", "price": "89000.00", "stock": 3, "description": "Những chia sẻ về hành trình tuổi trẻ, học tập và trải nghiệm sống."},
        {"name": "Sapiens - Lược Sử Loài Người", "price": "189000.00", "stock": 2, "description": "Hành trình lịch sử loài người từ thời nguyên thủy đến hiện đại."},
        {"name": "Cách Nghĩ Để Thành Công", "price": "99000.00", "stock": 26, "description": "Sách kỹ năng sống giúp thay đổi tư duy để đạt được thành công."},
        {"name": "Truyện Kiều (bìa cứng)", "price": "129000.00", "stock": 18, "description": "Tác phẩm văn học kinh điển của đại thi hào Nguyễn Du, bìa cứng trang trọng."},
        {"name": "Bí Mật Tư Duy Triệu Phú", "price": "109000.00", "stock": 22, "description": "Sách kỹ năng về tư duy tài chính và con đường xây dựng sự giàu có."},
        {"name": "Người Giàu Có Nhất Thành Babylon", "price": "79000.00", "stock": 35, "description": "Những bài học quản lý tài chính cá nhân qua các câu chuyện ngụ ngôn."},
        {"name": "Combo truyện thiếu nhi Doraemon (10 tập)", "price": "250000.00", "stock": 5, "description": "Combo 10 tập truyện tranh Doraemon quen thuộc với nhiều thế hệ thiếu nhi."},
        {"name": "Bố Già (The Godfather)", "price": "149000.00", "stock": 20, "description": "Tiểu thuyết kinh điển về thế giới ngầm và gia tộc mafia nổi tiếng."},
        {"name": "Nhà Lãnh Đạo Không Chức Danh", "price": "95000.00", "stock": 31, "description": "Sách kỹ năng về tinh thần lãnh đạo trong công việc và cuộc sống."},
        {"name": "Atomic Habits - Thay Đổi Tí Hon Hiệu Quả Bất Ngờ", "price": "119000.00", "stock": 3, "description": "Phương pháp xây dựng thói quen tốt và loại bỏ thói quen xấu hiệu quả."},
        {"name": "Chiến Binh Cầu Vồng", "price": "89000.00", "stock": 28, "description": "Câu chuyện cảm động về hành trình vượt khó để đến trường của các em nhỏ."},
        {"name": "Tôi Tài Giỏi Bạn Cũng Thế", "price": "99000.00", "stock": 33, "description": "Sách kỹ năng học tập giúp khai phá tiềm năng bản thân."},
        {"name": "Sách tô màu cho bé mầm non", "price": "39000.00", "stock": 48, "description": "Hình ảnh sinh động dễ thương, giúp bé phát triển khả năng sáng tạo."},
        {"name": "Từ điển Anh - Việt bỏ túi", "price": "69000.00", "stock": 40, "description": "Từ điển nhỏ gọn tiện mang theo, phù hợp học sinh sinh viên."},
        {"name": "Muôn Kiếp Nhân Sinh", "price": "159000.00", "stock": 24, "description": "Câu chuyện về hành trình chiêm nghiệm luân hồi và ý nghĩa cuộc sống."},
        {"name": "Kinh Tế Học Hài Hước (Freakonomics)", "price": "129000.00", "stock": 15, "description": "Góc nhìn kinh tế học thú vị về những hiện tượng đời sống thường ngày."},
        {"name": "Sổ tay lập kế hoạch (planner) 2026", "price": "99000.00", "stock": 30, "description": "Sổ kế hoạch theo tuần/tháng, giúp quản lý thời gian và mục tiêu hiệu quả."},
        {"name": "Cây Cam Ngọt Của Tôi", "price": "88000.00", "stock": 27, "description": "Câu chuyện cảm động về tuổi thơ của cậu bé Zezé đầy hồn nhiên và nghịch ngợm."},
    ],
}


def _seed_categories(db) -> dict[str, int]:
    """Trả về map slug -> id (kể cả category đã tồn tại từ trước) để
    `_seed_products` resolve `category_id` đúng FK."""
    slug_to_id: dict[str, int] = {}
    for data in _CATEGORIES:
        category = db.query(Category).filter(Category.slug == data["slug"]).one_or_none()
        if category is None:
            category = Category(**data)
            db.add(category)
            db.flush()  # lấy category.id (autoincrement) ngay, CHƯA commit
            print(f"  + category mới: {data['slug']} (id={category.id})")
        else:
            print(f"  = category đã tồn tại, bỏ qua: {data['slug']} (id={category.id})")
        slug_to_id[data["slug"]] = category.id
    return slug_to_id


def _seed_products(db, category_ids: dict[str, int]) -> None:
    for data in _PRODUCTS:
        existing = db.query(Product).filter(Product.slug == data["slug"]).one_or_none()
        if existing is not None:
            print(f"  = product đã tồn tại, bỏ qua: {data['slug']} (id={existing.id})")
            continue
        product = Product(
            category_id=category_ids[data["category_slug"]],
            name=data["name"],
            slug=data["slug"],
            description=data["description"],
            price=data["price"],
            stock_quantity=data["stock_quantity"],
        )
        db.add(product)
        db.flush()
        print(f"  + product mới: {data['slug']} (id={product.id})")


def _seed_demo_categories(db) -> dict[str, int]:
    """Như `_seed_categories()` nhưng slug tính qua `product_service.slugify()`
    (KHÔNG khai tay) - trả về map TÊN category -> id (không phải slug, vì
    `_DEMO_PRODUCTS_BY_CATEGORY` tổ chức theo tên cho dễ đọc/dễ đối chiếu)."""
    name_to_id: dict[str, int] = {}
    for name, description in _DEMO_CATEGORY_DESCRIPTIONS.items():
        slug = product_service.slugify(name)
        category = db.query(Category).filter(Category.slug == slug).one_or_none()
        if category is None:
            category = Category(name=name, slug=slug, description=description)
            db.add(category)
            db.flush()
            print(f"  + category mới: {slug} (id={category.id})")
        else:
            print(f"  = category đã tồn tại, bỏ qua: {slug} (id={category.id})")
        name_to_id[name] = category.id
    return name_to_id


def _seed_demo_products(db, category_id_by_name: dict[str, int]) -> None:
    created = 0
    skipped = 0
    for category_name, products in _DEMO_PRODUCTS_BY_CATEGORY.items():
        for data in products:
            slug = product_service.slugify(data["name"])
            existing = db.query(Product).filter(Product.slug == slug).one_or_none()
            if existing is not None:
                skipped += 1
                continue
            product = Product(
                category_id=category_id_by_name[category_name],
                name=data["name"],
                slug=slug,
                description=data["description"],
                price=Decimal(data["price"]),
                stock_quantity=data["stock"],
            )
            db.add(product)
            db.flush()
            created += 1
    print(f"  + {created} product demo mới được tạo, {skipped} đã tồn tại (bỏ qua)")


def seed_dev_data() -> None:
    db = SessionLocal()
    try:
        print("Category:")
        category_ids = _seed_categories(db)
        print("Product:")
        _seed_products(db, category_ids)

        print("Category demo (Điện tử/Thời trang/Nhà cửa/Làm đẹp/Đồ chơi/Sách):")
        demo_category_ids = _seed_demo_categories(db)
        print("Product demo:")
        _seed_demo_products(db, demo_category_ids)

        db.commit()
    finally:
        db.close()

    print("Admin:")
    seed_admin()


if __name__ == "__main__":
    seed_dev_data()
