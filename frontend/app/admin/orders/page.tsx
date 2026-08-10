"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { OrderTable } from "@/components/admin/OrderTable";
import { api } from "@/lib/axios";
import type { ApiResponse, PaginatedResponse } from "@/types/common";
import type { Order, OrderStatus } from "@/types/order";

const SEARCH_DEBOUNCE_MS = 450;

/**
 * Client Component (task 4.4.2) - CSR, cùng lý do `/admin/products` (task
 * 4.4.1) và `/orders` (task 4.3.3): trang quản trị nội bộ, cần tương tác
 * ngay (search/filter/đổi trạng thái không reload) hơn là cần SEO. State
 * filter (search/status/page) giữ ở `useState` THƯỜNG, KHÔNG đồng bộ qua URL
 * `searchParams` - tránh phải bọc `<Suspense>` cho `useSearchParams()` (đã
 * tự gặp lỗi build thật vì thiếu Suspense ở `/orders`, task 4.3.3).
 *
 * Gọi `GET /orders/admin` (task 3.4.2, mở rộng thêm `search` ở task 4.4.2) -
 * `search` gửi NGUYÊN VĂN input (Backend tự parse: chuỗi số/có tiền tố
 * "#"/"VUN" -> tìm theo `id`; ngược lại -> tìm theo `shipping_name`, xem
 * docstring `order_service.list_orders()` - hệ thống KHÔNG có mã đơn hàng
 * dạng chữ thật, "#123" chỉ là cách hiển thị cosmetic).
 */
export default function AdminOrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<OrderStatus | "">("");

  const fetchOrders = useCallback(async () => {
    setIsLoading(true);
    try {
      const params: Record<string, string | number> = { page, page_size: 10 };
      if (search) params.search = search;
      if (status) params.status = status;
      const { data } = await api.get<ApiResponse<PaginatedResponse<Order>>>("/orders/admin", { params });
      setOrders(data.data.items);
      setTotalPages(data.data.total_pages);
    } catch {
      toast.error("Không tải được danh sách đơn hàng.");
    } finally {
      setIsLoading(false);
    }
  }, [page, search, status]);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  // Debounce search - cùng pattern AdminProductsPage (task 4.4.1), luôn quay
  // về trang 1 khi đổi từ khóa.
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput);
      setPage(1);
    }, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [searchInput]);

  function handleStatusChange(value: OrderStatus | "") {
    setStatus(value);
    setPage(1);
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="font-heading text-2xl text-foreground">Quản lý đơn hàng</h1>
        <p className="mt-1 text-sm text-foreground-muted">Theo dõi và cập nhật trạng thái đơn hàng của khách.</p>
      </div>

      <OrderTable
        orders={orders}
        isLoading={isLoading}
        search={searchInput}
        onSearchChange={setSearchInput}
        status={status}
        onStatusChange={handleStatusChange}
        page={page}
        totalPages={totalPages}
        onPageChange={setPage}
        onChanged={fetchOrders}
      />
    </div>
  );
}
