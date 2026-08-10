type Params = Promise<{ id: string }>;

// Trang chi tiết đơn hàng THẬT chưa thuộc phạm vi task 4.3.3 (chỉ trang danh
// sách + filter + hủy đơn) - route này CHỈ giữ chỗ (stub tĩnh, cùng quy ước
// placeholder đã dùng cho /cart và /checkout trước khi có task riêng) để nút
// "Xem chi tiết" ở OrderCard link được vào 1 trang thật (không phải nút chết/
// disable) - GET /orders/{id} đã hoạt động thật ở Backend, sẵn sàng dùng khi
// làm task chi tiết đơn hàng sau này.
export default async function OrderDetailPage({ params }: { params: Params }) {
  const { id } = await params;
  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <h1 className="font-heading text-xl text-foreground">Chi tiết đơn hàng #{id}</h1>
      <p className="mt-2 text-sm text-foreground-muted">Trang chi tiết đơn hàng - sẽ triển khai sau.</p>
    </div>
  );
}
